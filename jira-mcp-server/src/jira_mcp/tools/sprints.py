import json
from typing import Any

from jira_mcp import mcp
from jira_mcp.client import JiraClientError, get_client


@mcp.tool(
    name="jira_list_sprints",
    annotations={
        "title": "List Sprints",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def jira_list_sprints(
    board_id: int,
    state: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> str:
    """List sprints for a Jira agile board.

    Args:
        board_id: The board ID (numeric). Use jira_list_boards to find board IDs.
        state: Optional filter by sprint state: "active", "closed", or "future".
        limit: Maximum number of results (1-50, default 20).
        offset: Starting index for pagination (default 0).

    Returns:
        JSON with sprints, total count, and pagination info.
    """
    client = get_client()
    params: dict[str, Any] = {
        "maxResults": min(limit, 50),
        "startAt": offset,
    }
    if state:
        params["state"] = state
    try:
        data = await client.get(f"/rest/agile/1.0/board/{board_id}/sprint", params=params)
        sprints = []
        for s in data.get("values", []):
            sprints.append({
                "id": s["id"],
                "name": s["name"],
                "state": s.get("state"),
                "start_date": s.get("startDate"),
                "end_date": s.get("endDate"),
                "complete_date": s.get("completeDate"),
                "goal": s.get("goal"),
            })
        total = data.get("total", 0)
        return json.dumps({
            "total": total,
            "count": len(sprints),
            "offset": offset,
            "sprints": sprints,
            "has_more": offset + len(sprints) < total,
            "next_offset": offset + len(sprints) if offset + len(sprints) < total else None,
        })
    except JiraClientError as e:
        return f"Error: {e}"


@mcp.tool(
    name="jira_get_sprint_issues",
    annotations={
        "title": "Get Sprint Issues",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def jira_get_sprint_issues(
    sprint_id: int,
    limit: int = 20,
    offset: int = 0,
) -> str:
    """Get issues assigned to a specific sprint.

    Args:
        sprint_id: The sprint ID (numeric). Use jira_list_sprints to find sprint IDs.
        limit: Maximum number of results (1-50, default 20).
        offset: Starting index for pagination (default 0).

    Returns:
        JSON with issues in the sprint, total count, and pagination info.
    """
    client = get_client()
    try:
        data = await client.get(
            f"/rest/agile/1.0/sprint/{sprint_id}/issue",
            params={
                "maxResults": min(limit, 50),
                "startAt": offset,
            },
        )
        issues = []
        for issue in data.get("issues", []):
            fields = issue.get("fields", {})
            issues.append({
                "key": issue["key"],
                "summary": fields.get("summary"),
                "status": _extract_name(fields.get("status")),
                "assignee": _extract_display_name(fields.get("assignee")),
                "priority": _extract_name(fields.get("priority")),
                "issuetype": _extract_name(fields.get("issuetype")),
            })
        total = data.get("total", 0)
        return json.dumps({
            "total": total,
            "count": len(issues),
            "offset": offset,
            "issues": issues,
            "has_more": offset + len(issues) < total,
            "next_offset": offset + len(issues) if offset + len(issues) < total else None,
        })
    except JiraClientError as e:
        return f"Error: {e}"


def _extract_name(obj: dict[str, Any] | None) -> str | None:
    if obj is None:
        return None
    return obj.get("name") or obj.get("key")


def _extract_display_name(obj: dict[str, Any] | None) -> str | None:
    if obj is None:
        return None
    return obj.get("displayName")
