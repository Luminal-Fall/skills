from jira_mcp import mcp

# Import all tool modules to register them on the mcp instance
import jira_mcp.tools.issues  # noqa: F401
import jira_mcp.tools.comments  # noqa: F401
import jira_mcp.tools.transitions  # noqa: F401
import jira_mcp.tools.projects  # noqa: F401
import jira_mcp.tools.users  # noqa: F401
import jira_mcp.tools.boards  # noqa: F401
import jira_mcp.tools.sprints  # noqa: F401


def main():
    mcp.run()


if __name__ == "__main__":
    main()
