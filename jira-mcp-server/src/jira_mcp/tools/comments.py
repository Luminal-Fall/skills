import json
from typing import Any

from jira_mcp import mcp
from jira_mcp.client import JiraClientError, get_client


@mcp.tool(
    name="jira_get_comments",
    annotations={
        "title": "Get Issue Comments",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def jira_get_comments(
    issue_key: str,
    limit: int = 20,
    offset: int = 0,
    order_by: str = "-created",
) -> str:
    """Get comments on a Jira issue.

    Args:
        issue_key: The issue key, e.g. "PROJ-123".
        limit: Maximum number of comments to return (1-100, default 20).
        offset: Starting index for pagination (default 0).
        order_by: Sort order. Use "-created" for newest first, "+created" for oldest first. Default "-created".

    Returns:
        JSON with comments, total count, and pagination info.
    """
    client = get_client()
    try:
        data = await client.get(
            f"/rest/api/3/issue/{issue_key}/comment",
            params={
                "maxResults": min(limit, 100),
                "startAt": offset,
                "orderBy": order_by,
            },
        )
        comments = []
        for comment in data.get("comments", []):
            comments.append({
                "id": comment["id"],
                "author": _extract_display_name(comment.get("author")),
                "body": _extract_text_from_adf(comment.get("body")),
                "created": comment.get("created"),
                "updated": comment.get("updated"),
            })
        total = data.get("total", 0)
        return json.dumps({
            "total": total,
            "count": len(comments),
            "offset": offset,
            "comments": comments,
            "has_more": offset + len(comments) < total,
            "next_offset": offset + len(comments) if offset + len(comments) < total else None,
        })
    except JiraClientError as e:
        return f"Error: {e}"


@mcp.tool(
    name="jira_add_comment",
    annotations={
        "title": "Add Issue Comment",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def jira_add_comment(issue_key: str, body: str) -> str:
    """Add a comment to a Jira issue.

    Args:
        issue_key: The issue key, e.g. "PROJ-123".
        body: Comment text (plain text, will be converted to Atlassian Document Format).

    Returns:
        JSON with the created comment's ID and details.
    """
    client = get_client()
    adf_body = {
        "version": 1,
        "type": "doc",
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": body}],
            }
        ],
    }
    try:
        data = await client.post(
            f"/rest/api/3/issue/{issue_key}/comment",
            json_body={"body": adf_body},
        )
        return json.dumps({
            "id": data["id"],
            "author": _extract_display_name(data.get("author")),
            "body": body,
            "created": data.get("created"),
        })
    except JiraClientError as e:
        return f"Error: {e}"


def _extract_display_name(obj: dict[str, Any] | None) -> str | None:
    if obj is None:
        return None
    return obj.get("displayName")


def _extract_text_from_adf(adf: dict[str, Any] | None) -> str | None:
    if adf is None:
        return None
    parts: list[str] = []
    for block in adf.get("content", []):
        for inline in block.get("content", []):
            if inline.get("type") == "text":
                parts.append(inline.get("text", ""))
        parts.append("\n")
    return "".join(parts).strip() or None
