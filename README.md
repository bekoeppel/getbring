# getbring

A command-line interface for [Bring!](https://www.getbring.com/) shopping lists.

View your lists, check what's on them, and add items -- all from your terminal.

## Install

```
uv tool install git+https://github.com/bekoeppel/getbring.git
```

Or clone and install locally:

```
git clone https://github.com/bekoeppel/getbring.git
cd getbring
uv tool install .
```

## Usage

### Log in

```
getbring auth login
```

You'll be prompted for your Bring! email and password. Credentials are stored locally in `~/.config/getbring/`.

### See your lists

```
getbring lists
```

### See what's on a list

```
getbring items Home
```

Add `--all` to also show recently purchased items. If you leave out the list name, you'll get an interactive picker.

### Add items

Add one or more items directly:

```
getbring add Home Milk
getbring add Home Milk Cheese Yoghurt
```

Or start interactive mode with autocomplete:

```
getbring add Home
```

This loads the full Bring! item catalog so you get fuzzy autocomplete as you type. Keep adding items until you're done (press Enter on an empty line or Ctrl+D to stop).

If you leave out the list name too, you'll first pick a list with arrow keys:

```
getbring add
```

### Log out

```
getbring auth logout
```
