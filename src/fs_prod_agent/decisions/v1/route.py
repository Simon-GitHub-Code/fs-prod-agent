from fs_prod_agent.decisions.contract import Question

VERSION = "v1"

INGRESS_QUESTIONS: list[Question] = [
    Question(
        id="route",
        version=VERSION,
        type="choice",
        instructions="Which execution path should handle this request?",
        criteria={
            "workflow": "A known deterministic procedure can answer it.",
            "agent": "The request needs open-ended retrieval and reasoning.",
            "clarify": "The request is underspecified and a person should be asked.",
            "refuse": "The request asks for an action this system does not perform.",
        },
    ),
    Question(
        id="workflow_id",
        version=VERSION,
        type="choice",
        instructions="If a workflow applies, which one?",
        criteria={
            "performance_pack": "Quarterly total-fund performance against the strategic asset allocation.",
            "mandate_check": "Holdings compared with investment policy ranges.",
            "none": "No registered workflow applies.",
        },
    ),
    Question(
        id="materiality",
        version=VERSION,
        type="score",
        instructions="How material is this request to the investment committee?",
        criteria=[
            "informational, no committee attention",
            "notable for the analyst file",
            "belongs in the next committee pack",
            "board-level exception or policy change",
        ],
    ),
    Question(
        id="needs_human",
        version=VERSION,
        type="noul",
        instructions="Does this request require a person to approve it before any further work?",
    ),
]
