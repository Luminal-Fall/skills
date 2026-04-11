import json
from typing import Any

from jira_mcp import mcp
from jira_mcp.client import JiraClientError, get_client


@mcp.tool(
    name="jira_search_users",
    annotations={
        "title": "Search Jira Users",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def jira_search_users(
    query: str,
    limit: int = 20,
    offset: int = 0,
) -> str:
    """Search for Jira users by name or email.

    Useful for finding account IDs needed by jira_assign_issue and jira_create_issue.

    Args:
        query: Search string matching display name, email, or username.
        limit: Maximum number of results (1-50, default 20).
        offset: Starting index for pagination (default 0).

    Returns:
        JSON with matching users including their account IDs and display names.
    """
    client = get_client()
    try:
        data = await client.get(
            "/rest/api/3/user/search",
            params={
                "query": query,
                "maxResults": min(limit, 50),
                "startAt": offset,
            },
        )
        users = []
        for user in data if isinstance(data, list) else []:
            users.append({
                "account_id": user.get("accountId"),
                "display_name": user.get("displayName"),
                "email_address": user.get("emailAddress"),
                "active": user.get("active"),
                "account_type": user.get("accountType"),
            })
        return json.dumps({
            "count": len(users),
            "offset": offset,
            "users": users,
        })
    except JiraClientError as e:
        return f"Error: {e}"


@mcp.tool(
    name="jira_get_myself",
    annotations={
        "title": "Get Current User",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def jira_get_myself() -> str:
    """Get the currently authenticated Jira user's profile.

    Returns:
        JSON with the current user's account ID, display name, email, and timezone.
    """
    client = get_client()
    try:
        data = await client.get("/rest/api/3/myself")
        return json.dumps({
            "account_id": data.get("accountId"),
            "display_name": data.get("displayName"),
            "email_address": data.get("emailAddress"),
            "active": data.get("active"),
            "timezone": data.get("timeZone"),
            "locale": data.get("locale"),
            "account_type": data.get("accountType"),
        })
    except JiraClientError as e:
        return f"Error: {e}"
