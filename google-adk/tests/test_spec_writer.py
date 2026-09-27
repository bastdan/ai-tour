import asyncio
import io
import os
import re
import tempfile
import unittest
from collections.abc import AsyncGenerator
from contextlib import nullcontext, redirect_stdout
from dataclasses import FrozenInstanceError
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

from google.adk.models import Gemini
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import PrivateAttr

from agents.documentation import build_agent as build_documentation
from agents.implementation_plan import build_agent as build_implementation_plan
from agents.product_owner import build_agent as build_product_owner
from agents.product_owner import build_clarifier
from agents.tech_lead import build_agent as build_tech_lead
from main import (
    PROJECT_DIR,
    main,
    read_need,
    read_project_path,
    read_request,
    run_prompt,
    save_specification,
)
from model.spec_request import SpecRequest
from runner import build_runner
from utils import first_line, one_line, text_content, title_slug, validate_headings
from workflow import build_workflow

TODAY = date(2026, 9, 27)
TEMPLATE = (PROJECT_DIR / "SPEC.md").read_text(encoding="utf-8")
STORY = """Title: Header validation
## User story
As a CSV reader, I want explicit header validation, so that mistakes are clear.
## Acceptance criteria
1. Given duplicate headers, when strict parsing is enabled, then reject them.
## Out of scope
Changing default parsing behaviour.
""".strip()
DOC_QUESTION = "Where are headers parsed and tested?"
PO_QUESTION = "Should an empty header be rejected?"
CLARIFICATION = """Reject empty headers when strict parsing is enabled.
Revised criterion:
1. Given duplicate or empty headers, when strict parsing is enabled, then reject them.
""".strip()
APPROACH = """## Affected files
src/parser.txt:1 — validate headers.
## Implementation steps
1. Add strict validation.
## Edge cases
Empty headers: reject in strict mode (Product Owner).
## Performance considerations
One pass over headers.
## Test strategy
Criterion 1: test duplicate and empty headers in tests/parser.txt (new).
## Open risks
None.
## Clarifications
""" + PO_QUESTION + "\n" + CLARIFICATION
DOCUMENT = TEMPLATE.replace("<feature title>", "Header validation").replace(
    "<project name>", "sample"
).replace("<project path>", "/example/sample").replace("<today>", TODAY.isoformat())
DOCUMENT = re.sub(r"(<!--.*?-->)", r"\1\nRecorded requirement or approach.", DOCUMENT)


def system_instruction(request: LlmRequest) -> str:
    instruction = request.config.system_instruction
    if not isinstance(instruction, str):
        raise TypeError("Expected a text system instruction.")
    return instruction


def responses(request: LlmRequest, name: str) -> list[types.FunctionResponse]:
    return [
        part.function_response
        for content in request.contents
        for part in content.parts or []
        if part.function_response and part.function_response.name == name
    ]


class ScriptedModel(BaseLlm):
    """Run the real ADK flow and tools using only deterministic local responses."""

    failure: str | None = None
    empty: str | None = None
    silent: str | None = None
    po_questions: int = 1
    doc_questions: int = 1
    document: str = DOCUMENT
    doc_answer: str = "## Header handling\nsrc/parser.txt:1 contains the header token."
    _trace: list[str] = PrivateAttr(default_factory=list)
    _requests: dict[str, list[LlmRequest]] = PrivateAttr(default_factory=dict)

    @property
    def trace(self) -> list[str]:
        return self._trace

    @property
    def requests(self) -> dict[str, list[LlmRequest]]:
        return self._requests

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        match = re.search(r"You are the (\w+) agent\.", system_instruction(llm_request))
        if match is None:
            raise AssertionError("Agent identity is missing.")
        name = match.group(1)
        self._trace.append(f"{name}:request")
        snapshot = llm_request.model_copy(update={
            "contents": [content.model_copy(deep=True) for content in llm_request.contents],
            "config": llm_request.config.model_copy(deep=True),
        })
        self._requests.setdefault(name, []).append(snapshot)
        if name == self.failure:
            raise RuntimeError("Simulated model failure")
        if name == self.silent:
            return
        call: types.FunctionCall | None = None
        if name == "tech_lead":
            docs = len(responses(llm_request, "documentation"))
            owners = len(responses(llm_request, "product_owner_clarifier"))
            if docs < self.doc_questions:
                call = types.FunctionCall(name="documentation", args={"request": DOC_QUESTION})
            elif owners < self.po_questions:
                call = types.FunctionCall(name="product_owner_clarifier", args={"request": PO_QUESTION})
        elif name == "documentation" and not responses(llm_request, "search_text"):
            call = types.FunctionCall(name="search_text", args={"query": "header", "glob": "src/**/*.txt"})
        if call is not None:
            call.id = f"{name}-{len(self._requests[name])}"
            yield LlmResponse(
                content=types.Content(role="model", parts=[types.Part(function_call=call)]),
                usage_metadata=types.GenerateContentResponseUsageMetadata(
                    prompt_token_count=1, candidates_token_count=1, total_token_count=2
                ),
            )
            return
        outputs = {
            "product_owner": STORY,
            "product_owner_clarifier": CLARIFICATION,
            "documentation": self.doc_answer,
            "tech_lead": APPROACH,
            "implementation_plan": self.document,
        }
        output = "   " if name == self.empty else outputs[name]
        self._trace.append(f"{name}:done")
        yield LlmResponse(
            content=types.Content(role="model", parts=[
                types.Part(text="private reasoning", thought=True),
                types.Part(text=output),
            ]),
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=1, candidates_token_count=1, total_token_count=2
            ),
        )


class TemporaryProjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent, prefix=".spec-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.project = self.base / "sample"
        (self.project / "src").mkdir(parents=True)
        self.source_text = "header REPOSITORY_CONTENT_MUST_NOT_APPEAR_IN_LOG"
        (self.project / "src/parser.txt").write_text(self.source_text + "\n", encoding="utf-8")
        self.request = SpecRequest("Make header validation explicit.", self.project, TODAY, TEMPLATE)


class InputTests(TemporaryProjectTests):
    def test_blank_need_reprompts_and_trims(self) -> None:
        output = io.StringIO()
        with patch("builtins.input", side_effect=["", " \t ", "  A useful change.  "]) as prompt, redirect_stdout(output):
            self.assertEqual(read_need(), "A useful change.")
        self.assertEqual(output.getvalue().count("A description is required."), 2)
        self.assertEqual(prompt.call_args.args[0], "Describe the change you need, in one paragraph: ")

    def test_project_default_and_invalid_folder_reprompt(self) -> None:
        with patch.dict(os.environ, {"PROJECT_PATH": str(self.project)}), patch("builtins.input", side_effect=[str(self.base / "missing"), ""]), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(read_project_path(), self.project)
        self.assertIn("Enter an existing project directory.", output.getvalue())

    def test_builtin_default_when_environment_is_blank(self) -> None:
        with patch.dict(os.environ, {"PROJECT_PATH": ""}), patch("main.DEFAULT_PROJECT_PATH", self.project), patch("builtins.input", return_value=""):
            self.assertEqual(read_project_path(), self.project)

    def test_relative_project_resolves_and_file_is_rejected(self) -> None:
        relative = os.path.relpath(self.project)
        with patch("builtins.input", side_effect=[str(self.project / "src/parser.txt"), relative]), redirect_stdout(io.StringIO()):
            self.assertEqual(read_project_path(), self.project)

    def test_request_loads_template_after_inputs(self) -> None:
        with patch("builtins.input", side_effect=["  Make headers explicit. ", str(self.project)]):
            request = read_request(today=TODAY)
        self.assertEqual(request.need, "Make headers explicit.")
        self.assertEqual(request.template, TEMPLATE)
        self.assertEqual(request.project_path, self.project)

    def test_missing_template_reports_its_path(self) -> None:
        with patch("builtins.input", side_effect=["A change", str(self.project)]), patch("main.TEMPLATE_PATH", self.base / "missing.md"), self.assertRaisesRegex(RuntimeError, "missing.md"):
            read_request(today=TODAY)

    def test_request_is_frozen_and_state_is_complete(self) -> None:
        self.assertEqual(self.request.to_state(), {
            "need": self.request.need, "project_path": str(self.project),
            "project_name": "sample", "today": "2026-09-27", "spec_template": TEMPLATE,
        })
        with self.assertRaises(FrozenInstanceError):
            setattr(self.request, "need", "different")


