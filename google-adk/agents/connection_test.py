from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types


def build_agent(model: Gemini) -> Agent:
    # ADK's Agent inherits ABC but has no abstract methods and is instantiable.
    return Agent(  # pyright: ignore[reportEmptyAbstractUsage]
        name="connection_test",
        model=model,
        instruction="Answer briefly and follow the user's request.",
        generate_content_config=types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            http_options=types.HttpOptions(timeout=60_000),
        ),
    )
