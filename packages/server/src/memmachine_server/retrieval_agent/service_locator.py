"""Factory helpers for retrieval-agent construction."""

from memmachine_server.common.language_model import LanguageModel
from memmachine_server.common.reranker import Reranker
from memmachine_server.retrieval_agent.agents import (
    ChainOfQueryAgent,
    MemMachineAgent,
    SplitQueryAgent,
    ToolSelectAgent,
)
from memmachine_server.retrieval_agent.common.agent_api import (
    AgentToolBase,
    AgentToolBaseParam,
)


def create_retrieval_agent(
    *,
    model: LanguageModel,
    reranker: Reranker,
    agent_name: str = "ToolSelectAgent",
) -> AgentToolBase:
    """Create the configured retrieval-agent strategy."""
    memory_agent = MemMachineAgent(
        AgentToolBaseParam(
            model=None,
            children_tools=[],
            extra_params={},
            reranker=reranker,
        ),
    )
    if agent_name == memory_agent.agent_name:
        return memory_agent

    coq_param = AgentToolBaseParam(
        model=model,
        children_tools=[memory_agent],
        extra_params={},
        reranker=reranker,
    )
    coq_agent = ChainOfQueryAgent(coq_param)

    split_param = AgentToolBaseParam(
        model=model,
        children_tools=[memory_agent, coq_agent],
        extra_params={},
        reranker=reranker,
    )
    split_agent = SplitQueryAgent(split_param)

    tool_select_agent = ToolSelectAgent(
        AgentToolBaseParam(
            model=model,
            children_tools=[split_agent, coq_agent, memory_agent],
            extra_params={"default_tool_name": coq_agent.agent_name},
            reranker=reranker,
        ),
    )
    split_agent.set_tool_selector(tool_select_agent)

    if agent_name == coq_agent.agent_name:
        return coq_agent
    if agent_name == split_agent.agent_name:
        return split_agent
    if agent_name == tool_select_agent.agent_name:
        return tool_select_agent

    return tool_select_agent
