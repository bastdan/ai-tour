from google.adk import Workflow
from google.adk.models.base_llm import BaseLlm

from agents.documentation import build_agent as build_documentation
from agents.implementation_plan import build_agent as build_implementation_plan
from agents.product_owner import build_agent as build_product_owner
from agents.product_owner import build_clarifier
from agents.tech_lead import build_agent as build_tech_lead


def build_workflow(model: BaseLlm) -> Workflow:
    product_owner = build_product_owner(model)
    tech_lead = build_tech_lead(
        model, build_documentation(model), build_clarifier(model)
    )
    implementation_plan = build_implementation_plan(model)
    return Workflow(
        name="spec_writer",
        edges=[("START", product_owner, tech_lead, implementation_plan)],
    )