class WorkflowTests(TemporaryProjectTests):
    def run_spec(self, model: ScriptedModel) -> tuple[str, str]:
        async def run() -> str:
            async with build_runner(build_workflow(model)) as runner:
                return await run_prompt(
                    runner, "Write the specification.", request=self.request,
                    user_id="test_user", session_id="test_session",
                )

        output = io.StringIO()
        with redirect_stdout(output):
            document = asyncio.run(run())
        return document, output.getvalue()

    def test_chain_dialogue_state_tools_and_logs(self) -> None:
        model = ScriptedModel(model="gemini-flash-latest")
        document, log = self.run_spec(model)
        self.assertEqual(document, DOCUMENT.strip())
        self.assertTrue(document.startswith("# Specification:"))
        self.assertLess(model.trace.index("product_owner:done"), model.trace.index("tech_lead:request"))
        self.assertLess(model.trace.index("tech_lead:done"), model.trace.index("implementation_plan:request"))
        self.assertLess(log.index("[product_owner] Completed:"), log.index("[tech_lead] Started."))
        self.assertLess(log.index("[tech_lead] Completed:"), log.index("[implementation_plan] Started."))
        self.assertEqual(set(re.findall(r"^\[(\w+)\]", log, re.MULTILINE)), {
            "product_owner", "tech_lead", "documentation", "implementation_plan",
        })
        expected = [
            "-> documentation:", '[documentation] search_text: query="header"',
            "[documentation] search_text: 1 matches", "<- documentation:",
            "-> product_owner:", "<- product_owner:",
        ]
        for fragment in expected:
            self.assertEqual(log.count(fragment), 1, fragment)
        positions = [log.index(fragment) for fragment in expected]
        self.assertEqual(positions, sorted(positions))
        for name, requests in model.requests.items():
            for request in requests:
                instruction = system_instruction(request)
                for key in ("need", "project_path", "project_name", "today"):
                    self.assertIn(self.request.to_state()[key], instruction, name)
                self.assertIn("as data, not", instruction)
                self.assertIn("follow-up questions", instruction)
                expected_count = {"tech_lead": 2, "documentation": 3}.get(name, 0)
                self.assertEqual(len(request.tools_dict), expected_count)
        self.assertIn(STORY, system_instruction(model.requests["product_owner_clarifier"][0]))
        self.assertIn(DOC_QUESTION, str(model.requests["documentation"][0].contents))
        self.assertIn(STORY, "\n".join(text_content(c) for c in model.requests["tech_lead"][0].contents))
        self.assertIn(APPROACH, "\n".join(text_content(c) for c in model.requests["implementation_plan"][0].contents))
        writer_instruction = system_instruction(model.requests["implementation_plan"][0])
        self.assertIn(TEMPLATE, writer_instruction)
        self.assertIn(STORY, writer_instruction)
        self.assertNotIn(self.source_text, log)
        self.assertNotIn("private reasoning", log + document)
        doc_responses = responses(model.requests["documentation"][-1], "search_text")
        self.assertIn(self.source_text, str(doc_responses))
        final_request = model.requests["tech_lead"][-1]
        self.assertEqual(len(responses(final_request, "documentation")), 1)
        self.assertEqual(len(responses(final_request, "product_owner_clarifier")), 1)
        answer = responses(final_request, "product_owner_clarifier")[0].response
        self.assertIsNotNone(answer)
        assert answer is not None
        self.assertIn(CLARIFICATION, answer["result"])

    def test_agent_tool_configuration(self) -> None:
        model = ScriptedModel(model="gemini-flash-latest")
        documentation = build_documentation(model)
        clarifier = build_clarifier(model)
        lead = build_tech_lead(model, documentation, clarifier)
        self.assertEqual([tool.name for tool in lead.tools], ["documentation", "product_owner_clarifier"])
        self.assertEqual([tool.name for tool in documentation.tools], ["list_files", "search_text", "read_file"])
        for agent in (build_product_owner(model), clarifier, build_implementation_plan(model)):
            self.assertEqual(agent.tools, [])
        self.assertEqual(build_product_owner(model).output_key, "story")

    def test_sixth_product_question_is_refused_and_run_completes(self) -> None:
        model = ScriptedModel(model="gemini-flash-latest", po_questions=6)
        document, log = self.run_spec(model)
        self.assertTrue(document.startswith("# Specification:"))
        self.assertEqual(len(model.requests["product_owner_clarifier"]), 5)
        self.assertEqual(log.count("Budget spent:"), 1)
        self.assertIn("Budget spent: product_owner (5 of 5). Deciding with what it has.", log)
        answers = responses(model.requests["tech_lead"][-1], "product_owner_clarifier")
        self.assertEqual(len(answers), 6)
        self.assertIn("budget spent", str(answers[-1].response))
        self.assertIn("Decide with what you have", str(answers[-1].response))

    def test_sixteenth_documentation_question_is_refused(self) -> None:
        model = ScriptedModel(model="gemini-flash-latest", doc_questions=16)
        _, log = self.run_spec(model)
        self.assertEqual(model.trace.count("documentation:done"), 15)
        self.assertEqual(log.count("Budget spent:"), 1)
        self.assertIn("documentation (15 of 15)", log)

    def test_budgets_reset_on_a_second_run_in_same_session(self) -> None:
        model = ScriptedModel(model="gemini-flash-latest", po_questions=6)

        async def run_twice() -> None:
            async with build_runner(build_workflow(model)) as runner:
                for _ in range(2):
                    with redirect_stdout(io.StringIO()) as output:
                        await run_prompt(
                            runner, "Write a specification.", request=self.request,
                            user_id="test_user", session_id="test_session",
                        )
                    self.assertEqual(output.getvalue().count("Budget spent:"), 1)

        asyncio.run(run_twice())
        self.assertEqual(model.trace.count("product_owner_clarifier:done"), 10)

    def test_log_details_are_bounded_and_completed_is_one_line(self) -> None:
        model = ScriptedModel(model="gemini-flash-latest", doc_answer="\n\n" + "A" * 180 + "\nSECOND ANSWER LINE")
        _, log = self.run_spec(model)
        self.assertIn("[documentation] Completed: " + "A" * 120 + "…\n", log)
        self.assertNotIn("SECOND ANSWER LINE", log)
        for line in log.splitlines():
            if ": " in line:
                detail = line.split(": ", 1)[1]
                self.assertLessEqual(len(detail), 121)
                if len(detail) == 121:
                    self.assertTrue(detail.endswith("…"))

    def test_failed_product_owner_prevents_later_agents(self) -> None:
        model = ScriptedModel(model="gemini-flash-latest", failure="product_owner")
        with self.assertLogs("google_adk", level="ERROR"), self.assertRaisesRegex(RuntimeError, "product_owner"):
            self.run_spec(model)
        self.assertNotIn("tech_lead", model.requests)
        self.assertNotIn("implementation_plan", model.requests)

    def test_empty_tech_lead_is_rejected_before_writer(self) -> None:
        model = ScriptedModel(model="gemini-flash-latest", empty="tech_lead")
        with self.assertLogs("google_adk", level="ERROR"), self.assertRaisesRegex(RuntimeError, "tech_lead"):
            self.run_spec(model)
        self.assertNotIn("implementation_plan", model.requests)

    def test_silent_writer_is_an_error(self) -> None:
        model = ScriptedModel(model="gemini-flash-latest", silent="implementation_plan")
        with self.assertLogs("google_adk", level="ERROR"), self.assertRaisesRegex(RuntimeError, "implementation_plan"):
            self.run_spec(model)

    def test_missing_or_reordered_heading_rejected_after_workflow(self) -> None:
        documents = [DOCUMENT.replace("## Scope\n", ""), DOCUMENT.replace("## Scope", "## TEMP").replace("## Summary", "## Scope").replace("## TEMP", "## Summary")]
        for document, heading in zip(documents, ("## Scope", "## Summary")):
            with self.subTest(heading=heading), self.assertRaisesRegex(RuntimeError, heading):
                self.run_spec(ScriptedModel(model="gemini-flash-latest", document=document))

    def test_story_is_persisted_in_session(self) -> None:
        async def run() -> None:
            model = ScriptedModel(model="gemini-flash-latest")
            async with build_runner(build_workflow(model)) as runner:
                await run_prompt(
                    runner, "Write it.", request=self.request,
                    user_id="u", session_id="s",
                )
                session = await runner.session_service.get_session(
                    app_name="spec_writer", user_id="u", session_id="s"
                )
                self.assertIsNotNone(session)
                assert session is not None
                self.assertEqual(session.state["story"], STORY)

        with redirect_stdout(io.StringIO()):
            asyncio.run(run())


