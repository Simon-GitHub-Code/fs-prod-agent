"""Strands agent loop. Unwired until a later slice. The local profile uses FixtureAgentRunner."""


def build_agent() -> None:
    raise NotImplementedError(
        "The Strands agent SDK is not installed in this slice. build('local') uses the fixture agent runner."
    )
