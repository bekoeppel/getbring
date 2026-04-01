import json
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
from getbring.cli import cli
from getbring import auth


def test_auth_status_not_logged_in(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")
    runner = CliRunner()
    result = runner.invoke(cli, ["auth", "status"])
    assert result.exit_code == 0
    assert "Not logged in" in result.output


def test_auth_status_logged_in(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")
    auth.save_auth({"name": "Beni", "email": "test@example.com", "uuid": "abc-123"})

    runner = CliRunner()
    result = runner.invoke(cli, ["auth", "status"])
    assert result.exit_code == 0
    assert "Beni" in result.output
    assert "test@example.com" in result.output


def test_auth_logout(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")
    auth.save_auth({"name": "Beni"})

    runner = CliRunner()
    result = runner.invoke(cli, ["auth", "logout"])
    assert result.exit_code == 0
    assert "Logged out" in result.output
    assert auth.load_auth() is None


def test_lists_not_logged_in(tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")
    runner = CliRunner()
    result = runner.invoke(cli, ["lists"])
    assert result.exit_code != 0
    assert "Not logged in" in result.output


@patch("getbring.cli.BringClient")
def test_lists_shows_names(mock_client_cls, tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")
    auth.save_auth({"name": "Beni", "email": "t@t.com", "uuid": "u"})

    mock_client = MagicMock()
    mock_client.get_lists.return_value = [
        {"listUuid": "u1", "name": "Home"},
        {"listUuid": "u2", "name": "Work"},
    ]
    mock_client_cls.return_value = mock_client

    runner = CliRunner()
    result = runner.invoke(cli, ["lists"])
    assert result.exit_code == 0
    assert "Home" in result.output
    assert "Work" in result.output


@patch("getbring.cli.BringClient")
def test_items_with_list_name(mock_client_cls, tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")
    auth.save_auth({"name": "Beni", "email": "t@t.com", "uuid": "u"})

    mock_client = MagicMock()
    mock_client.resolve_list.return_value = {"listUuid": "u1", "name": "Home"}
    mock_client.get_list_items.return_value = {
        "purchase": [{"name": "Milk", "specification": ""}, {"name": "Bread", "specification": "whole grain"}],
        "recently": [{"name": "Eggs", "specification": ""}],
    }
    mock_client_cls.return_value = mock_client

    runner = CliRunner()
    result = runner.invoke(cli, ["items", "Home"])
    assert result.exit_code == 0
    assert "Milk" in result.output
    assert "Bread" in result.output
    assert "whole grain" in result.output
    assert "Eggs" not in result.output  # not shown without --all


@patch("getbring.cli.BringClient")
def test_items_with_all_flag(mock_client_cls, tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")
    auth.save_auth({"name": "Beni", "email": "t@t.com", "uuid": "u"})

    mock_client = MagicMock()
    mock_client.resolve_list.return_value = {"listUuid": "u1", "name": "Home"}
    mock_client.get_list_items.return_value = {
        "purchase": [{"name": "Milk", "specification": ""}],
        "recently": [{"name": "Eggs", "specification": ""}],
    }
    mock_client_cls.return_value = mock_client

    runner = CliRunner()
    result = runner.invoke(cli, ["items", "Home", "--all"])
    assert result.exit_code == 0
    assert "Eggs" in result.output


@patch("getbring.cli.BringClient")
def test_add_item_direct(mock_client_cls, tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")
    auth.save_auth({"name": "Beni", "email": "t@t.com", "uuid": "u"})

    mock_client = MagicMock()
    mock_client.resolve_list.return_value = {"listUuid": "u1", "name": "Home"}
    mock_client_cls.return_value = mock_client

    runner = CliRunner()
    result = runner.invoke(cli, ["add", "Home", "Toast"])
    assert result.exit_code == 0
    assert "Added 'Toast'" in result.output
    mock_client.add_item.assert_called_once_with("u1", "Toast")


@patch("getbring.cli.BringClient")
def test_add_multiple_items(mock_client_cls, tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")
    auth.save_auth({"name": "Beni", "email": "t@t.com", "uuid": "u"})

    mock_client = MagicMock()
    mock_client.resolve_list.return_value = {"listUuid": "u1", "name": "Home"}
    mock_client_cls.return_value = mock_client

    runner = CliRunner()
    result = runner.invoke(cli, ["add", "Home", "Milk", "Cheese", "Yoghurt"])
    assert result.exit_code == 0
    assert "Added 'Milk'" in result.output
    assert "Added 'Cheese'" in result.output
    assert "Added 'Yoghurt'" in result.output
    assert mock_client.add_item.call_count == 3


@patch("getbring.cli.BringClient")
def test_remove_item_direct(mock_client_cls, tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")
    auth.save_auth({"name": "Beni", "email": "t@t.com", "uuid": "u"})

    mock_client = MagicMock()
    mock_client.resolve_list.return_value = {"listUuid": "u1", "name": "Home"}
    mock_client_cls.return_value = mock_client

    runner = CliRunner()
    result = runner.invoke(cli, ["remove", "Home", "Toast"])
    assert result.exit_code == 0
    assert "Removed 'Toast'" in result.output
    mock_client.remove_item.assert_called_once_with("u1", "Toast")


@patch("getbring.cli.BringClient")
def test_remove_multiple_items(mock_client_cls, tmp_path, monkeypatch):
    monkeypatch.setattr(auth, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(auth, "AUTH_FILE", tmp_path / "auth.json")
    auth.save_auth({"name": "Beni", "email": "t@t.com", "uuid": "u"})

    mock_client = MagicMock()
    mock_client.resolve_list.return_value = {"listUuid": "u1", "name": "Home"}
    mock_client_cls.return_value = mock_client

    runner = CliRunner()
    result = runner.invoke(cli, ["remove", "Home", "Milk", "Cheese"])
    assert result.exit_code == 0
    assert "Removed 'Milk'" in result.output
    assert "Removed 'Cheese'" in result.output
    assert mock_client.remove_item.call_count == 2
