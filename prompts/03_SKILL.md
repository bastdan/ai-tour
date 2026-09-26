# 03 — Skills: a documentation skill that outlives the prompt

You are working in a clone of **Apache Commons CSV** checked out at tag `rel/commons-csv-1.9.0` (July 2021). In the previous activity a `docs/` folder of HTML pages was written by hand from a prompt, and it may or may not exist in this clone. That prompt did one job once. Your job now is to turn it into a skill: a folder, stored next to the code, that creates the documentation when it is missing and updates it when it is stale, in this repository or any other. Running the skill is not part of this job. A human runs it afterwards.

Do this in one turn: read what section 2 lists, write the skill, check it, and hand it over as described in section 8. Do not ask whether to proceed, do not summarize and wait, and do not end your turn before the two files of section 3 exist in the working tree.

## 1. Goal and limits

Goal: a skill folder at `.agents/skills/write-docs/` with two files, `SKILL.md` and `assets/page.html`. When triggered, the skill reads the repository, creates `docs/` if it is absent, updates it if it is present, and styles every page with pico.css loaded from a CDN.

The skill is tool-agnostic. The format is an open convention: a folder, a `SKILL.md` with YAML frontmatter and a Markdown body, and optional `assets/`, `references/` and `scripts/` folders. This IDE discovers skills under `.agents/skills/`; other agents read the same folder from their own path, unchanged. So nothing inside the skill folder may name an IDE, a model or a vendor, and no tool-specific file (rules, manifests, hooks, a `GEMINI.md`, a `.claude/` or `.cursor/` folder) is created.

If a root `AGENTS.md` exists, its rules apply to this work as well.

Limits:

- In this activity, the only files you may create are the two files of the skill folder. The skill, when it runs, may create files only under `docs/`.
- The only existing file you may edit is `pom.xml`, by the lines described in section 6.
- Do not run the build, the tests or any other tool. Maven and a JDK may not be installed on this machine. Everything you need is in the files.
- Do not run the skill you write, do not invoke it by name, and do not create or edit anything under `docs/`. Running it is the human's next step.
- Do not commit. Leave the changes in the working tree for review.
- Do not invent anything: no version numbers, dates, counts, timings, names or commands that a file in this repository does not contain. Where the repository is silent, the page says so in one sentence instead of filling the gap.
- No marketing language, in the skill or in the pages.

## 2. Order of work

Work in three phases, back to back in this turn, with no question and no pause between them. The turn ends after phase 3, with the skill written and not run.

**Phase 1, inspect.** Reading only, and only what is listed here. Do not create or edit any file yet.

1. Read the root `AGENTS.md` if it exists.
2. List `docs/` and read every page in it, if the folder exists. Note the markup structure the pages share.
3. List `.agents/skills/`. Other skills may already be installed there; read one `SKILL.md` as an example of the format and change nothing in it.
4. Read the `apache-rat-plugin` `<excludes>` block in `pom.xml`.
5. State in chat, one line each: whether `docs/` exists and which pages it holds; which markup structure they use; which entries the `<excludes>` block already has. These lines are a record, not a question. Continue to phase 2 in the same turn.

**Phase 2, write the skill.** Create the two files following sections 3, 4 and 5, then make the `pom.xml` change of section 6. This is the deliverable of this prompt: do not end your turn before both files exist.

**Phase 3, check and hand over.** Do the checks of section 8 by reading the files you wrote, then write the hand-over message of section 8 and stop. Do not run the skill.

## 3. The skill folder

Two files and nothing else:

```
.agents/skills/write-docs/
├── SKILL.md
└── assets/page.html
```

A `references/` folder is allowed only if the body of `SKILL.md` would otherwise pass the cap below; if you create one, say so in the phase 2 report.

`SKILL.md` frontmatter:

- `name: write-docs`, equal to the folder name.
- `description:` at most two sentences. First, what the skill does: create or update a `docs/` folder of HTML pages that a developer reads before a first change to the repository. Second, when to use it, in the words a developer would type when asking for the task (documentation, developer docs, onboarding pages, refresh the docs), and one thing it is not for (Javadoc, the `README`, the Maven site under `src/site/`).

`SKILL.md` body, at most 150 lines, written as instructions to a capable colleague who has never seen the procedure. Five H2 sections, in this order:

- `## Outcome` — one paragraph: what exists in `docs/` when the skill is done.
- `## Inputs` — what to read in the repository, in order: the readme and contributing files; the build file; the CI workflow; the package-level and class-level documentation of the main package; the existing `docs/` if any.
- `## Steps` — section 4.
- `## Page rules` — section 5.
- `## Report` — the checks and the table of section 4, steps 6 and 7.

Plain American English, imperative bullets, no emoji.

## 4. What the skill does when it runs

These are the steps the body of `SKILL.md` must contain.

