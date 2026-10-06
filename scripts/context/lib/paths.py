"""Repository paths shared by the pack and the fitness suite."""

from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "src" / "fs_prod_agent"
PACK_DIR = REPO / "docs" / "context"
RULES_PACK = REPO / ".grok" / "rules" / "context-pack.md"
FITNESS = REPO / "tests" / "fitness"
