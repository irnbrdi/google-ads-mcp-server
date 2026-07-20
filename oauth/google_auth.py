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


def get_credentials() -> Credentials:
    """
    Build OAuth credentials purely from environment variables.
    No config file / no GOOGLE_ADS_OAUTH_CONFIG_PATH needed.
    """
    client_id = _get_env("GOOGLE_ADS_CLIENT_ID")
    client_secret = _get_env("GOOGLE_ADS_CLIENT_SECRET")
    refresh_token = _get_env("GOOGLE_ADS_REFRESH_TOKEN")

    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri=TOKEN_URI,
        scopes=SCOPES,
    )

    # Always refresh to obtain a valid access token from the refresh token.
    creds.refresh(Request())
    return creds


def get_headers(creds: Credentials) -> dict:
    """
    Standard headers for Google Ads REST calls.
    login-customer-id is set to the Manager (MCC) account when provided.
    """
    developer_token = _get_env("GOOGLE_ADS_DEVELOPER_TOKEN")

    if not creds.valid:
        creds.refresh(Request())

    headers = {
        "Authorization": f"Bearer {creds.token}",
        "developer-token": developer_token,
        "content-type": "application/json",
    }

    login_customer_id = os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID")
    if login_customer_id:
        headers["login-customer-id"] = login_customer_id.replace("-", "")

    return headers


def search(customer_id: str, query: str) -> dict:
    """
    Execute a GAQL query via the Google Ads REST search endpoint.
    """
    creds = get_credentials()
    headers = get_headers(creds)

    formatted_customer_id = customer_id.replace("-", "")
    url = (
        f"https://googleads.googleapis.com/{API_VERSION}"
        f"/customers/{formatted_customer_id}/googleAds:search"
    )

    response = requests.post(url, headers=headers, json={"query": query}, timeout=60)

    if response.status_code != 200:
        logger.error(
            "Google Ads API error %s: %s", response.status_code, response.text
        )
        response.raise_for_status()

    return response.json()
