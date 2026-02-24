import json
import logging

import requests

LOGGER = logging.getLogger("apps.utils")


def get_papertrail_logs(papertrail_api_token: str, system_id: str, query: str):
    """
    Get logs from papertrail as per the passed query.
    """
    url = f"https://papertrailapp.com/api/v1/events/search.json?system_id={system_id}&q={query}"
    headers = {"X-Papertrail-Token": papertrail_api_token}
    response = requests.get(url, headers=headers)
    if response.ok:
        return json.loads(response.content).get("events", [])
    return []
