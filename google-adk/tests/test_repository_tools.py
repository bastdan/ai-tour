import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import patch

from google.adk.tools.tool_context import ToolContext

from tools import repository
from tools.repository import list_files, read_file, search_text


class RepositoryToolsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent, prefix=".repo-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / "repository"
        self.root.mkdir()
        self.context = cast(ToolContext, SimpleNamespace(state={"project_path": str(self.root)}))

    def write(self, path: str, text: str) -> Path:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        return target

    def test_list_search_read_and_recursive_globs(self) -> None:
        self.write("README.md", "Header guide\nSecond line\n")
        self.write("src/main/A.java", "package example;\nHEADER token\n")
        self.write("src/main/nested/B.java", "header detail\n")
        self.write("elsewhere/src/main/C.java", "header elsewhere\n")
        listed = list_files("**/*", self.context).splitlines()
        self.assertEqual(listed[:-1], sorted([
            "README.md", "src/main/A.java", "src/main/nested/B.java",
            "elsewhere/src/main/C.java",
        ]))
        self.assertEqual(listed[-1], "4 files; 0 omitted")
        self.assertEqual(search_text("HeAdEr", self.context, "src/main/**/*.java"),
                         "src/main/A.java:2: HEADER token\nsrc/main/nested/B.java:1: header detail\n2 matches")
        self.assertIn("README.md:1: Header guide", search_text("header", self.context))
        self.assertEqual(read_file("README.md", self.context, 2, 2), "2: Second line\n2 lines total")
        self.assertEqual(list_files("*.md", self.context), "README.md\n1 files; 0 omitted")
        self.assertEqual(search_text("absent", self.context), "0 matches")

    def test_list_cap_and_omission_count(self) -> None:
        for index in range(205):
            self.write(f"file-{index:03}.txt", "text")
        lines = list_files("**/*", self.context).splitlines()
        self.assertEqual(len(lines), 201)
        self.assertEqual(lines[0], "file-000.txt")
        self.assertEqual(lines[-2], "file-199.txt")
        self.assertEqual(lines[-1], "205 files; 5 omitted")

    def test_search_and_read_caps_and_counts(self) -> None:
        self.write("many.txt", "\n".join(f"MATCH {index}" for index in range(260)))
        result = search_text("match", self.context).splitlines()
        self.assertEqual(len(result), 51)
        self.assertEqual(result[-1], "260 matches")
        result = read_file("many.txt", self.context, 10, 1000).splitlines()
        self.assertEqual(len(result), 201)
        self.assertEqual(result[0], "10: MATCH 9")
        self.assertEqual(result[-2], "209: MATCH 208")
        self.assertEqual(result[-1], "260 lines total")
        self.assertEqual(read_file("many.txt", self.context, 300, 400), "260 lines total")
        self.assertTrue(read_file("many.txt", self.context, 0, 2).startswith("Refused:"))
        self.assertTrue(read_file("many.txt", self.context, 3, 2).startswith("Refused:"))

    def test_outside_paths_and_symlinks_are_refused_without_opening(self) -> None:
        outside = self.base / "outside.txt"
        outside.write_text("outside secret", encoding="utf-8")
        (self.root / "escape.txt").symlink_to(outside)
        (self.root / "external").symlink_to(self.base, target_is_directory=True)
        for path in ("../outside.txt", str(outside), "escape.txt", "external/outside.txt"):
            with self.subTest(path=path), patch.object(Path, "open", side_effect=AssertionError("must not open")):
                results = [
                    read_file(path, self.context),
                    list_files(path, self.context),
                    search_text("secret", self.context, path),
                ]
            for result in results:
                self.assertIn("Refused: path is outside", result)
                self.assertNotIn("\n", result)
        self.assertEqual(list_files("**/*", self.context), "0 files; 0 omitted")
        self.assertEqual(search_text("secret", self.context), "0 matches")

    def test_skips_excluded_folders_oversized_and_non_utf8_files(self) -> None:
        for folder in (".git", "target", ".venv", "node_modules", "__pycache__", ".hidden", "src/.cache"):
            self.write(f"{folder}/skip.txt", "hidden needle")
            self.assertTrue(read_file(f"{folder}/skip.txt", self.context).startswith("Skipped:"))
        huge = self.write("huge.txt", "x" * (repository.MAX_BYTES + 1))
        (self.root / "binary.dat").write_bytes(b"\xff\xfe")
        self.write("normal.txt", "visible needle")
        self.assertEqual(list_files("**/*", self.context), "normal.txt\n1 files; 0 omitted")
        self.assertEqual(search_text("needle", self.context), "normal.txt:1: visible needle\n1 matches")
        self.assertIn("1 MiB", read_file(huge.name, self.context))
        self.assertIn("not UTF-8", read_file("binary.dat", self.context))
        (self.root / "alias.txt").symlink_to(self.root / "target/skip.txt")
        self.assertIn("excluded folder", read_file("alias.txt", self.context))

    def test_size_boundary_and_inside_file_symlink(self) -> None:
        path = self.write("limit.txt", "x" * repository.MAX_BYTES)
        (self.root / "inside.txt").symlink_to(path)
        self.assertEqual(list_files("*.txt", self.context), "inside.txt\nlimit.txt\n2 files; 0 omitted")
        self.assertTrue(read_file("inside.txt", self.context).endswith("1 lines total"))

    def test_missing_paths_and_context_return_messages(self) -> None:
        self.assertIn("Skipped:", read_file("missing.txt", self.context))
        context = cast(ToolContext, SimpleNamespace(state={}))
        for result in (list_files("**/*", context), search_text("x", context), read_file("x", context)):
            self.assertIn("project_path is not set", result)

    def test_module_has_no_write_or_process_operations_and_tools_are_silent(self) -> None:
        source = Path(repository.__file__).read_text(encoding="utf-8")
        for forbidden in ('"w"', '"a"', "subprocess", "shutil"):
            self.assertNotIn(forbidden, source)
        self.write("data.txt", "text")
        output = io.StringIO()
        with redirect_stdout(output):
            list_files("**/*", self.context)
            search_text("text", self.context)
            read_file("data.txt", self.context)
        self.assertEqual(output.getvalue(), "")


if __name__ == "__main__":
    unittest.main()
