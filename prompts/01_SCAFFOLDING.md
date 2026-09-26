# 01 — Scaffolding: agent instruction files for a pre-AI repo

You are working in a clone of **Apache Commons CSV** checked out at tag `rel/commons-csv-1.9.0` (July 2021). The project predates AI coding tools: there is no `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` or any other agent instruction file in the repository or its history. Your job is to add them.

## 1. Goal and limits

Goal: an `AGENTS.md` and a `CLAUDE.md` in each folder listed in section 5, written from what you can read in this repository, with the build configuration adjusted so the project still builds when someone runs it.

Not the goal: refactoring, new features, Javadoc fixes, formatting, dependency changes, or a `GEMINI.md`. Antigravity reads `AGENTS.md` natively.

Limits:

- The only files you may create are the `AGENTS.md` and `CLAUDE.md` files listed in section 5.
- The only existing file you may edit is `pom.xml`, and only the one `<excludes>` block described in section 7.
- Do not commit. Leave the changes in the working tree for review.
- Do not run the build, the tests or any other tool. Maven and a JDK may not be installed on this machine. Everything you need is in the files.
- Do not write anything you did not verify in this repository. If a fact cannot be confirmed from a file you read, leave it out. Never invent a command, a version number, a rule or a person.

## 2. Order of work

Work in three phases. Stop at the end of phase 1 and phase 3 and wait for approval before continuing.

**Phase 1, read only.** Do not create or edit any file.

1. Read, in this order: `README.md`, `CONTRIBUTING.md`, `pom.xml` (parent artifact and version, `commons.bc.version`, `defaultGoal`, the plugins configured, the `apache-rat-plugin` excludes, the surefire and compiler test excludes), `.github/workflows/maven.yml`, the three files under `src/site/resources/checkstyle/`, the top of `src/changes/changes.xml`, `src/main/java/org/apache/commons/csv/package-info.java`, and the directory listing of `src/test/java/org/apache/commons/csv/` and `src/test/resources/org/apache/commons/csv/`.
2. Answer the questions in section 4 in chat, one line each, naming the file and line that proves each answer. Then stop.

**Phase 2, write.** Create the files in section 5, following the rubric in section 3, the `CLAUDE.md` template in section 6 and the license-check rule in section 7.

**Phase 3, verify.** Do the checks in section 8 by reading the files you wrote, and report. Then stop.

## 3. What a good `AGENTS.md` is

An `AGENTS.md` is loaded into every agent session that opens the folder, so every line costs context. It is a page, not a manual. Four sections, in this order, as H2 headings:

- `## Commands` — how to build, test and run. Exact and copy-pasteable, including what each command needs (JDK, profile, flag). Every command you write here is copied verbatim from `README.md`, `CONTRIBUTING.md`, `pom.xml` or `.github/workflows/maven.yml`; do not compose commands of your own.
- `## Conventions` — only what the code cannot show: what "done" means for a change, where the changelog entry goes and in what shape, compatibility rules, license and Javadoc requirements, naming that a newcomer would get wrong.
- `## Boundaries` — what never to touch, and what to ask a human before doing.
- `## Pointers` — where the deeper documents are. Link, do not paste.

What stays out:

- Anything the code already says. An agent can read `CSVFormat.java`; it does not need a summary of it.
- Tutorials and long procedures.
- Secrets, credentials, personal names.
- Rules you cannot give a reason for.

Length caps: the root `AGENTS.md` at most 80 lines; each nested `AGENTS.md` at most 40 lines. Plain American English, imperative bullets, no marketing words, no emoji.

## 4. Questions the root `AGENTS.md` must answer

Find the answers in the repository. Each one becomes a line, or nothing, in the root file.

1. What single command is the test gate, and which JDK versions does CI run it on?
2. What does a plain `mvn` with no arguments run? (Look for `defaultGoal`.)
3. How is a single test class run?
4. What checks that every file has the Apache license header, and in which Maven phase does it run? What happens to a new file without a header?
5. Where is a change logged, in what XML shape (element, attributes), and what issue-key format do branches and commit messages use?
6. Which released version is the binary-compatibility baseline, and what does that mean for public API in a minor release? (Removing versus deprecating.)
7. What Javadoc tag does new public API carry, and with which value at this point in the project's history?
8. Which style rules would surprise a newcomer? Look at the Checkstyle configuration for rules about tabs, line length, `final` on parameters and local variables, import order, `@author` tags, and braces.
9. Which test framework and version are used, which test classes are excluded from the normal test run, and how are they run instead?
10. Which folders are generated, templated or maintained by tooling rather than by hand, and which hold configuration the build reads?

## 5. Where the pairs go

Create one `AGENTS.md` and one `CLAUDE.md` in each of these eight folders and nowhere else.

