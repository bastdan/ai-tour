import asyncio
import io
import re
import unittest
from collections.abc import AsyncGenerator
from contextlib import redirect_stdout
from datetime import date
from typing import cast, override
from unittest.mock import patch

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import PrivateAttr

from agents.common import text_content
from main import TripRequest, read_trip, run_prompt
from runner import build_runner
from workflow import build_workflow

TODAY = date(2026, 9, 14)
TRIP = TripRequest("Lisbon", "Rio de Janeiro", TODAY, date(2026, 9, 21), TODAY)


def system_instruction(request: LlmRequest) -> str:
    instruction = cast(object, request.config.model_dump()["system_instruction"])
    if not isinstance(instruction, str):
        raise TypeError("Expected a text system instruction.")
    return instruction


class ScriptedModel(BaseLlm):
    """Exercise the real ADK workflow and callbacks without network requests."""

    wait_for_sights: bool = False
    failure: str | None = None
    empty: str | None = None
    silent: str | None = None
    weather: str = "2026-09-14: heavy rain. 2026-09-15: clear skies."
    flights: str = "Flight research: exact dated fares unavailable."
    _trace: list[str] = PrivateAttr(default_factory=list)
    _requests: dict[str, LlmRequest] = PrivateAttr(default_factory=dict)
    _flight_started: asyncio.Event = PrivateAttr(default_factory=asyncio.Event)
    _sights_done: asyncio.Event = PrivateAttr(default_factory=asyncio.Event)

    @property
    def trace(self) -> list[str]:
        return self._trace

    @property
    def requests(self) -> dict[str, LlmRequest]:
        return self._requests

    @override
    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        instruction = system_instruction(llm_request)
        match = re.search(r"You are the (\w+) agent\.", instruction)
        if match is None:
            raise AssertionError("Agent identity is missing from the request.")
        name = match.group(1)
        self._trace.append(f"{name}:start")
        self._requests[name] = llm_request
        if name == self.failure:
            raise RuntimeError("Simulated model failure")
        if name == self.silent:
            return
        if self.wait_for_sights:
            if name == "flight_planner":
                self._flight_started.set()
                _ = await asyncio.wait_for(self._sights_done.wait(), timeout=3)
            elif name == "weather_forecast":
                _ = await asyncio.wait_for(self._flight_started.wait(), timeout=3)

        outputs = {
            "flight_planner": self.flights,
            "weather_forecast": self.weather,
            "sights_to_see": "Sight suggestions: museum in rain, park in clear weather.",
            "plan_writer": "# Travel plan\nThe consolidated itinerary.",
        }
        output = "   " if name == self.empty else outputs[name]
        metadata = None
        if name in {"flight_planner", "weather_forecast"}:
            metadata = types.GroundingMetadata(
                grounding_chunks=[
                    types.GroundingChunk(
                        web=types.GroundingChunkWeb(
                            uri="https://example.com/shared", title="Shared source"
                        )
                    ),
                    types.GroundingChunk(
                        web=types.GroundingChunkWeb(
                            uri=f"https://example.com/{name}", title=f"{name} source"
                        )
                    ),
                ]
            )
        self._trace.append(f"{name}:done")
        yield LlmResponse(
            content=types.Content(role="model", parts=[types.Part(text=output)]),
            grounding_metadata=metadata,
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=1, candidates_token_count=1, total_token_count=2
            ),
        )
        if name == "sights_to_see":
            self._sights_done.set()


class TripInputTests(unittest.TestCase):
    def read(self, values: list[str], *, today: date = TODAY) -> TripRequest:
        with (
            patch("builtins.input", side_effect=values),
            redirect_stdout(io.StringIO()),
        ):
            return read_trip(today=today)

    def test_blank_and_whitespace_defaults(self) -> None:
        for blank in ("", " \t "):
            with self.subTest(blank=blank):
                self.assertEqual(self.read([blank] * 4), TRIP)

    def test_defaults_cross_year_boundary(self) -> None:
        trip = self.read([""] * 4, today=date(2026, 12, 29))
        self.assertEqual(trip.return_date, date(2027, 1, 5))

    def test_custom_cities_and_dates(self) -> None:
        trip = self.read([" Porto ", " Paris ", " 2026-10-01 ", "2026-10-09"])
        self.assertEqual(trip.origin, "Porto")
        self.assertEqual(trip.destination, "Paris")
        self.assertEqual(trip.departure_date, date(2026, 10, 1))
        self.assertEqual(trip.return_date, date(2026, 10, 9))

    def test_invalid_and_past_dates_are_reprompted(self) -> None:
        trip = self.read(
            ["", "", "bad", "2026-02-30", "20260914", "2026-09-13", "", "bad", ""]
        )
        self.assertEqual(trip, TRIP)

    def test_return_must_follow_departure(self) -> None:
        trip = self.read(["", "", "", "2026-09-13", "2026-09-14", "2026-09-15"])
        self.assertEqual(trip.return_date, date(2026, 9, 15))

    def test_default_return_does_not_shift_with_custom_departure(self) -> None:
        trip = self.read(["", "", "2026-09-30", "", "2026-10-01"])
        self.assertEqual(trip.departure_date, date(2026, 9, 30))
        self.assertEqual(trip.return_date, date(2026, 10, 1))


