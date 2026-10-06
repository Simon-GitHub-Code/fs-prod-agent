"""Registered workflows and agents. Tool names are strings, checked against MCP manifests by a fitness test."""

from pydantic import BaseModel, ConfigDict

from fs_prod_agent.agents.oversight import AGENT_ID, PROMPT_ID
from fs_prod_agent.agents.oversight import EVAL_SUITE as AGENT_EVAL
from fs_prod_agent.agents.oversight import TOOL_NAMES as AGENT_TOOLS
from fs_prod_agent.workflows.mandate_check import (
    EVAL_SUITE as MANDATE_EVAL,
)
from fs_prod_agent.workflows.mandate_check import (
    STEPS as MANDATE_STEPS,
)
from fs_prod_agent.workflows.mandate_check import (
    TOOL_NAMES as MANDATE_TOOLS,
)
from fs_prod_agent.workflows.mandate_check import (
    WORKFLOW_ID as MANDATE_ID,
)
from fs_prod_agent.workflows.performance_pack import (
    EVAL_SUITE as PACK_EVAL,
)
from fs_prod_agent.workflows.performance_pack import (
    STEPS as PACK_STEPS,
)
from fs_prod_agent.workflows.performance_pack import (
    TOOL_NAMES as PACK_TOOLS,
)
from fs_prod_agent.workflows.performance_pack import (
    WORKFLOW_ID as PACK_ID,
)


class WorkflowSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    tool_names: tuple[str, ...]
    eval_suite: str
    steps: tuple[str, ...]


class AgentSpec(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    tool_names: tuple[str, ...]
    eval_suite: str
    prompt_id: str


def workflows() -> list[WorkflowSpec]:
    return [
        WorkflowSpec(id=PACK_ID, tool_names=PACK_TOOLS, eval_suite=PACK_EVAL, steps=PACK_STEPS),
        WorkflowSpec(id=MANDATE_ID, tool_names=MANDATE_TOOLS, eval_suite=MANDATE_EVAL, steps=MANDATE_STEPS),
    ]


def agents() -> list[AgentSpec]:
    return [
        AgentSpec(id=AGENT_ID, tool_names=AGENT_TOOLS, eval_suite=AGENT_EVAL, prompt_id=PROMPT_ID),
    ]


def workflow_by_id(workflow_id: str) -> WorkflowSpec:
    for spec in workflows():
        if spec.id == workflow_id:
            return spec
    raise KeyError(workflow_id)
