import json
from typing import Any

from jira_mcp import mcp
from jira_mcp.client import JiraClientError, get_client


@mcp.tool(
    name="jira_get_transitions",
    annotations={
        "title": "Get Issue Transitions",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def jira_get_transitions(issue_key: str) -> str:
    """Get available workflow transitions for a Jira issue.

    Use this to find valid transition IDs before calling jira_transition_issue.

    Args:
        issue_key: The issue key, e.g. "PROJ-123".

    Returns:
        JSON list of available transitions with their IDs and target statuses.
    """
    client = get_client()
    try:
        data = await client.get(f"/rest/api/3/issue/{issue_key}/transitions")
        transitions = []
        for t in data.get("transitions", []):
            to_status = t.get("to", {})
            transitions.append({
                "id": t["id"],
                "name": t["name"],
                "to_status": to_status.get("name"),
                "to_status_category": to_status.get("statusCategory", {}).get("name"),
            })
        return json.dumps({"issue_key": issue_key, "transitions": transitions})
    except JiraClientError as e:
        return f"Error: {e}"


@mcp.tool(
    name="jira_transition_issue",
    annotations={
        "title": "Transition Jira Issue",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def jira_transition_issue(
    issue_key: str,
    transition_id: str,
    comment: str | None = None,
) -> str:
    """Move a Jira issue to a new status via a workflow transition.

    Use jira_get_transitions first to find valid transition IDs.

    Args:
        issue_key: The issue key, e.g. "PROJ-123".
        transition_id: The transition ID (from jira_get_transitions).
        comment: Optional comment to add with the transition.

    Returns:
        Confirmation message on success.
    """
    client = get_client()
    body: dict[str, Any] = {"transition": {"id": transition_id}}
    if comment:
        body["update"] = {
            "comment": [
                {
                    "add": {
                        "body": {
                            "version": 1,
                            "type": "doc",
                            "content": [
                                {
                                    "type": "paragraph",
                                    "content": [{"type": "text", "text": comment}],
                                }
                            ],
                        }
                    }
                }
            ]
        }
    try:
        await client.post(f"/rest/api/3/issue/{issue_key}/transitions", json_body=body)
        return json.dumps({"status": "transitioned", "issue_key": issue_key, "transition_id": transition_id})
    except JiraClientError as e:
        return f"Error: {e}"
