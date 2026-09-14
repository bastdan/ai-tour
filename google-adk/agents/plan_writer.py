from google.adk.agents import Agent
from google.adk.models.base_llm import BaseLlm

from agents.common import create_agent


def build_agent(model: BaseLlm) -> Agent:
    return create_agent(
        name="plan_writer",
        model=model,
        instruction="""
Your input contains three reports keyed by flight_planner, weather_forecast,
and sights_to_see. Consolidate all three into a readable Markdown travel plan.
Include a trip summary, flight options with verification status, a daily weather
table with forecast status, and a dated day-by-day itinerary with suggested
morning/afternoon/evening activities where appropriate.
Explain how weather influenced the activities. Keep travel days light and honor
verified flight arrival/departure dates, including overnight travel. If flight
times are unknown, explicitly keep those days provisional.
Preserve forecast gaps and provide indoor/outdoor alternatives for those dates.
If a forecast is unavailable, keep its conditions 'Unknown' everywhere in the
plan. Never replace this with expected conditions, seasonal guidance, climate
averages, temperature ranges, sea temperatures, or rain-risk estimates. Copy
each date's verification status from the weather report into the weather table.
Show flight prices only for itineraries verified for BOTH requested travel dates;
for route-only options, keep fare and dated availability 'Unknown'. Never turn
generic route information into a dated flight offer or invent a currency.
Retain missing-flight information and research uncertainty instead of filling
gaps with invented facts. Use only the supplied research and recommendations;
you have no tools and must not claim additional searches or confirmed bookings.
Preserve source URLs supplied in the reports as inline references where useful.
The application will append the collected search sources, so do not add a
separate Sources section. Finish with a short list of practical items to verify,
such as flight availability, the latest weather, and attraction opening hours.
""",
    )
