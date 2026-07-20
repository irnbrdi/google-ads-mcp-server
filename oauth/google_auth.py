import os
import logging
import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

logger = logging.getLogger("google_ads_server")

# Current stable Google Ads API major version (v19 is sunsetted -> 404).
API_VERSION = "v21"

TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPES = ["https://www.googleapis.com/auth/adwords"]


def _get_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def format_customer_id(customer_id: str) -> str:
    """Strip dashes/spaces so the ID is API-ready (e.g. 123-456-7890 -> 1234567890)."""
    return str(customer_id).replace("-", "").replace(" ", "").strip()


def _get_credentials() -> Credentials:
    """Build OAuth credentials purely from environment variables (no config file)."""
    creds = Credentials(
        token=None,
        refresh_token=_get_env("GOOGLE_ADS_REFRESH_TOKEN"),
        client_id=_get_env("GOOGLE_ADS_CLIENT_ID"),
        client_secret=_get_env("GOOGLE_ADS_CLIENT_SECRET"),
        token_uri=TOKEN_URI,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def get_headers_with_auto_token() -> dict:
    """
    Return ready-to-use Google Ads REST headers.
    Refreshes the access token automatically from the refresh token.
    """
    creds = _get_credentials()

    headers = {
        "Authorization": f"Bearer {creds.token}",
        "developer-token": _get_env("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "content-type": "application/json",
    }

    login_customer_id = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
    if login_customer_id:
        headers["login-customer-id"] = format_customer_id(login_customer_id)

    return headers


def execute_gaql(customer_id: str, query: str) -> dict:
    """Execute a GAQL query via the Google Ads REST search endpoint."""
    headers = get_headers_with_auto_token()
    cid = format_customer_id(customer_id)

    url = (
        f"https://googleads.googleapis.com/{API_VERSION}"
        f"/customers/{cid}/googleAds:search"
    )

    response = requests.post(url, headers=headers, json={"query": query}, timeout=60)

    if response.status_code != 200:
        logger.error("Google Ads API error %s: %s", response.status_code, response.text)
        response.raise_for_status()

    return response.json()