| Folder | What its `AGENTS.md` covers |
| --- | --- |
| `/` (repository root) | The full rubric of section 3, answering section 4 |
| `.github/` | The CI workflow and Dependabot: the JDK matrix, the exact command CI runs, that it also covers `workflows/`; never add secrets or tokens here |
| `src/main/java/org/apache/commons/csv/` | Which classes are public API and which are package-private; how `CSVFormat.Builder` and `CSVFormat.Predefined` are meant to be extended; `@since` on new public members; deprecate, never remove; where Checkstyle suppressions live |
| `src/test/java/org/apache/commons/csv/` | JUnit layout and naming; the data-driven `CSVFileParserTest` pattern; which classes are excluded from the normal run and how to run them; that it also covers `perf/` |
| `src/test/java/org/apache/commons/csv/issues/` | One regression test class per JIRA issue, its naming pattern, and how to add one |
| `src/test/resources/org/apache/commons/csv/` | How input and expected-output fixtures pair up in `CSVFileParser/`; the per-issue data folders; that every new fixture needs an entry in the license-check excludes in `pom.xml`; that it covers all its subfolders |
| `src/site/` | The Maven site sources (`site.xml`, `xdoc/`) and, under `resources/`, the Checkstyle, PMD and SpotBugs configuration the build reads; do not edit unless asked; covers its subfolders |
| `src/changes/` | The shape of a `changes.xml` entry and where new entries go; that `release-notes.vm` is a template and `RELEASE-NOTES.txt` is generated from it |

Folders that get no pair, because they have nothing to say beyond their parent: the pass-through package directories (`src/main/java/org/`, `src/main/java/org/apache/`, `src/main/java/org/apache/commons/`, and the same three under `src/test/java/` and `src/test/resources/`), `src/assembly/`, everything under `src/site/resources/`, every subfolder of `src/test/resources/org/apache/commons/csv/`, and `src/test/java/org/apache/commons/csv/perf/`. The nearest `AGENTS.md` above each of them names it in one line.

Shape of a nested `AGENTS.md`:

1. An H1 with the folder path.
2. One sentence saying what the folder holds.
3. A blockquote linking up to the root file with a relative Markdown link, for example from `src/changes/`: `> Repository-wide rules are in [../../AGENTS.md](../../AGENTS.md). This file covers only this folder.` Compute the correct number of `../` for each folder.
4. Only those of the four sections that have something specific to this folder. Omit a section rather than repeat the root.

## 6. `CLAUDE.md`, verbatim

Every `CLAUDE.md` is exactly this one line, so a colleague using Claude Code reads the same file as everyone else:

```
See [AGENTS.md](./AGENTS.md) — that file is the canonical agent guide for <scope>. Keep guidance there, not here, so we have one source of truth.
```

Replace `<scope>` with `this repository` at the root, and with `` the `<relative/path>/` folder `` elsewhere, for example `` the `src/changes/` folder ``. Nothing else goes in `CLAUDE.md`, ever. Guidance lives in `AGENTS.md`.

## 7. The license check

The next time anyone builds this project, it will fail before compiling: the Apache RAT plugin runs in the `validate` phase and rejects any file without an Apache license header, and the Markdown files you are adding have none. This is the first convention in this repo that the code cannot show, and it belongs in the root `## Commands` section.

Do not fix it with `-Drat.skip=true`; that would also stop the check on new Java files. Instead, add these lines inside the existing `<excludes>` element of the `apache-rat-plugin` configuration in `pom.xml` (the block that already lists the test fixtures):

```xml
<!-- Agent instruction files; no license header by design. -->
<exclude>AGENTS.md</exclude>
<exclude>CLAUDE.md</exclude>
<exclude>**/AGENTS.md</exclude>
<exclude>**/CLAUDE.md</exclude>
```

Change nothing else in `pom.xml`. Then state in the root `AGENTS.md` which command is the gate (from the answer to question 1), that the license check runs on every build, and that every new `.java` file needs the header.

## 8. Verification and report

Check all of these by reading files, without running the build or any tool, and report the results in chat:

1. Exactly 16 new files exist (eight `AGENTS.md`, eight `CLAUDE.md`), in the folders of section 5 and nowhere else, and `pom.xml` is the only existing file that changed, by the four `<exclude>` lines and their comment only.
2. Every `CLAUDE.md` is one line and matches the template in section 6, scope included.
3. Every `AGENTS.md` is within the length cap of section 3, has the H2 sections in the order of section 3, and every nested one has a working relative link to the root file.
4. Every command written in any `AGENTS.md` appears verbatim in one of the four source files named in section 3, and every file path mentioned exists in the repository.
5. A closing table with one row per `AGENTS.md`: path, line count, and one phrase for what it covers.

Then stop. A human will read each file and delete every line the code already says.
