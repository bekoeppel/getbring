import json
from getbring import auth


def test_save_and_load_auth(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")

    assert auth.load_auth() is None

    data = {"uuid": "abc-123", "email": "test@example.com", "access_token": "tok"}
    auth.save_auth(data)
    loaded = auth.load_auth()
    assert loaded == data


def test_clear_auth(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")

    auth.save_auth({"key": "val"})
    assert auth.load_auth() is not None
    auth.clear_auth()
    assert auth.load_auth() is None


def test_clear_auth_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")
    auth.clear_auth()  # should not raise


def test_save_and_load_api_key(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth, "API_KEY_FILE", tmp_path / "api_key.txt")

    assert auth.load_api_key() is None
    auth.save_api_key("mykey123")
    assert auth.load_api_key() == "mykey123"


def test_clear_api_key(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth, "API_KEY_FILE", tmp_path / "api_key.txt")

    auth.save_api_key("mykey123")
    auth.clear_api_key()
    assert auth.load_api_key() is None
