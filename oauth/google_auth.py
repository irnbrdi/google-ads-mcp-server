"""
Google Ads OAuth Authentication - environment-variable based (Langdock/Railway ready).
Keeps the exact public interface expected by oauth/__init__.py and server.py:
    format_customer_id, get_oauth_credentials, get_headers_with_auto_token, execute_gaql
"""
import os
import logging
import requests
from typing import Dict, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/adwords"]
# v19 is sunsetted (-> 404). v21 is a current stable major version.
API_VERSION = "v21"

TOKEN_URI = "https://oauth2.googleapis.com/token"

GOOGLE_ADS_DEVELOPER_TOKEN = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")
GOOGLE_ADS_CLIENT_ID = os.environ.get("GOOGLE_ADS_CLIENT_ID")
GOOGLE_ADS_CLIENT_SECRET = os.environ.get("GOOGLE_ADS_CLIENT_SECRET")
GOOGLE_ADS_REFRESH_TOKEN = os.environ.get("GOOGLE_ADS_REFRESH_TOKEN")


def format_customer_id(customer_id: str) -> str:
    """Format customer ID to 10 digits without dashes."""
    customer_id = str(customer_id)
    customer_id = customer_id.replace('\\"', "").replace('"', "")
    customer_id = "".join(char for char in customer_id if char.isdigit())
    return customer_id.zfill(10)


def get_oauth_credentials():
    """
    Build and refresh OAuth user credentials purely from environment variables.
    No config file / no GOOGLE_ADS_OAUTH_CONFIG_PATH / no interactive flow needed.
    """
    if not GOOGLE_ADS_CLIENT_ID:
        raise ValueError("GOOGLE_ADS_CLIENT_ID environment variable not set")
    if not GOOGLE_ADS_CLIENT_SECRET:
        raise ValueError("GOOGLE_ADS_CLIENT_SECRET environment variable not set")
    if not GOOGLE_ADS_REFRESH_TOKEN:
        raise ValueError("GOOGLE_ADS_REFRESH_TOKEN environment variable not set")

    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_ADS_REFRESH_TOKEN,
        client_id=GOOGLE_ADS_CLIENT_ID,
        client_secret=GOOGLE_ADS_CLIENT_SECRET,
        token_uri=TOKEN_URI,
        scopes=SCOPES,
    )

    logger.info("Refreshing OAuth access token from refresh token")
    creds.refresh(Request())
    logger.info("Token successfully refreshed")
    return creds


def get_headers_with_auto_token() -> Dict[str, str]:
    """Get API headers with an automatically refreshed access token."""
    if not GOOGLE_ADS_DEVELOPER_TOKEN:
        raise ValueError("GOOGLE_ADS_DEVELOPER_TOKEN environment variable not set")

    creds = get_oauth_credentials()

    headers = {
        "Authorization": f"Bearer {creds.token}",
        "Developer-Token": GOOGLE_ADS_DEVELOPER_TOKEN.strip('"').strip("'"),
        "Content-Type": "application/json",
    }
    return headers


def execute_gaql(customer_id: str, query: str, manager_id: str = "") -> Dict[str, Any]:
    """Execute GAQL using the non-streaming search endpoint."""
    headers = get_headers_with_auto_token()
    formatted_customer_id = format_customer_id(customer_id)

    url = (
        f"https://googleads.googleapis.com/{API_VERSION}"
        f"/customers/{formatted_customer_id}/googleAds:search"
    )

    # Manager (MCC) account for login-customer-id: use argument, else env fallback.
    login_cid = manager_id or os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "")
    if login_cid:
        headers["login-customer-id"] = format_customer_id(login_cid)

    payload = {"query": query}
    resp = requests.post(url, headers=headers, json=payload, timeout=60)

    if not resp.ok:
        raise Exception(
            f"Error executing GAQL: {resp.status_code} {resp.reason} - {resp.text}"
        )

    data = resp.json()
    results = data.get("results", [])
    return {
        "results": results,
        "query": query,
        "totalRows": len(results),
    }
