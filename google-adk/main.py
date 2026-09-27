import asyncio
import os
import sys
from contextlib import AsyncExitStack
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from google.adk.models import Gemini
from google.adk.runners import Runner
from google.genai import types
from google.genai.errors import APIError

from model.spec_request import SpecRequest
from runner import build_runner
from utils import text_content, title_slug, validate_headings
from workflow import build_workflow

PROJECT_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = PROJECT_DIR / "SPEC.md"
OUTPUT_DIR = PROJECT_DIR / "specs"
DEFAULT_PROJECT_PATH = Path("/mnt/c/projects/commons-csv")


def read_need() -> str:
    while True:
        need = input("Describe the change you need, in one paragraph: ").strip()
        if need:
            return need
        print("A description is required.", flush=True)


def read_project_path() -> Path:
    default = os.getenv("PROJECT_PATH", "").strip() or str(DEFAULT_PROJECT_PATH)
    while True:
        value = input(f"Project folder [{default}]: ").strip() or default
        try:
            path = Path(value).expanduser().resolve()
            if path.is_dir():
                return path
        except (OSError, ValueError, RuntimeError):
            pass
        print("Enter an existing project directory.", flush=True)


def read_request(*, today: date) -> SpecRequest:
    need = read_need()
    project_path = read_project_path()
    try:
        template = TEMPLATE_PATH.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise RuntimeError(f"Could not read specification template: {TEMPLATE_PATH}") from exc
    return SpecRequest(need, project_path, today, template)


def load_environment() -> tuple[str, str]:
    _ = load_dotenv(PROJECT_DIR / ".env")
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


async def run_prompt(
    runner: Runner,
    prompt: str,
    *,
    request: SpecRequest,
    user_id: str,
    session_id: str,
) -> str:
    response = ""
    completed: set[str] = set()
    error: str | None = None
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
            state_delta=request.to_state(),
        ):
            name = event.node_info.name or event.author
            if event.error_code:
                error = error or f"{name} failed ({event.error_code})."
            if event.is_final_response() and not event.partial:
                text = text_content(event.content)
                if text:
                    completed.add(name)
                    if name == "implementation_plan":
                        response = text
    except APIError:
        raise
    except Exception as exc:
        raise RuntimeError(error or f"Specification writing failed: {exc}") from exc
    if error:
        raise RuntimeError(error)
    missing = {"product_owner", "tech_lead"} - completed
    if missing:
        raise RuntimeError(f"Missing agent output: {', '.join(sorted(missing))}.")
    if not response:
        raise RuntimeError("The implementation_plan agent returned no final text response.")
    validate_headings(response, request.template)
    return response


def save_specification(
    document: str, *, story: str, request: SpecRequest, now: datetime
) -> Path:
    validate_headings(document, request.template)
    output_dir = OUTPUT_DIR.resolve()
    if not output_dir.is_relative_to(PROJECT_DIR):
        raise RuntimeError("The specification output folder must stay inside google-adk.")
    if output_dir.is_relative_to(request.project_path.resolve()):
        raise RuntimeError("The specification output folder is inside the analysed project.")
    path = output_dir / f"{now:%Y%m%d-%H%M}-{title_slug(story)}.md"
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        # Exclusive creation also refuses existing files and file symlinks.
        with path.open("x", encoding="utf-8") as handle:
            _ = handle.write(document.rstrip() + "\n")
    except OSError as exc:
        raise RuntimeError(f"Could not save specification: {path}: {exc.strerror}") from exc
    return path


async def main() -> None:
    model = build_base_model()
    request = read_request(today=datetime.now(timezone.utc).astimezone().date())
    async with AsyncExitStack() as resources:
        if isinstance(model, Gemini):
            # Runner.close() does not own the shared model's HTTP clients.
            # Close both clients while the loop that served their requests lives.
            client = model.api_client
            resources.callback(client.close)
            await resources.enter_async_context(client.aio)
        runner = await resources.enter_async_context(
            build_runner(build_workflow(model))
        )
        print(f"Project: {request.project_name} ({request.project_path})", flush=True)
        print(f"Model: {model.model}\n", flush=True)
        user_id, session_id = "spec_author", "spec_session"
        response = await run_prompt(
            runner,
            "Write a technical specification for the change described in the supplied need.",
            request=request,
            user_id=user_id,
            session_id=session_id,
        )
        session = await runner.session_service.get_session(
            app_name=runner.app_name, user_id=user_id, session_id=session_id
        )
        story = str(session.state.get("story", "")) if session else ""
    path = save_specification(
        response, story=story, request=request, now=datetime.now().astimezone()
    )
    print(f"\n{response}", flush=True)
    print(f"Saved: {path}", flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
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
    except (EOFError, KeyboardInterrupt):
        print("\nSpecification writing cancelled.", file=sys.stderr)
        sys.exit(1)
