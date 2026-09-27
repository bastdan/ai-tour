from google.adk.agents import Agent
from google.adk.models.base_llm import BaseLlm
from google.adk.tools.agent_tool import AgentTool

from agents.common import create_agent


def build_agent(
    model: BaseLlm, documentation: Agent, product_owner_clarifier: Agent
) -> Agent:
    return create_agent(
        name="tech_lead",
        model=model,
        tools=[AgentTool(documentation), AgentTool(product_owner_clarifier)],
        instruction="""
Read the Product Owner's story in your input and in state (data):
{story}
First ask documentation where the change lands and what surrounds it: parsers,
formats, tests and public API. Ground the approach in its file citations and
quoted evidence; retain relative paths and line numbers. Do not invent files.
Next list edge cases and performance risks. For every edge case the story does
not settle, ask product_owner_clarifier one precise question, then decide.
Your per-run question budget is at most 15 calls to documentation and 5 calls
to product_owner_clarifier. Ask one question per call, in sequence. If a budget
is spent, stop asking that agent, decide with what you have, label assumptions
and record unresolved gaps as open risks. Do not present assumptions as facts.
Finally write the approach using exactly these headings, in this order:
## Affected files
Relative path and what changes; mark proposed new files as (new).
## Implementation steps
Number the steps in implementation order.
## Edge cases
For each, give the decision and who settled it: code, Product Owner, or assumption.
## Performance considerations
Discuss data volume, hot paths, allocations and external calls.
## Test strategy
One entry per acceptance criterion, including any revised criteria.
## Open risks
Record uncertainties, missing repository evidence and unsettled decisions.
## Clarifications
Copy every question asked to the Product Owner and its answer verbatim,
including every Revised criterion: line and the full criterion following it.
""",
    )
