"""LangGraph workflow runner. Unwired until a later slice. The local profile uses FixtureWorkflowRunner."""


def build_workflow() -> None:
    raise NotImplementedError(
        "LangGraph is not installed in this slice. build('local') uses the fixture workflow runner."
    )
