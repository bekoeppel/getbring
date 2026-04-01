import click
from prompt_toolkit import prompt
from prompt_toolkit.application import Application
from prompt_toolkit.completion import Completer, Completion, FuzzyCompleter, WordCompleter
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


class ArticleCompleter(Completer):
    """Fuzzy completer that searches across multilingual article names.

    Matches against all locale names (e.g. "Milch", "Milk") but completes
    with the canonical item ID, showing the matched alias in the display.
    """

    def __init__(self, articles: dict[str, set[str]]):
        # articles: {canonical_key: {name1, name2, ...}}
        self._articles = articles

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.lower()
        if not text:
            for key in sorted(self._articles):
                yield Completion(key, start_position=-len(document.text_before_cursor))
            return

        seen = set()
        for key, names in self._articles.items():
            # check if any name fuzzy-matches the input
            best_match = None
            for name in names:
                if text in name.lower():
                    # prefer exact key match, then shortest matching name
                    if name == key:
                        best_match = key
                        break
                    if best_match is None or len(name) < len(best_match):
                        best_match = name

            if best_match is not None and key not in seen:
                seen.add(key)
                display_meta = ""
                if best_match != key:
                    display_meta = best_match
                yield Completion(
                    key,
                    start_position=-len(document.text_before_cursor),
                    display=key,
                    display_meta=display_meta,
                )


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
@click.argument("list_name")
@click.argument("items", nargs=-1)
def add_item(list_name, items):
    """Add items to a shopping list.

    If no ITEMs are given, enters interactive mode with autocomplete.
    Multiple items can be given: getbring add Home Milk Cheese Yoghurt
    """
    _require_auth()
    client = BringClient()
    lst = client.resolve_list(list_name)

    if items:
        for item in items:
            client.add_item(lst["listUuid"], item)
            click.echo(f"Added '{item}' to {lst['name']}.")
        return

    # interactive mode — merge catalog articles + list history for autocomplete
    click.echo("Loading item catalog...")
    articles = client.get_articles()
    details = client.get_list_details(lst["listUuid"])
    for d in details:
        item_id = d["itemId"]
        if item_id not in articles:
            articles[item_id] = {item_id}

    completer = ArticleCompleter(articles)

    click.echo(f"Adding items to {lst['name']} (start typing to search, empty line or Ctrl+D to stop):")
    while True:
        try:
            text = prompt("  > ", completer=completer, complete_while_typing=True).strip()
        except (EOFError, KeyboardInterrupt):
            click.echo("")
            break
        if not text:
            break
        client.add_item(lst["listUuid"], text)
        click.echo(f"    Added '{text}'")

    click.echo("Done.")


@cli.command("remove")
@click.argument("list_name")
@click.argument("items", nargs=-1)
def remove_item(list_name, items):
    """Remove items from a shopping list (moves them to recently purchased).

    If no ITEMs are given, enters interactive mode with the current list items.
    Multiple items can be given: getbring remove Home Milk Cheese
    """
    _require_auth()
    client = BringClient()
    lst = client.resolve_list(list_name)

    if items:
        for item in items:
            client.remove_item(lst["listUuid"], item)
            click.echo(f"Removed '{item}' from {lst['name']}.")
        return

    # interactive mode — autocomplete from current purchase list
    data = client.get_list_items(lst["listUuid"])
    purchase = [item["name"] for item in data.get("purchase", [])]
    if not purchase:
        click.echo(f"No items to remove in {lst['name']}.")
        return

    click.echo(f"Removing items from {lst['name']} (empty line or Ctrl+D to stop):")
    while True:
        # refresh available items each iteration
        try:
            text = _fuzzy_prompt("  > ", purchase)
        except (EOFError, KeyboardInterrupt):
            click.echo("")
            break
        if not text:
            break
        client.remove_item(lst["listUuid"], text)
        if text in purchase:
            purchase.remove(text)
        click.echo(f"    Removed '{text}'")

    click.echo("Done.")
