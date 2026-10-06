from fs_prod_agent.decisions.contract import Question

VERSION = "v1"

TOOL_GATE_QUESTIONS: list[Question] = [
    Question(
        id="tool_gate",
        version=VERSION,
        type="choice",
        instructions="What should happen to this proposed tool call?",
        criteria={
            "proceed": "The call matches the request and is safe to attempt.",
            "guide": "The call needs a correction before it runs.",
            "confirm": "A person should confirm the call before it runs.",
            "deny": "The call should not run.",
        },
    ),
    Question(
        id="arguments_grounded",
        version=VERSION,
        type="noul",
        instructions="Are the tool arguments grounded in the request and the retrieved evidence?",
    ),
    Question(
        id="required_info_missing",
        version=VERSION,
        type="noul",
        instructions="Is information required by this tool still missing?",
    ),
    Question(
        id="call_premature",
        version=VERSION,
        type="noul",
        instructions="Is this tool call premature given the conversation so far?",
    ),
]
