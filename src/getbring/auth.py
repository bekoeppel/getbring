import json
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "getbring"
AUTH_FILE = CONFIG_DIR / "auth.json"
API_KEY_FILE = CONFIG_DIR / "api_key.txt"


def _ensure_config_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def save_auth(data: dict):
    _ensure_config_dir()
    AUTH_FILE.write_text(json.dumps(data, indent=2))


def load_auth() -> dict | None:
    if not AUTH_FILE.exists():
        return None
    return json.loads(AUTH_FILE.read_text())


def clear_auth():
    if AUTH_FILE.exists():
        AUTH_FILE.unlink()


def save_api_key(key: str):
    _ensure_config_dir()
    API_KEY_FILE.write_text(key)


def load_api_key() -> str | None:
    if not API_KEY_FILE.exists():
        return None
    return API_KEY_FILE.read_text().strip()


def clear_api_key():
    if API_KEY_FILE.exists():
        API_KEY_FILE.unlink()
