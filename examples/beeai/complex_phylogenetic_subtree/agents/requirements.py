from beeai_framework.agents.requirement.requirements.requirement import Rule, requirement


def require_stage_tool_before_final_answer(stage_tool_names: list[str]):
    tool_names = set(stage_tool_names)

    @requirement(name="RequireStageToolBeforeFinalAnswer")
    def require_stage_tool(state, context):
        used_stage_tool = any(
            step.tool is not None
            and step.tool.name in tool_names
            and not step.error
            for step in state.steps
        )
        if used_stage_tool:
            return []

        return [
            Rule(
                target="final_answer",
                allowed=False,
                prevent_stop=True,
                reason=(
                    "You must call one of the stage MCP tools successfully before returning a final answer. "
                    "Do not return paths from memory or prior runs."
                ),
            )
        ]

    return require_stage_tool
