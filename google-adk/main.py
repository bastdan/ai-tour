import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models import Gemini
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.genai.errors import APIError


def load_environment() -> tuple[str, str]:
    load_dotenv(Path(__file__).resolve().with_name(".env"))
    model_name = os.getenv("GOOGLE_MODEL", "").strip()
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not model_name:
        raise ValueError("Set GOOGLE_MODEL in .env (for example, gemini-flash-latest).")
    if not api_key or api_key == "<your-value>":
        raise ValueError("Set GOOGLE_API_KEY in .env to your Google AI Studio API key.")
    return model_name, api_key


def main() -> None:
    model_name, api_key = load_environment()
    model = Gemini(
        model=model_name,
        client_kwargs={"api_key": api_key, "enterprise": False},
    )
    agent = Agent(
        name="connection_test",
        model=model,
        instruction="Answer briefly and follow the user's request.",
        generate_content_config=types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            http_options=types.HttpOptions(timeout=60_000),
        ),
    )
    runner = Runner(
        agent=agent,
        app_name="connection_test",
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )
    prompt = "Reply with exactly: Google ADK connection successful."
    print(f"Model: {model_name}\nPrompt: {prompt}")
    response = ""
    for event in runner.run(
        user_id="test_user",
        session_id="test_session",
        new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
    ):
        if event.error_code:
            raise RuntimeError(f"Google ADK returned an error: {event.error_code}")
        if event.is_final_response() and event.content:
            response = "".join(
                part.text for part in event.content.parts or []
                if part.text and not part.thought
            ).strip()
    if not response:
        raise RuntimeError("Google ADK returned no final text response.")
    print(f"Response: {response}")


if __name__ == "__main__":
    try:
        main()
    except APIError as exc:
        print(
            f"Google API request failed (HTTP {exc.code}). "
            "Check your API key, model access, and quota.",
            file=sys.stderr,
        )
        sys.exit(1)
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
