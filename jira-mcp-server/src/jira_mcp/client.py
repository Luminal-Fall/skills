import base64
import json
import os
from typing import Any

import httpx


class JiraClientError(Exception):
    """Raised when a Jira API request fails."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class JiraClient:
    """Async HTTP client for Jira Cloud REST API v3 and Agile API."""

    def __init__(self) -> None:
        self._base_url = os.environ.get("JIRA_URL", "").rstrip("/")
        self._email = os.environ.get("JIRA_EMAIL", "")
        self._api_token = os.environ.get("JIRA_API_TOKEN", "")

        if not self._base_url:
            raise JiraClientError(
                "JIRA_URL environment variable is required. "
                "Set it to your Jira Cloud instance URL, e.g. https://yoursite.atlassian.net"
            )
        if not self._email or not self._api_token:
            raise JiraClientError(
                "JIRA_EMAIL and JIRA_API_TOKEN environment variables are required. "
                "Generate an API token at https://id.atlassian.com/manage-profile/security/api-tokens"
            )

        credentials = base64.b64encode(f"{self._email}:{self._api_token}".encode()).decode()
        self._headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=30.0,
        )

    async def request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[Any]:
        """Make an authenticated request to the Jira API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: API endpoint path (e.g., /rest/api/3/issue/PROJ-1).
            params: Query parameters.
            json_body: JSON request body.

        Returns:
            Parsed JSON response.
        """
        try:
            response = await self._client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json_body,
            )
            response.raise_for_status()

            if response.status_code == 204:
                return {}

            return response.json()

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            try:
                body = e.response.json()
                errors = body.get("errorMessages", [])
                field_errors = body.get("errors", {})
                detail = "; ".join(errors) if errors else json.dumps(field_errors)
            except Exception:
                detail = e.response.text[:500]

            messages = {
                400: f"Bad request: {detail}",
                401: "Authentication failed. Verify JIRA_EMAIL and JIRA_API_TOKEN are correct.",
                403: f"Permission denied. Your account lacks access to this resource. {detail}",
                404: f"Resource not found. {detail}",
                429: "Rate limited by Jira. Wait a moment and try again.",
            }
            message = messages.get(status, f"Jira API error (HTTP {status}): {detail}")
            raise JiraClientError(message, status_code=status) from e

        except httpx.TimeoutException as e:
            raise JiraClientError(
                "Request to Jira timed out. The server may be slow or unreachable."
            ) from e

        except httpx.RequestError as e:
            raise JiraClientError(
                f"Failed to connect to Jira at {self._base_url}. "
                "Verify JIRA_URL is correct and the server is reachable."
            ) from e

    async def get(self, endpoint: str, params: dict[str, Any] | None = None) -> Any:
        return await self.request("GET", endpoint, params=params)

    async def post(self, endpoint: str, json_body: dict[str, Any] | None = None) -> Any:
        return await self.request("POST", endpoint, json_body=json_body)

    async def put(self, endpoint: str, json_body: dict[str, Any] | None = None) -> Any:
        return await self.request("PUT", endpoint, json_body=json_body)

    async def delete(self, endpoint: str) -> Any:
        return await self.request("DELETE", endpoint)


# Module-level singleton
_client: JiraClient | None = None


def get_client() -> JiraClient:
    """Get or create the shared JiraClient instance."""
    global _client
    if _client is None:
        _client = JiraClient()
    return _client
