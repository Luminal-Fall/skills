import json
from typing import Any

from jira_mcp import mcp
from jira_mcp.client import JiraClientError, get_client


@mcp.tool(
    name="jira_search_issues",
    annotations={
        "title": "Search Jira Issues",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def jira_search_issues(
    jql: str,
    fields: str = "summary,status,assignee,priority,issuetype,created,updated",
    limit: int = 20,
    offset: int = 0,
) -> str:
    """Search for Jira issues using JQL (Jira Query Language).

    Args:
        jql: JQL query string, e.g. 'project = PROJ AND status = "In Progress"'
        fields: Comma-separated list of fields to return. Default includes common fields.
        limit: Maximum number of results (1-100, default 20).
        offset: Starting index for pagination (default 0).

    Returns:
        JSON with matching issues, total count, and pagination info.
    """
    client = get_client()
    try:
        data = await client.get(
            "/rest/api/3/search",
            params={
                "jql": jql,
                "fields": fields,
                "maxResults": min(limit, 100),
                "startAt": offset,
            },
        )
        issues = []
        for issue in data.get("issues", []):
            fields_data = issue.get("fields", {})
            issues.append({
                "key": issue["key"],
                "summary": fields_data.get("summary"),
                "status": _extract_name(fields_data.get("status")),
                "assignee": _extract_display_name(fields_data.get("assignee")),
                "priority": _extract_name(fields_data.get("priority")),
                "issuetype": _extract_name(fields_data.get("issuetype")),
                "created": fields_data.get("created"),
                "updated": fields_data.get("updated"),
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


@mcp.tool(
    name="jira_get_issue",
    annotations={
        "title": "Get Jira Issue",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def jira_get_issue(
    issue_key: str,
    fields: str | None = None,
) -> str:
    """Get detailed information about a specific Jira issue.

    Args:
        issue_key: The issue key, e.g. "PROJ-123".
        fields: Optional comma-separated list of fields to return. Returns all fields if not specified.

    Returns:
        JSON with full issue details including fields, status, assignee, comments count, etc.
    """
    client = get_client()
    params: dict[str, Any] = {}
    if fields:
        params["fields"] = fields
    try:
        data = await client.get(f"/rest/api/3/issue/{issue_key}", params=params or None)
        fields_data = data.get("fields", {})
        result: dict[str, Any] = {
            "key": data["key"],
            "id": data["id"],
            "self": data["self"],
            "summary": fields_data.get("summary"),
            "description": _extract_text_from_adf(fields_data.get("description")),
            "status": _extract_name(fields_data.get("status")),
            "assignee": _extract_display_name(fields_data.get("assignee")),
            "reporter": _extract_display_name(fields_data.get("reporter")),
            "priority": _extract_name(fields_data.get("priority")),
            "issuetype": _extract_name(fields_data.get("issuetype")),
            "project": _extract_name(fields_data.get("project")),
            "labels": fields_data.get("labels", []),
            "created": fields_data.get("created"),
            "updated": fields_data.get("updated"),
            "resolution": _extract_name(fields_data.get("resolution")),
            "components": [_extract_name(c) for c in fields_data.get("components", [])],
        }
        return json.dumps(result)
    except JiraClientError as e:
        return f"Error: {e}"


@mcp.tool(
    name="jira_create_issue",
    annotations={
        "title": "Create Jira Issue",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def jira_create_issue(
    project_key: str,
    summary: str,
    issue_type: str = "Task",
    description: str | None = None,
    assignee_account_id: str | None = None,
    priority: str | None = None,
    labels: list[str] | None = None,
    parent_key: str | None = None,
) -> str:
    """Create a new Jira issue.

    Args:
        project_key: Project key, e.g. "PROJ".
        summary: Issue title/summary.
        issue_type: Issue type name, e.g. "Task", "Bug", "Story", "Epic". Default "Task".
        description: Optional plain text description. Will be converted to Atlassian Document Format.
        assignee_account_id: Optional Atlassian account ID to assign. Use jira_search_users to find IDs.
        priority: Optional priority name, e.g. "High", "Medium", "Low".
        labels: Optional list of labels.
        parent_key: Optional parent issue key for subtasks, e.g. "PROJ-100".

    Returns:
        JSON with the created issue's key, id, and URL.
    """
    client = get_client()
    fields: dict[str, Any] = {
        "project": {"key": project_key},
        "summary": summary,
        "issuetype": {"name": issue_type},
    }
    if description:
        fields["description"] = _text_to_adf(description)
    if assignee_account_id:
        fields["assignee"] = {"accountId": assignee_account_id}
    if priority:
        fields["priority"] = {"name": priority}
    if labels:
        fields["labels"] = labels
    if parent_key:
        fields["parent"] = {"key": parent_key}

    try:
        data = await client.post("/rest/api/3/issue", json_body={"fields": fields})
        return json.dumps({
            "key": data["key"],
            "id": data["id"],
            "self": data["self"],
        })
    except JiraClientError as e:
        return f"Error: {e}"


@mcp.tool(
    name="jira_update_issue",
    annotations={
        "title": "Update Jira Issue",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def jira_update_issue(
    issue_key: str,
    summary: str | None = None,
    description: str | None = None,
    priority: str | None = None,
    labels: list[str] | None = None,
) -> str:
    """Update fields on an existing Jira issue.

    Args:
        issue_key: The issue key, e.g. "PROJ-123".
        summary: New summary/title.
        description: New plain text description.
        priority: New priority name, e.g. "High", "Medium", "Low".
        labels: New list of labels (replaces existing).

    Returns:
        Confirmation message on success.
    """
    client = get_client()
    fields: dict[str, Any] = {}
    if summary is not None:
        fields["summary"] = summary
    if description is not None:
        fields["description"] = _text_to_adf(description)
    if priority is not None:
        fields["priority"] = {"name": priority}
    if labels is not None:
        fields["labels"] = labels

    if not fields:
        return "Error: No fields provided to update. Specify at least one of: summary, description, priority, labels."

    try:
        await client.put(f"/rest/api/3/issue/{issue_key}", json_body={"fields": fields})
        return json.dumps({"status": "updated", "issue_key": issue_key})
    except JiraClientError as e:
        return f"Error: {e}"


@mcp.tool(
    name="jira_delete_issue",
    annotations={
        "title": "Delete Jira Issue",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def jira_delete_issue(issue_key: str, delete_subtasks: bool = False) -> str:
    """Permanently delete a Jira issue. This action cannot be undone.

    Args:
        issue_key: The issue key, e.g. "PROJ-123".
        delete_subtasks: If True, also delete subtasks. Default False.

    Returns:
        Confirmation message on success.
    """
    client = get_client()
    params: dict[str, Any] = {}
    if delete_subtasks:
        params["deleteSubtasks"] = "true"
    try:
        await client.delete(f"/rest/api/3/issue/{issue_key}")
        return json.dumps({"status": "deleted", "issue_key": issue_key})
    except JiraClientError as e:
        return f"Error: {e}"


@mcp.tool(
    name="jira_assign_issue",
    annotations={
        "title": "Assign Jira Issue",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def jira_assign_issue(issue_key: str, account_id: str | None = None) -> str:
    """Assign or unassign a Jira issue.

    Args:
        issue_key: The issue key, e.g. "PROJ-123".
        account_id: Atlassian account ID to assign. Pass None or omit to unassign. Use jira_search_users to find account IDs.

    Returns:
        Confirmation message on success.
    """
    client = get_client()
    try:
        await client.put(
            f"/rest/api/3/issue/{issue_key}/assignee",
            json_body={"accountId": account_id},
        )
        action = "assigned" if account_id else "unassigned"
        return json.dumps({"status": action, "issue_key": issue_key})
    except JiraClientError as e:
        return f"Error: {e}"


# --- Helpers ---


def _extract_name(obj: dict[str, Any] | None) -> str | None:
    if obj is None:
        return None
    return obj.get("name") or obj.get("key")


def _extract_display_name(obj: dict[str, Any] | None) -> str | None:
    if obj is None:
        return None
    return obj.get("displayName")


def _text_to_adf(text: str) -> dict[str, Any]:
    """Convert plain text to Atlassian Document Format."""
    return {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text}],
            }
        ],
    }


def _extract_text_from_adf(adf: dict[str, Any] | None) -> str | None:
    """Extract plain text from Atlassian Document Format."""
    if adf is None:
        return None
    parts: list[str] = []
    for block in adf.get("content", []):
        for inline in block.get("content", []):
            if inline.get("type") == "text":
                parts.append(inline.get("text", ""))
        parts.append("\n")
    return "".join(parts).strip() or None
