import os
import sys
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from google.adk.models import Gemini
from google.adk.runners import Runner
from google.genai import types
from google.genai.errors import APIError

from agents.common import grounding_sources, text_content
from runner import build_runner
from workflow import build_workflow


@dataclass(frozen=True)
class TripRequest:
    origin: str
    destination: str
    departure_date: date
    return_date: date
    today: date

    def to_state(self) -> dict[str, str]:
        return {
            "origin": self.origin,
            "destination": self.destination,
            "departure_date": self.departure_date.isoformat(),
            "return_date": self.return_date.isoformat(),
            "today": self.today.isoformat(),
        }


def read_date(label: str, *, default: date, earliest: date) -> date:
    while True:
        value = input(f"{label} (YYYY-MM-DD) [{default.isoformat()}]: ").strip()
        try:
            parsed = date.fromisoformat(value) if value else default
            if value and parsed.isoformat() != value:
                raise ValueError("Use YYYY-MM-DD.")
        except ValueError:
            print("Enter a valid date in YYYY-MM-DD format.")
            continue
        if parsed < earliest:
            print(f"{label} must be on or after {earliest.isoformat()}.")
            continue
        return parsed


def read_trip(*, today: date) -> TripRequest:
    origin = input("Origin [Lisbon]: ").strip() or "Lisbon"
    destination = input("Destination [Rio de Janeiro]: ").strip() or "Rio de Janeiro"
    departure = read_date("Departure date", default=today, earliest=today)
    return_date = read_date(
        "Return date",
        default=today + timedelta(days=7),
        earliest=departure + timedelta(days=1),
    )
    return TripRequest(origin, destination, departure, return_date, today)


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


def run_prompt(
    runner: Runner,
    prompt: str,
    *,
    trip: TripRequest,
    user_id: str,
    session_id: str,
) -> str:
    response = ""
    sources: dict[str, str] = {}
    completed: set[str] = set()
    error: str | None = None
    try:
        for event in runner.run(
            user_id=user_id,
            session_id=session_id,
            new_message=types.Content(role="user", parts=[types.Part(text=prompt)]),
            state_delta=trip.to_state(),
        ):
            name = event.node_info.name or event.author
            if event.error_code:
                error = error or f"{name} failed ({event.error_code})."
            if name in {"flight_planner", "weather_forecast"}:
                sources.update(grounding_sources(event.grounding_metadata))
            if event.is_final_response() and not event.partial:
                text = text_content(event.content)
                if text:
                    completed.add(name)
                    if name == "plan_writer":
                        response = text
    except APIError:
        raise
    except Exception as exc:
        raise RuntimeError(
            error or f"Trip planning failed ({type(exc).__name__})."
        ) from exc
    if error:
        raise RuntimeError(error)
    missing = {"flight_planner", "weather_forecast", "sights_to_see"} - completed
    if missing:
        raise RuntimeError(f"Missing agent output: {', '.join(sorted(missing))}.")
    if not response:
        raise RuntimeError("The plan writer returned no final text response.")
    if sources:
        response += "\n\n## Sources\n" + "\n".join(
            f"- [{title}]({url})" for url, title in sources.items()
        )
    return response


def main() -> None:
    today = datetime.now(UTC).astimezone().date()
    model = build_base_model()
    trip = read_trip(today=today)
    runner = build_runner(build_workflow(model))
    print(f"\nTrip: {trip.origin} → {trip.destination}")
    print(f"Dates: {trip.departure_date} → {trip.return_date}")
    print(f"Model: {model.model}\n", flush=True)
    response = run_prompt(
        runner,
        "Plan the trip described in the supplied trip fields.",
        trip=trip,
        user_id="traveler",
        session_id="trip_session",
    )
    print(f"\n{response}")


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
    except (EOFError, KeyboardInterrupt):
        print("\nTrip planning cancelled.", file=sys.stderr)
        sys.exit(1)
