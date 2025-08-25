"""GraphQL client for AI Typing Trainer PySide6 desktop UI.

Handles queries and mutations to /api/library_graphql.
"""

from typing import Any, Dict, Optional, cast

import requests

API_URL = "http://localhost:5000/api/library_graphql"


class GraphQLClient:
    """A client for making GraphQL requests to the API."""
    
    def __init__(self, api_url: str = API_URL) -> None:
        self.api_url = api_url

    def query(
        self, query: str, variables: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        resp = requests.post(
            self.api_url, json={"query": query, "variables": variables or {}}
        )
        resp.raise_for_status()
        return cast(Dict[str, Any], resp.json())