1. Inspect the repository from the Inputs, and `docs/`.
2. Decide the page set. The default shape, in reading order, is: `index`, `build`, `architecture`, `public-api`, `internals`, `conventions`, `testing`, `making-a-change`, `glossary`. Each page answers one question a developer asks before changing the code, and the order follows how the questions arise. Adapt the set to the repository: drop a page whose sources do not exist, add one only for a developer question that no page answers. In this repository `internals` covers the parser and the lexer; in another it covers whatever the core mechanism is.
3. Decide, per page, one of three actions:
   - **create**: the page is absent.
   - **update**: the page exists, and its markup differs from `assets/page.html`, or a statement on it can no longer be verified in the repository, or a source file it draws from has changed.
   - **keep**: the markup already matches and every statement still verifies.
   Pages written by hand in the previous activity take the update path: same file names, content kept wherever it still verifies, markup replaced by the skeleton, one-sentence gap statements kept.
4. Write the pages in reading order, each from `assets/page.html`. Every page except the index opens with two short paragraphs labelled `Read this if` and `After this page you can`, and closes with a `Next:` link to the following page. The index opens with a description of the library and the ordered list of the other pages, one line each.
5. If the build file has a license-header check and `docs/` is not excluded from it, add the exclusion, and state on the build page in one sentence that the folder is excluded and why.
6. Check the pages by reading them: every link points to a file under `docs/`; every class, method or constant named exists under the main source folder; every page except the index has the two labelled paragraphs and the `Next:` link; every page has exactly one `<link>` and no `class`, `id`, `style`, `<script>` or `<img>`; every page is within its cap.
7. Report: a table with one row per page (file, action taken, line count, question it answers), followed by one line per gap sentence written and one line per check of step 6 that failed.

## 5. Page rules

The body of `SKILL.md` carries these rules, and `assets/page.html` embodies them.

- Plain semantic HTML, the smallest markup that carries the content, the same structure on every page.
- Exactly one external resource per page, this line, verbatim, in `<head>`:

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.classless.min.css">
```

- `assets/page.html` holds the skeleton and contains, in order: the doctype, `<html lang="en">`, `<meta charset="utf-8">`, the viewport meta, `<title>`, the link above, then `<body>` with one `<main>` holding a `<header>` with the `<h1>`, one `<section>` per H2 topic, and a `<footer>` with the `Next:` link. The classless build styles `main` as the page container; nothing else is needed for layout, and Pico follows the reader's light or dark preference on its own.
- No classes, no ids, no inline styles, no `<style>`, no `<script>`, no images, no fonts, no other resource from the network, no generators.
- Relative links only, between pages in `docs/`.
- Code appears as text, with `<`, `>` and `&` escaped. Samples are short and are taken or condensed from the repository's own documentation, never written from imagination.
- No page repeats another; link to the page that owns the topic. Where the repository is silent, one sentence says so. No numbers the files do not contain. Use the names the code uses.
- Line caps, as defaults the skill may raise for a repository with more public types, saying so in the report: index 40, build 80, architecture 100, public API 120, internals 120, conventions 80, testing 80, making a change 60, glossary 60.
- Prose in short sentences, one idea each. Headings say what the section contains.

## 6. The license check

The Apache RAT plugin runs in the `validate` phase of every build and rejects any file without an Apache license header. The skill folder and the pages have none. Add, inside the existing `<excludes>` element of the `apache-rat-plugin` configuration in `pom.xml`, only those of these two lines that are not already there:

```xml
<exclude>.agents/**</exclude>
<exclude>docs/**</exclude>
```

Change nothing else in `pom.xml`. The sentence on the build page comes from the skill, per section 4, step 5.

## 7. Why the skill names no tool

Copied to the skills path of another agent, the same folder runs unchanged, because everything it needs is in the folder. That is the reason the skill names no product and has no companion file.

## 8. Verification and hand-over

Check all of these by reading the files you wrote, without running the build, the skill or any tool:

1. The skill folder holds exactly `SKILL.md` and `assets/page.html`, plus `references/` only if it was declared in phase 2. Nothing was created or changed under `docs/`.
2. The frontmatter `name` equals the folder name; the description says what the skill does, when to use it and what it is not for; the body is within the cap with the five sections in the order of section 3; the steps of section 4 and the rules of section 5 are all present.
3. `assets/page.html` contains every element listed in section 5, in that order, and the link line verbatim.
4. No IDE, model or vendor is named anywhere in the folder.
5. `pom.xml` differs only by the lines of section 6 that were missing.

Then end your turn with a hand-over message, and nothing after it:

- One line saying the skill is written and was not run.
- A table with one row per file written or changed: path, line count, and one phrase for what it holds.
- How to run it, in two lines: by name, typing `/write-docs` in the chat of this IDE; or by intent, asking for the documentation in plain words, for example "write the developer docs for this repository, the ones we have need a refresh", which loads the skill if its description matches. Say that the run creates `docs/` if absent and updates it if present, and that the skill reports what it created, updated and kept.
- One line saying that if the plain request does not load the skill, the description is what gets fixed, not the request.

A human will read the skill before running it and remove anything the code already says.
