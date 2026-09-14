from google.adk import Workflow
from google.adk.models.base_llm import BaseLlm
from google.adk.workflow import JoinNode

from agents.flight_planner import build_agent as build_flight_planner
from agents.plan_writer import build_agent as build_plan_writer
from agents.sights_to_see import build_agent as build_sights_to_see
from agents.weather_forecast import build_agent as build_weather_forecast


def build_workflow(model: BaseLlm) -> Workflow:
    flights = build_flight_planner(model)
    weather = build_weather_forecast(model)
    sights = build_sights_to_see(model)
    writer = build_plan_writer(model)
    research_results = JoinNode(name="research_results")

    return Workflow(
        name="trip_planner",
        edges=[
            ("START", flights, research_results),
            ("START", weather, sights, research_results),
            (weather, research_results),
            (research_results, writer),
        ],
    )
