from google.adk.agents import Agent
from google.adk.models.base_llm import BaseLlm
from google.adk.tools.function_tool import FunctionTool

from agents.common import create_agent
from tools.repository import list_files, read_file, search_text


def build_agent(model: BaseLlm) -> Agent:
    return create_agent(
        name="documentation",
        model=model,
        # AgentTool's child Runner requires a chat/task root in ADK 2.8.
        mode="chat",
        description="Answer a repository question using read-only source and documentation tools.",
        tools=[FunctionTool(list_files), FunctionTool(search_text), FunctionTool(read_file)],
        instruction="""
Answer the question in your input about this repository by listing, searching
and reading files with your tools. Every claim must carry a relative file path
and, where applicable, line numbers. Quote the relevant lines rather than
paraphrasing them. Never describe files you did not read. Never guess from
memory or general knowledge of the library. When the repository does not
contain the answer, say "Not in the repository" and stop.
Return a short Markdown answer. Start with a short summary heading; put source
quotations on subsequent lines so the console summary contains no file contents.
""",
    )