class WorkflowTests(unittest.TestCase):
    def run_trip(self, model: ScriptedModel) -> tuple[str, str]:
        output = io.StringIO()
        with redirect_stdout(output):
            result = run_prompt(
                build_runner(build_workflow(model)),
                "Plan this trip.",
                trip=TRIP,
                user_id="test_user",
                session_id="test_session",
            )
        return result, output.getvalue()

    def test_parallel_dependencies_tools_context_and_final_output(self) -> None:
        model = ScriptedModel(model="gemini-flash-latest", wait_for_sights=True)
        result, progress = self.run_trip(model)
        trace = model.trace
        self.assertLess(
            trace.index("flight_planner:start"), trace.index("weather_forecast:done")
        )
        self.assertLess(
            trace.index("weather_forecast:done"), trace.index("sights_to_see:start")
        )
        self.assertLess(
            trace.index("sights_to_see:done"), trace.index("flight_planner:done")
        )
        self.assertLess(
            trace.index("flight_planner:done"), trace.index("plan_writer:start")
        )
        for name, request in model.requests.items():
            with self.subTest(agent=name):
                instruction = system_instruction(request)
                for value in TRIP.to_state().values():
                    self.assertIn(value, instruction)
                tools = cast(
                    list[dict[str, object]], request.config.model_dump()["tools"] or []
                )
                if name in {"flight_planner", "weather_forecast"}:
                    self.assertEqual(len(tools), 1)
                    self.assertIsNotNone(tools[0]["google_search"])
                else:
                    self.assertEqual(tools, [])
                self.assertEqual(progress.count(f"[{name}] Started."), 1)
                self.assertEqual(progress.count(f"[{name}] Completed."), 1)
        sights_input = str(model.requests["sights_to_see"].contents)
        self.assertIn(model.weather, sights_input)
        self.assertNotIn(model.flights, sights_input)
        writer_input = str(model.requests["plan_writer"].contents)
        for text in (model.weather, model.flights, "Sight suggestions:"):
            self.assertIn(text, writer_input)
        for name in ("flight_planner", "weather_forecast"):
            self.assertIn(f"https://example.com/{name}", writer_input)
        self.assertTrue(result.startswith("# Travel plan"))
        self.assertNotIn("Flight research:", result)
        self.assertNotIn("Sight suggestions:", result)
        self.assertNotIn("heavy rain", progress)
        self.assertEqual(result.count("https://example.com/shared"), 1)
        self.assertIn("## Sources", result)

    def test_forecast_gaps_and_missing_flights_reach_downstream_agents(self) -> None:
        model = ScriptedModel(
            model="gemini-flash-latest",
            weather="2026-09-14: rain. 2026-09-15 to 2026-09-21: Forecast unavailable.",
            flights="No verifiable flights found for these dates.",
        )
        result, _ = self.run_trip(model)
        for name in ("sights_to_see", "plan_writer"):
            self.assertIn(model.weather, str(model.requests[name].contents))
        self.assertIn(model.flights, str(model.requests["plan_writer"].contents))
        self.assertTrue(result.startswith("# Travel plan"))

    def test_failed_research_prevents_writer(self) -> None:
        model = ScriptedModel(model="gemini-flash-latest", failure="weather_forecast")
        with (
            self.assertLogs("google_adk", level="ERROR"),
            self.assertRaisesRegex(RuntimeError, "weather_forecast"),
        ):
            _ = self.run_trip(model)
        self.assertNotIn("sights_to_see:start", model.trace)
        self.assertNotIn("plan_writer:start", model.trace)

    def test_empty_research_is_rejected_before_writer(self) -> None:
        model = ScriptedModel(model="gemini-flash-latest", empty="weather_forecast")
        with (
            self.assertLogs("google_adk", level="ERROR"),
            self.assertRaisesRegex(RuntimeError, "weather_forecast"),
        ):
            _ = self.run_trip(model)
        self.assertNotIn("plan_writer:start", model.trace)

    def test_missing_research_output_is_an_error(self) -> None:
        model = ScriptedModel(model="gemini-flash-latest", silent="flight_planner")
        with (
            self.assertLogs("google_adk", level="ERROR"),
            self.assertRaisesRegex(RuntimeError, "flight_planner"),
        ):
            _ = self.run_trip(model)
        self.assertNotIn("plan_writer:start", model.trace)

    def test_empty_writer_does_not_return_another_agents_answer(self) -> None:
        model = ScriptedModel(model="gemini-flash-latest", empty="plan_writer")
        with (
            self.assertLogs("google_adk", level="ERROR"),
            self.assertRaisesRegex(RuntimeError, "plan_writer"),
        ):
            _ = self.run_trip(model)

    def test_thought_parts_are_not_displayed(self) -> None:
        content = types.Content(
            parts=[
                types.Part(text="private reasoning", thought=True),
                types.Part(text="Plan"),
            ]
        )
        self.assertEqual(text_content(content), "Plan")


if __name__ == "__main__":
    _ = unittest.main()
