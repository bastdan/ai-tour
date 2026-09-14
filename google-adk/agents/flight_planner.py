from google.adk.agents import Agent
from google.adk.models.base_llm import BaseLlm
from google.adk.tools import google_search

from agents.common import create_agent


def build_agent(model: BaseLlm) -> Agent:
    return create_agent(
        name="flight_planner",
        model=model,
        tools=[google_search],
        instruction="""
Use Google Search to research round-trip flights for the exact origin,
destination, departure date, and return date above. Consider airports serving
each city and search both outbound and return travel.
Summarize up to three useful options in a table with airline, airports, stops,
verification status, outbound and return dates/times, fare/currency, and source.
Label each option either 'Dated itinerary verified' or 'Route only; dates unverified'.
Only mark a dated itinerary verified when sources explicitly match BOTH requested
travel dates. Only include a price if it is explicitly for that verified dated
itinerary and state whether it is round-trip or one-way. Otherwise write 'Unknown'
for fare: omit generic route prices, historical fares, ranges, and 'from' prices.
Preserve overnight arrival dates so the itinerary does not schedule activities
in transit. Write 'Unknown' for any other unverified details.
Cite source links when available. Do not invent schedules, fares, availability,
or booking links. General route information must be labeled as such when exact
dated flights cannot be verified. If no suitable results are found, say so and
identify what the traveler still needs to check. Search results are research,
not a confirmed booking or a guarantee of availability. Do not book anything.
""",
    )
