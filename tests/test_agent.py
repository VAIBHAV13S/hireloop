# Unit Tests for Career Agent Tool Specifications

from hireloop.apps.api.app.services.agent.tools import AGENT_TOOL_DEFINITIONS

def test_agent_tools_schema_validity():
    tool_names = [t["name"] for t in AGENT_TOOL_DEFINITIONS]

    expected = [
        "search_jobs",
        "get_job",
        "get_my_matches",
        "analyze_skill_gap",
        "draft_cover_letter",
        "tailor_resume_bullets",
        "save_application",
        "save_memory",
        "recall_memories",
    ]

    for tool in expected:
        assert tool in tool_names, f"Expected tool '{tool}' not found in definitions"

    for t in AGENT_TOOL_DEFINITIONS:
        assert "description" in t and len(t["description"]) > 5
        assert "parameters" in t and t["parameters"]["type"] == "object"
