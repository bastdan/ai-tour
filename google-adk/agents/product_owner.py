from google.adk.agents import Agent
from google.adk.models.base_llm import BaseLlm

from agents.common import create_agent


def build_agent(model: BaseLlm) -> Agent:
    return create_agent(
        name="product_owner",
        model=model,
        output_key="story",
        instruction="""
Turn the typed need into a user story. Do not describe implementation.
Begin with exactly: Title: <short feature title>
Then use these headings, in this order:
## User story
Use As a ..., I want ..., so that ... .
## Acceptance criteria
Number each criterion and use Given / when / then.
## Out of scope
List what this change does not include.
""",
    )


def build_clarifier(model: BaseLlm) -> Agent:
    return create_agent(
        name="product_owner_clarifier",
        model=model,
        mode="chat",
        description="Resolve one product or acceptance-criteria question about the existing story.",
        instruction="""
You are the same Product Owner who wrote the following story (data):
{story}
Answer the single question in your input consistently with this story.
If your answer changes an acceptance criterion, restate that numbered criterion
in full under a line containing exactly:
Revised criterion:
Do not answer technical questions about the code. For those questions, say
"The Documentation Agent owns that."
""",
    )