class OutputTests(TemporaryProjectTests):
    def test_main_saves_named_file_and_prints_saved_last(self) -> None:
        model = ScriptedModel(model="gemini-flash-latest")
        output_dir = self.base / "specs"
        output = io.StringIO()
        with patch("main.build_base_model", return_value=model), patch("main.OUTPUT_DIR", output_dir), patch.dict(os.environ, {"PROJECT_PATH": str(self.project)}), patch("builtins.input", side_effect=[self.request.need, ""]), redirect_stdout(output):
            asyncio.run(main())
        paths = list(output_dir.glob("*.md"))
        self.assertEqual(len(paths), 1)
        self.assertRegex(paths[0].name, r"^\d{8}-\d{4}-header-validation\.md$")
        self.assertEqual(paths[0].read_text(encoding="utf-8"), DOCUMENT.rstrip() + "\n")
        self.assertEqual(output.getvalue().splitlines()[-1], f"Saved: {paths[0]}")
        self.assertEqual(output.getvalue().count("\n" + DOCUMENT.strip()), 1)
        self.assertIn(f"Project: sample ({self.project})", output.getvalue())
        self.assertIn("Model: gemini-flash-latest", output.getvalue())

    def test_save_exact_name_fallback_and_no_overwrite(self) -> None:
        with patch("main.OUTPUT_DIR", self.base / "specs"):
            path = save_specification(DOCUMENT, story="No title", request=self.request, now=datetime(2026, 9, 27, 10, 5))
            self.assertEqual(path.name, "20260927-1005-specification.md")
            with self.assertRaisesRegex(RuntimeError, "Could not save"):
                save_specification(DOCUMENT, story="No title", request=self.request, now=datetime(2026, 9, 27, 10, 5))
        self.assertEqual(path.read_text(encoding="utf-8"), DOCUMENT.rstrip() + "\n")

    def test_invalid_document_is_not_saved(self) -> None:
        output_dir = self.base / "specs"
        with patch("main.OUTPUT_DIR", output_dir), self.assertRaisesRegex(RuntimeError, "## Scope"):
            save_specification(DOCUMENT.replace("## Scope\n", ""), story=STORY, request=self.request, now=datetime.now())
        self.assertFalse(output_dir.exists())

    def test_save_refuses_analysed_folder_and_external_output(self) -> None:
        for output in (self.project / "specs", PROJECT_DIR.parent / "specs"):
            with self.subTest(output=output), patch("main.OUTPUT_DIR", output), self.assertRaises(RuntimeError):
                save_specification(DOCUMENT, story=STORY, request=self.request, now=datetime.now())
            self.assertFalse(output.exists())

    def test_save_refuses_symlink_into_analysed_folder(self) -> None:
        output = self.base / "specs"
        output.symlink_to(self.project, target_is_directory=True)
        with patch("main.OUTPUT_DIR", output), self.assertRaisesRegex(RuntimeError, "analysed project"):
            save_specification(DOCUMENT, story=STORY, request=self.request, now=datetime.now())
        self.assertEqual(list(self.project.glob("*.md")), [])


