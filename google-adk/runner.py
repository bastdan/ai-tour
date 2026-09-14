from google.adk import Workflow
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService


def build_runner(workflow: Workflow) -> Runner:
    return Runner(
        node=workflow,
        app_name="trip_planner",
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )
