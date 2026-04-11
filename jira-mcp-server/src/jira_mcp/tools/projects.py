import json
from typing import Any

from jira_mcp import mcp
from jira_mcp.client import JiraClientError, get_client


@mcp.tool(
    name="jira_list_projects",
    annotations={
        "title": "List Jira Projects",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def jira_list_projects(
    query: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> str:
    """List Jira projects, optionally filtered by name.

    Args:
        query: Optional search string to filter projects by name.
        limit: Maximum number of results (1-50, default 20).
        offset: Starting index for pagination (default 0).

    Returns:
        JSON with projects, total count, and pagination info.
    """
    client = get_client()
    params: dict[str, Any] = {
        "maxResults": min(limit, 50),
        "startAt": offset,
    }
    if query:
        params["query"] = query
    try:
        data = await client.get("/rest/api/3/project/search", params=params)
        projects = []
        for p in data.get("values", []):
            projects.append({
                "key": p["key"],
                "id": p["id"],
                "name": p["name"],
                "style": p.get("style"),
                "project_type_key": p.get("projectTypeKey"),
                "lead": p.get("lead", {}).get("displayName") if p.get("lead") else None,
            })
        total = data.get("total", 0)
        return json.dumps({
            "total": total,
            "count": len(projects),
            "offset": offset,
            "projects": projects,
            "has_more": offset + len(projects) < total,
            "next_offset": offset + len(projects) if offset + len(projects) < total else None,
        })
    except JiraClientError as e:
        return f"Error: {e}"


@mcp.tool(
    name="jira_get_project",
    annotations={
        "title": "Get Jira Project",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def jira_get_project(project_key: str) -> str:
    """Get detailed information about a specific Jira project.

    Args:
        project_key: Project key, e.g. "PROJ".

    Returns:
        JSON with project details including name, lead, description, issue types, and components.
    """
    client = get_client()
    try:
        data = await client.get(f"/rest/api/3/project/{project_key}")
        issue_types = [
            {"name": it["name"], "subtask": it.get("subtask", False)}
            for it in data.get("issueTypes", [])
        ]
        components = [
            {"name": c["name"], "id": c["id"]}
            for c in data.get("components", [])
        ]
        result = {
            "key": data["key"],
            "id": data["id"],
            "name": data["name"],
            "description": data.get("description"),
            "lead": data.get("lead", {}).get("displayName") if data.get("lead") else None,
            "project_type_key": data.get("projectTypeKey"),
            "style": data.get("style"),
            "issue_types": issue_types,
            "components": components,
        }
        return json.dumps(result)
    except JiraClientError as e:
        return f"Error: {e}"