class ShutdownTests(TemporaryProjectTests):
    def check_shutdown(
        self,
        *,
        failure: bool = False,
        invalid_document: bool = False,
        cancelled: bool = False,
        runner_close_failure: bool = False,
    ) -> None:
        """Exercise real SDK cleanup with scripted requests and no network."""
        model = Gemini(
            model="gemini-flash-latest",
            client_kwargs={"api_key": "offline-test-key", "enterprise": False},
        )
        client = model.api_client
        scripted = ScriptedModel(
            model=model.model,
            failure="product_owner" if failure else None,
            document=DOCUMENT.replace("## Scope\n", "") if invalid_document else DOCUMENT,
        )
        runner = build_runner(build_workflow(model))
        close_runner = runner.close
        close_async_client = client.aio.aclose
        close_sync_client = client.close
        request_loops: list[asyncio.AbstractEventLoop] = []
        cleanup: list[str] = []
        output = io.StringIO()
        main_task: asyncio.Task[None] | None = None

        async def run_main() -> None:
            nonlocal main_task
            main_task = asyncio.current_task()
            await main()

        async def generate(
            current_model: Gemini,
            llm_request: LlmRequest,
            stream: bool = False,
        ) -> AsyncGenerator[LlmResponse, None]:
            self.assertIs(current_model.api_client, client)
            request_loops.append(asyncio.get_running_loop())
            if cancelled:
                assert main_task is not None
                main_task.cancel()
                await asyncio.sleep(0)
                raise asyncio.CancelledError()
            async for response in scripted.generate_content_async(llm_request, stream):
                yield response

        def record_cleanup(name: str) -> None:
            self.assertTrue(request_loops)
            self.assertIs(asyncio.get_running_loop(), request_loops[0])
            self.assertFalse(request_loops[0].is_closed())
            self.assertNotIn("Saved:", output.getvalue())
            cleanup.append(name)

        async def finish_runner() -> None:
            record_cleanup("runner")
            await close_runner()
            if runner_close_failure:
                raise RuntimeError("Runner cleanup failed")

        async def finish_async_client() -> None:
            record_cleanup("async client")
            await close_async_client()

        def finish_sync_client() -> None:
            record_cleanup("sync client")
            close_sync_client()

        expected_error = None
        if failure:
            expected_error = self.assertRaisesRegex(RuntimeError, "product_owner")
        elif invalid_document:
            expected_error = self.assertRaisesRegex(RuntimeError, "## Scope")
        elif cancelled:
            expected_error = self.assertRaises(asyncio.CancelledError)
        elif runner_close_failure:
            expected_error = self.assertRaisesRegex(RuntimeError, "Runner cleanup failed")

        with (
            patch("main.build_base_model", return_value=model),
            patch("main.build_runner", return_value=runner),
            patch("main.OUTPUT_DIR", self.base / "specs"),
            patch("builtins.input", side_effect=[self.request.need, str(self.project)]),
            patch.object(Gemini, "generate_content_async", new=generate),
            patch.object(runner, "close", side_effect=finish_runner),
            patch.object(client.aio, "aclose", side_effect=finish_async_client),
            patch.object(client, "close", side_effect=finish_sync_client),
            redirect_stdout(output),
            self.assertLogs("google_adk", level="WARNING")
            if failure or cancelled else nullcontext(),
            expected_error or nullcontext(),
        ):
            asyncio.run(run_main())

        self.assertEqual(cleanup, ["runner", "async client", "sync client"])
        self.assertTrue(all(loop is request_loops[0] for loop in request_loops))
        self.assertTrue(request_loops[0].is_closed())
        if expected_error:
            self.assertNotIn("Saved:", output.getvalue())
        else:
            self.assertIn("Saved:", output.getvalue().splitlines()[-1])
            self.assertEqual(set(scripted.requests), {
                "product_owner", "tech_lead", "documentation",
                "product_owner_clarifier", "implementation_plan",
            })

    def test_clients_close_on_request_loop_before_saved(self) -> None:
        self.check_shutdown()

    def test_clients_close_after_model_failure(self) -> None:
        self.check_shutdown(failure=True)

    def test_clients_close_after_validation_failure(self) -> None:
        self.check_shutdown(invalid_document=True)

    def test_clients_close_after_cancellation(self) -> None:
        self.check_shutdown(cancelled=True)

    def test_clients_close_even_if_runner_cleanup_fails(self) -> None:
        self.check_shutdown(runner_close_failure=True)


