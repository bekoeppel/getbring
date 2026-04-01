import click
from prompt_toolkit import prompt
from prompt_toolkit.application import Application
from prompt_toolkit.completion import FuzzyCompleter, WordCompleter
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.containers import Window

from getbring.api import BringClient
from getbring.auth import save_auth, load_auth, clear_auth


def _fuzzy_prompt(message: str, words: list[str]) -> str:
    """Prompt with fuzzy autocomplete that shows completions immediately."""
    completer = FuzzyCompleter(WordCompleter(words, sentence=True))
    return prompt(message, completer=completer, complete_while_typing=True).strip()


def _select_prompt(message: str, choices: list[str]) -> int:
    """Arrow-key selector. Returns the index of the chosen item."""
    selected = [0]

    def get_text():
        lines = []
        for i, choice in enumerate(choices):
            if i == selected[0]:
                lines.append(("class:selected", f"  > {choice}\n"))
            else:
                lines.append(("", f"    {choice}\n"))
        return FormattedText(lines)

    kb = KeyBindings()

    @kb.add("up")
    @kb.add("k")
    def _up(event):
        selected[0] = max(0, selected[0] - 1)

    @kb.add("down")
    @kb.add("j")
    def _down(event):
        selected[0] = min(len(choices) - 1, selected[0] + 1)

    @kb.add("enter")
    def _enter(event):
        event.app.exit(result=selected[0])

    @kb.add("c-c")
    @kb.add("c-d")
    def _quit(event):
        event.app.exit(result=None)

    from prompt_toolkit.styles import Style
    style = Style.from_dict({"selected": "bold reverse"})

    control = FormattedTextControl(get_text)
    app = Application(
        layout=Layout(Window(control)),
        key_bindings=kb,
        style=style,
        full_screen=False,
    )

    click.echo(message)
    result = app.run()
    if result is None:
        raise click.Abort()
    return result


class OrderedGroup(click.Group):
    def list_commands(self, ctx):
        return list(self.commands)


@click.group(cls=OrderedGroup)
def cli():
    """CLI for Bring! shopping lists."""


# --- auth commands ---

@cli.group(cls=OrderedGroup)
def auth():
    """Manage authentication."""


@auth.command()
def login():
    """Log in to Bring!"""
    email = click.prompt("Email")
    password = click.prompt("Password", hide_input=True)
    client = BringClient()
    try:
        data = client.login(email, password)
    except Exception as e:
        raise click.ClickException(f"Login failed: {e}")
    save_auth(data)
    click.echo(f"Logged in as {data.get('name') or email}")


@auth.command()
def logout():
    """Log out and remove stored credentials."""
    clear_auth()
    click.echo("Logged out.")


@auth.command()
def status():
    """Show current auth status."""
    data = load_auth()
    if not data:
        click.echo("Not logged in.")
        return
    click.echo(f"Logged in as: {data.get('name') or 'unknown'} ({data.get('email') or 'unknown'})")
    click.echo(f"UUID: {data.get('uuid', 'unknown')}")


# --- list commands ---

def _require_auth():
    data = load_auth()
    if not data:
        raise click.ClickException("Not logged in. Run 'getbring auth login' first.")
    return data


def _pick_list(client: BringClient) -> dict:
    """Interactive list picker with arrow keys."""
    all_lists = client.get_lists()
    names = [lst["name"] for lst in all_lists]
    idx = _select_prompt("Select list:", names)
    return all_lists[idx]


@cli.command("lists")
def list_lists():
    """List all shopping lists."""
    _require_auth()
    client = BringClient()
    lists = client.get_lists()
    for lst in lists:
        click.echo(f"  {lst['name']}")


@cli.command("items")
@click.argument("list_name", required=False)
@click.option("--all", "show_all", is_flag=True, help="Also show recently purchased items")
def list_items(list_name, show_all):
    """Show items in a shopping list."""
    _require_auth()
    client = BringClient()

    if list_name:
        lst = client.resolve_list(list_name)
    else:
        lst = _pick_list(client)

    data = client.get_list_items(lst["listUuid"])

    purchase = data.get("purchase", [])
    if purchase:
        click.echo(f"To buy ({lst['name']}):")
        for item in purchase:
            spec = item.get("specification", "")
            line = f"  - {item['name']}"
            if spec:
                line += f" ({spec})"
            click.echo(line)
    else:
        click.echo(f"No items to buy in {lst['name']}.")

    if show_all:
        recently = data.get("recently", [])
        if recently:
            click.echo(f"\nRecently purchased:")
            for item in recently:
                spec = item.get("specification", "")
                line = f"  - {item['name']}"
                if spec:
                    line += f" ({spec})"
                click.echo(line)


@cli.command("add")
@click.argument("list_name", required=False)
@click.argument("item", required=False)
def add_item(list_name, item):
    """Add an item to a shopping list.

    If LIST_NAME is omitted, shows a list picker.
    If ITEM is omitted, enters interactive mode with autocomplete.
    """
    _require_auth()
    client = BringClient()

    if list_name:
        lst = client.resolve_list(list_name)
    else:
        lst = _pick_list(client)

    if item:
        client.add_item(lst["listUuid"], item)
        click.echo(f"Added '{item}' to {lst['name']}.")
        return

    # interactive mode — merge catalog articles + list history for autocomplete
    click.echo(f"Loading item catalog...")
    articles = client.get_articles()
    details = client.get_list_details(lst["listUuid"])
    history_items = {d["itemId"] for d in details}
    all_items = sorted(set(articles) | history_items)

    click.echo(f"Adding items to {lst['name']} (Tab to autocomplete, empty line or Ctrl+D to stop):")
    while True:
        try:
            text = _fuzzy_prompt("  > ", all_items)
        except (EOFError, KeyboardInterrupt):
            click.echo("")
            break
        if not text:
            break
        client.add_item(lst["listUuid"], text)
        click.echo(f"    Added '{text}'")

    click.echo("Done.")
