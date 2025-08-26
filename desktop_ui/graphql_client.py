"""GraphQL client for AI Typing Trainer PySide6 desktop UI.

Handles queries and mutations to /api/library_graphql.
"""

from typing import Any, Dict, Optional, cast

import requests

API_URL = "http://localhost:5000/api/library_graphql"


class GraphQLClient:
    """A client for making GraphQL requests to the API."""

    def __init__(self, api_url: str = API_URL) -> None:
        """Create a GraphQL client instance.

        Args:
            api_url: Base URL for the GraphQL API.
        """
        self.api_url = api_url

    def query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a GraphQL query and return the parsed JSON response.

        Args:
            query: GraphQL query string.
            variables: Optional variables for the query.

        Returns:
            The JSON-decoded response as a dictionary.
        """
        resp = requests.post(self.api_url, json={"query": query, "variables": variables or {}})
        resp.raise_for_status()
        return cast(Dict[str, Any], resp.json())
