"""
Google Ads OAuth Authentication - environment variables based
"""

import os
import requests
import logging
from typing import Dict, Any

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/adwords']
API_VERSION = "v17"

GOOGLE_ADS_DEVELOPER_TOKEN = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN")
GOOGLE_ADS_CLIENT_ID = os.environ.get("GOOGLE_ADS_CLIENT_ID")
GOOGLE_ADS_CLIENT_SECRET = os.environ.get("GOOGLE_ADS_CLIENT_SECRET")
GOOGLE_ADS_REFRESH_TOKEN = os.environ.get("GOOGLE_ADS_REFRESH_TOKEN")

def format_customer_id(customer_id: str) -> str:
    customer_id = str(customer_id).replace('\"', '').replace('"', '')
    customer_id = ''.join(c for c in customer_id if c.isdigit())
    return customer_id.zfill(10)

def get_oauth_credentials():
    """Build credentials directly from environment variables."""
    if not all([GOOGLE_ADS_CLIENT_ID, GOOGLE_ADS_CLIENT_SECRET, GOOGLE_ADS_REFRESH_TOKEN]):
        raise ValueError(
            "Missing required environment variables: "
            "GOOGLE_ADS_CLIENT_ID, GOOGLE_ADS_CLIENT_SECRET, GOOGLE_ADS_REFRESH_TOKEN"
        )

    creds = Credentials(
        token=None,
        refresh_token=GOOGLE_ADS_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GOOGLE_ADS_CLIENT_ID,
        client_secret=GOOGLE_ADS_CLIENT_SECRET,
        scopes=SCOPES,
    )

    creds.refresh(Request())
    logger.info("OAuth token refreshed successfully from environment variables")
    return creds

def get_headers_with_auto_token() -> Dict[str, str]:
    if not GOOGLE_ADS_DEVELOPER_TOKEN:
        raise ValueError("GOOGLE_ADS_DEVELOPER_TOKEN environment variable not set")

    creds = get_oauth_credentials()

    return {
        'Authorization': f'Bearer {creds.token}',
        'Developer-Token': GOOGLE_ADS_DEVELOPER_TOKEN.strip('"').strip("'"),
        'Content-Type': 'application/json'
    }

def execute_gaql(customer_id: str, query: str, manager_id: str = "") -> Dict[str, Any]:
    headers = get_headers_with_auto_token()
    formatted_customer_id = format_customer_id(customer_id)
    url = f"https://googleads.googleapis.com/{API_VERSION}/customers/{formatted_customer_id}/googleAds:search"

    if manager_id:
        headers['login-customer-id'] = format_customer_id(manager_id)

    payload = {'query': query}
    resp = requests.post(url, headers=headers, json=payload)

    if not resp.ok:
        raise Exception(f"Error executing GAQL: {resp.status_code} {resp.reason} - {resp.text}")

    data = resp.json()
    results = data.get('results', [])
    return {
        'results': results,
        'query': query,
        'totalRows': len(results),
    }
