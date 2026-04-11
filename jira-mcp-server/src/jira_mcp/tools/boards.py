import json
from typing import Any

from jira_mcp import mcp
from jira_mcp.client import JiraClientError, get_client


@mcp.tool(
    name="jira_list_boards",
    annotations={
        "title": "List Jira Boards",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def jira_list_boards(
    name: str | None = None,
    board_type: str | None = None,
    project_key: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> str:
    """List Jira agile boards, optionally filtered.

    Args:
        name: Optional filter by board name (partial match).
        board_type: Optional filter by type: "scrum", "kanban", or "simple".
        project_key: Optional filter by project key.
        limit: Maximum number of results (1-50, default 20).
        offset: Starting index for pagination (default 0).

    Returns:
        JSON with boards, total count, and pagination info.
    """
    client = get_client()
    params: dict[str, Any] = {
        "maxResults": min(limit, 50),
        "startAt": offset,
    }
    if name:
        params["name"] = name
    if board_type:
        params["type"] = board_type
    if project_key:
        params["projectKeyOrId"] = project_key
    try:
        data = await client.get("/rest/agile/1.0/board", params=params)
        boards = []
        for b in data.get("values", []):
            boards.append({
                "id": b["id"],
                "name": b["name"],
                "type": b.get("type"),
                "project_key": b.get("location", {}).get("projectKey"),
                "project_name": b.get("location", {}).get("projectName"),
            })
        total = data.get("total", 0)
        return json.dumps({
            "total": total,
            "count": len(boards),
            "offset": offset,
            "boards": boards,
            "has_more": offset + len(boards) < total,
            "next_offset": offset + len(boards) if offset + len(boards) < total else None,
        })
    except JiraClientError as e:
        return f"Error: {e}"


@mcp.tool(
    name="jira_get_board",
    annotations={
        "title": "Get Jira Board",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def jira_get_board(board_id: int) -> str:
    """Get details of a specific Jira agile board.

    Args:
        board_id: The board ID (numeric).

    Returns:
        JSON with board details including name, type, and associated project.
    """
    client = get_client()
    try:
        data = await client.get(f"/rest/agile/1.0/board/{board_id}")
        return json.dumps({
            "id": data["id"],
            "name": data["name"],
            "type": data.get("type"),
            "project_key": data.get("location", {}).get("projectKey"),
            "project_name": data.get("location", {}).get("projectName"),
        })
    except JiraClientError as e:
        return f"Error: {e}"
