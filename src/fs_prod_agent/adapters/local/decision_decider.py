"""Strands Decider HTTP adapter. Unwired until a later slice pins a checkpoint and serves it locally."""


def build_decider() -> None:
    raise NotImplementedError(
        "Strands Decider is not installed in this slice. build('local') uses the fixture decider."
    )
