from google.adk.agents import Agent
from google.adk.models import Gemini
from google.genai import types


def build_agent(model: Gemini) -> Agent:
    return Agent(
        name="connection_test",
        model=model,
        instruction="Answer briefly and follow the user's request.",
        generate_content_config=types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            http_options=types.HttpOptions(timeout=60_000),
        ),
    )
