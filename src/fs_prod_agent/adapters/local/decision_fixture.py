"""Re-export the fixture decider. Tests and the local profile use this, not Decider weights."""

from fs_prod_agent.adapters.local.fakes import FixtureDecision

__all__ = ["FixtureDecision"]