class TextHelperTests(unittest.TestCase):
    def test_slug_normalizes_limits_and_falls_back(self) -> None:
        for story, expected in (("Title: Café / CSV & Headers!", "cafe-csv-headers"), ("Title: ../../escape", "escape"), ("missing", "specification"), ("Title: !!!", "specification"), ("Title: \n## User story", "specification")):
            self.assertEqual(title_slug(story), expected)
        self.assertEqual(len(title_slug("Title: " + "x" * 100)), 60)
        self.assertFalse(title_slug("Title: " + "x" * 59 + " more").endswith("-"))

    def test_one_line_collapses_and_truncates(self) -> None:
        self.assertEqual(one_line("  one\n\t two  "), "one two")
        self.assertEqual(one_line("x" * 120), "x" * 120)
        self.assertEqual(one_line("x" * 121), "x" * 120 + "…")
        self.assertEqual(first_line("\n \n  First  \nSecond"), "First")

    def test_heading_validation_exact_order_and_no_fence(self) -> None:
        validate_headings(DOCUMENT, TEMPLATE)
        for heading in re.findall(r"^## .*", TEMPLATE, re.MULTILINE):
            with self.subTest(heading=heading), self.assertRaisesRegex(RuntimeError, heading):
                validate_headings(DOCUMENT.replace(heading, ""), TEMPLATE)
        with self.assertRaisesRegex(RuntimeError, "Unexpected.*Extra"):
            validate_headings(DOCUMENT + "\n## Extra", TEMPLATE)
        with self.assertRaisesRegex(RuntimeError, "must start"):
            validate_headings("```markdown\n" + DOCUMENT + "\n```", TEMPLATE)

    def test_thought_parts_are_excluded(self) -> None:
        self.assertEqual(text_content(types.Content(parts=[
            types.Part(text="private reasoning", thought=True), types.Part(text=" Visible "),
        ])), "Visible")
        self.assertEqual(text_content(None), "")


if __name__ == "__main__":
    unittest.main()
