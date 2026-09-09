from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService


def build_runner(agent: Agent) -> Runner:
    return Runner(
        agent=agent,
        app_name="connection_test",
        session_service=InMemorySessionService(),
        auto_create_session=True,
    )
