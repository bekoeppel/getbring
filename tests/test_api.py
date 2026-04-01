import json
import pytest
import httpx
from unittest.mock import MagicMock, patch
from getbring import api, auth


# --- API key extraction tests ---

def test_api_key_pattern_matches():
    js_content = """apiKeyValue:'cof4Nc6D8saplXjE3h3HXqHH8m7VU2i1Gs0g85Sp',baseUrl"""
    match = api.API_KEY_PATTERN.search(js_content)
    assert match
    assert match.group(1) == "cof4Nc6D8saplXjE3h3HXqHH8m7VU2i1Gs0g85Sp"


def test_api_key_pattern_double_quotes():
    js_content = '''apiKeyValue: "someOtherKey123",baseUrl'''
    match = api.API_KEY_PATTERN.search(js_content)
    assert match
    assert match.group(1) == "someOtherKey123"


def test_get_api_key_returns_cached(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth, "API_KEY_FILE", tmp_path / "api_key.txt")
    auth.save_api_key("cached_key")
    assert api.get_api_key() == "cached_key"


def test_fetch_api_key_from_bundle(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth, "API_KEY_FILE", tmp_path / "api_key.txt")

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "blah apiKeyValue:'extracted_key' blah"
    mock_resp.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_resp

    key = api.fetch_api_key(mock_client)
    assert key == "extracted_key"
    assert auth.load_api_key() == "extracted_key"


def test_fetch_api_key_no_match(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth, "API_KEY_FILE", tmp_path / "api_key.txt")

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = "no key here"
    mock_resp.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_resp

    with pytest.raises(RuntimeError, match="Could not extract API key"):
        api.fetch_api_key(mock_client)


# --- resolve_list tests ---

SAMPLE_LISTS = [
    {"listUuid": "uuid-1", "name": "Home", "theme": "grocery"},
    {"listUuid": "uuid-2", "name": "Bau & Hobby", "theme": "home"},
    {"listUuid": "uuid-3", "name": "Holidays", "theme": "home"},
]


class FakeBringClient(api.BringClient):
    """BringClient that skips __init__ and uses fake data."""
    def __init__(self):
        # skip real __init__ — no HTTP, no auth
        self._client = None
        self._api_key = "fake"
        self._auth = {"uuid": "fake-uuid", "access_token": "fake-token"}

    def get_lists(self):
        return SAMPLE_LISTS


def test_resolve_list_by_uuid():
    client = FakeBringClient()
    result = client.resolve_list("uuid-2")
    assert result["name"] == "Bau & Hobby"


def test_resolve_list_by_exact_name():
    client = FakeBringClient()
    result = client.resolve_list("Home")
    assert result["listUuid"] == "uuid-1"


def test_resolve_list_by_name_case_insensitive():
    client = FakeBringClient()
    result = client.resolve_list("home")
    assert result["listUuid"] == "uuid-1"


def test_resolve_list_by_partial_name():
    client = FakeBringClient()
    result = client.resolve_list("Holi")
    assert result["listUuid"] == "uuid-3"


def test_resolve_list_ambiguous():
    client = FakeBringClient()
    with pytest.raises(Exception, match="Ambiguous"):
        client.resolve_list("Ho")  # matches Home and Holidays


def test_resolve_list_not_found():
    client = FakeBringClient()
    with pytest.raises(Exception, match="No list found"):
        client.resolve_list("nonexistent")


# --- get_articles tests ---

def test_get_articles():
    """Test that get_articles merges both locales with all search names."""
    mock_client_http = MagicMock()

    def fake_get(url, **kwargs):
        resp = MagicMock()
        resp.status_code = 200
        if "de-CH" in url:
            resp.json.return_value = {"Milch": "Milch", "Brot": "Brot", "Käse": "Käse"}
        elif "en-US" in url:
            resp.json.return_value = {"Milch": "Milk", "Brot": "Bread", "Käse": "Cheese"}
        return resp

    mock_client_http.get.side_effect = fake_get

    client = FakeBringClient()
    client._client = mock_client_http
    articles = client.get_articles()
    # keys are canonical item IDs
    assert "Milch" in articles
    assert "Brot" in articles
    assert "Käse" in articles
    # each key maps to a set containing both locale names
    assert "Milk" in articles["Milch"]
    assert "Milch" in articles["Milch"]
    assert "Bread" in articles["Brot"]
    assert "Cheese" in articles["Käse"]


def test_get_articles_one_locale_fails():
    """If one locale fails, we still get the other."""
    mock_client_http = MagicMock()

    def fake_get(url, **kwargs):
        resp = MagicMock()
        if "de-CH" in url:
            resp.status_code = 404
        else:
            resp.status_code = 200
            resp.json.return_value = {"Milch": "Milk", "Brot": "Bread"}
        return resp

    mock_client_http.get.side_effect = fake_get

    client = FakeBringClient()
    client._client = mock_client_http
    articles = client.get_articles()
    assert "Milch" in articles
    assert "Milk" in articles["Milch"]
    assert "Brot" in articles
