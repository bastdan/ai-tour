import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.adk.models import Gemini
from google.adk.runners import Runner
from google.genai import types
from google.genai.errors import APIError

from agents.connection_test import build_agent
from runner import build_runner


def load_environment() -> tuple[str, str]:
    _ = load_dotenv(Path(__file__).resolve().with_name(".env"))
    model_name = os.getenv("GOOGLE_MODEL", "").strip()
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not model_name or not api_key or api_key == "<your-value>":
        raise ValueError("Set valid GOOGLE_MODEL and GOOGLE_API_KEY values in .env.")
    return model_name, api_key


def build_base_model() -> Gemini:
    model_name, api_key = load_environment()
    return Gemini(
        model=model_name,
        client_kwargs={"api_key": api_key, "enterprise": False},
    )


def run_prompt(runner: Runner, prompt: str, *, user_id: str, session_id: str) -> str:
    response = ""
    for event in runner.run(
        user_id=user_id,
        session_id=session_id,
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
    return response


def main() -> None:
    model = build_base_model()
    agent = build_agent(model)
    runner = build_runner(agent)
    prompt = "Reply with exactly: Google ADK connection successful."
    print(f"Model: {model.model}\nPrompt: {prompt}")
    response = run_prompt(
        runner,
        prompt,
        user_id="test_user",
        session_id="test_session",
    )
    print(f"Response: {response}")


if __name__ == "__main__":
    try:
        main()
    except APIError as exc:
        print(
            f"Google API request failed (HTTP {exc.code}).",
            "Check your API key, model access, and quota.",
            file=sys.stderr,
        )
        sys.exit(1)
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
