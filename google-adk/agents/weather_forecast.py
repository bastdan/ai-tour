from google.adk.agents import Agent
from google.adk.models.base_llm import BaseLlm
from google.adk.tools import google_search

from agents.common import create_agent


def build_agent(model: BaseLlm) -> Agent:
    return create_agent(
        name="weather_forecast",
        model=model,
        tools=[google_search],
        instruction="""
Use Google Search to find weather forecasts for the destination city and the
inclusive date range from departure through return. Prefer dated forecasts from
weather services. Report daily conditions, temperatures in Celsius, rain risk,
and relevant storms, wind, heat, or other conditions affecting activities.
Output a daily table: Date | Forecast status | Verified conditions | Source.
Include source links and the forecast's update date when available. Use 'Verified'
only when a source explicitly supports conditions for that exact calendar date.
Match actual calendar dates, not just weekday names. Clearly mark each date or
range without a verifiable forecast as 'Forecast unavailable'. Never invent
daily conditions or substitute seasonal averages for a forecast. When unavailable,
write 'Unknown' in the conditions column. Do not include any typical climate,
monthly averages, estimated temperature ranges, sea temperatures, or seasonal
rain risk anywhere in your answer. Preserve uncertainty and partial coverage so
the next agent can offer flexible options. If every forecast is unavailable,
return the table with every date marked unavailable; that is a complete answer.
""",
    )
