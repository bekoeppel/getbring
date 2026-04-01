from prompt_toolkit.document import Document
from getbring.cli import ArticleCompleter


def _complete(completer, text):
    """Helper: get completions for given text."""
    doc = Document(text, len(text))
    return list(completer.get_completions(doc, None))


def test_search_by_german_name():
    articles = {"Milch": {"Milch", "Milk"}, "Brot": {"Brot", "Bread"}}
    completer = ArticleCompleter(articles)
    results = _complete(completer, "mil")
    keys = [c.text for c in results]
    assert "Milch" in keys


def test_search_by_english_name():
    articles = {"Milch": {"Milch", "Milk"}, "Brot": {"Brot", "Bread"}}
    completer = ArticleCompleter(articles)
    results = _complete(completer, "milk")
    keys = [c.text for c in results]
    assert "Milch" in keys


def test_search_shows_english_as_meta():
    articles = {"Milch": {"Milch", "Milk"}}
    completer = ArticleCompleter(articles)
    results = _complete(completer, "milk")
    assert len(results) == 1
    assert results[0].text == "Milch"
    # display_meta is wrapped in FormattedText by prompt_toolkit
    meta = results[0].display_meta
    meta_text = "".join(t[1] for t in meta) if hasattr(meta, "__iter__") and not isinstance(meta, str) else meta
    assert meta_text == "Milk"


def test_search_by_partial():
    articles = {"Hackfleisch": {"Hackfleisch", "Ground meat"}}
    completer = ArticleCompleter(articles)
    results = _complete(completer, "ground")
    keys = [c.text for c in results]
    assert "Hackfleisch" in keys


def test_search_case_insensitive():
    articles = {"Milch": {"Milch", "Milk"}}
    completer = ArticleCompleter(articles)
    results = _complete(completer, "MILK")
    keys = [c.text for c in results]
    assert "Milch" in keys


def test_empty_input_returns_all():
    articles = {"Milch": {"Milch", "Milk"}, "Brot": {"Brot", "Bread"}}
    completer = ArticleCompleter(articles)
    results = _complete(completer, "")
    keys = [c.text for c in results]
    assert "Milch" in keys
    assert "Brot" in keys


def test_no_duplicates():
    articles = {"Milch": {"Milch", "Milk"}}
    completer = ArticleCompleter(articles)
    # "mi" matches both "Milch" and "Milk" but should only yield one completion
    results = _complete(completer, "mi")
    keys = [c.text for c in results]
    assert keys.count("Milch") == 1
