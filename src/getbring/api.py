import re
import click
import httpx
from getbring.auth import load_auth, load_api_key, save_api_key

BASE_URL = "https://api.getbring.com"
BUNDLE_URL = "https://web.getbring.com/main.bundle.js"
API_KEY_PATTERN = re.compile(r"""apiKeyValue:\s*['"]([^'"]+)['"]""")

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:149.0) Gecko/20100101 Firefox/149.0",
    "Accept": "application/json, text/plain, */*",
    "X-BRING-CLIENT": "webApp",
    "X-BRING-COUNTRY": "CH",
}


def fetch_api_key(client: httpx.Client | None = None) -> str:
    """Fetch the API key from the Bring! web app bundle."""
    if client is None:
        client = httpx.Client()
    resp = client.get(BUNDLE_URL)
    resp.raise_for_status()
    match = API_KEY_PATTERN.search(resp.text)
    if not match:
        raise RuntimeError("Could not extract API key from main.bundle.js")
    key = match.group(1)
    save_api_key(key)
    return key


def get_api_key(client: httpx.Client | None = None) -> str:
    """Return cached API key, or fetch and cache it."""
    cached = load_api_key()
    if cached:
        return cached
    return fetch_api_key(client)


class BringClient:
    def __init__(self):
        self._client = httpx.Client()
        self._api_key = get_api_key(self._client)
        self._auth = load_auth()

    def _headers(self, authenticated: bool = True) -> dict:
        headers = {
            **COMMON_HEADERS,
            "X-BRING-API-KEY": self._api_key,
        }
        if authenticated and self._auth:
            headers["Authorization"] = f"Bearer {self._auth['access_token']}"
            headers["X-BRING-USER-UUID"] = self._auth["uuid"]
        return headers

    def login(self, email: str, password: str) -> dict:
        resp = self._client.post(
            f"{BASE_URL}/rest/v2/bringauth",
            headers={**self._headers(authenticated=False), "Content-Type": "application/x-www-form-urlencoded"},
            data={"email": email, "password": password},
        )
        resp.raise_for_status()
        return resp.json()

    def get_lists(self) -> list[dict]:
        resp = self._client.get(
            f"{BASE_URL}/rest/v2/bringusers/{self._auth['uuid']}/lists",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()["lists"]

    def get_list_items(self, list_uuid: str) -> dict:
        resp = self._client.get(
            f"{BASE_URL}/rest/v2/bringlists/{list_uuid}",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def get_list_details(self, list_uuid: str) -> list[dict]:
        resp = self._client.get(
            f"{BASE_URL}/rest/v2/bringlists/{list_uuid}/details",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def add_item(self, list_uuid: str, item_name: str, specification: str = "") -> None:
        resp = self._client.put(
            f"{BASE_URL}/rest/v2/bringlists/{list_uuid}",
            headers={**self._headers(), "Content-Type": "application/x-www-form-urlencoded"},
            data={"uuid": list_uuid, "purchase": item_name, "specification": specification},
        )
        resp.raise_for_status()

    def get_articles(self) -> list[str]:
        """Fetch article names from both de-CH and en-US catalogs."""
        names = set()
        for locale in ("de-CH", "en-US"):
            resp = self._client.get(
                f"https://web.getbring.com/locale/articles.{locale}.json",
                headers=COMMON_HEADERS,
            )
            if resp.status_code == 200:
                names.update(resp.json().keys())
        return sorted(names)

    def resolve_list(self, name_or_uuid: str) -> dict:
        """Find a list by name (case-insensitive partial match) or UUID."""
        lists = self.get_lists()
        # exact UUID match
        for lst in lists:
            if lst["listUuid"] == name_or_uuid:
                return lst
        # case-insensitive exact name match
        for lst in lists:
            if lst["name"].lower() == name_or_uuid.lower():
                return lst
        # case-insensitive partial name match
        matches = [lst for lst in lists if name_or_uuid.lower() in lst["name"].lower()]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            names = ", ".join(m["name"] for m in matches)
            raise click.ClickException(f"Ambiguous list name '{name_or_uuid}', matches: {names}")
        raise click.ClickException(f"No list found matching '{name_or_uuid}'")
