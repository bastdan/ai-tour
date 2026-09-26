# 02 — Plan mode: developer documentation in minimal HTML

You are working in a clone of **Apache Commons CSV** checked out at tag `rel/commons-csv-1.9.0` (July 2021). The repository has a Maven site and Javadoc, but no documentation written for a developer who is about to change the code. Your job is to plan that documentation, get the plan approved, and then write it.

## 1. Goal and limits

Goal: a `docs/` folder at the repository root holding a small set of HTML pages that a developer reads, in order, before making a first change to this library. Every statement in them comes from a file in this repository.

If a root `AGENTS.md` exists, its rules apply to this work as well.

Limits:

- Read only until the plan is approved. No file is created or edited before then.
- Do not run the build, the tests or any other tool. Maven and a JDK may not be installed on this machine. Everything you need is in the files.
- The only files you may create are under `docs/`.
- The only existing file you may edit is `pom.xml`, by one line described in section 5.
- Do not commit. Leave the changes in the working tree for review.
- Do not invent anything: no version numbers, dates, counts, timings, names or commands that a file in this repository does not contain. If the repository does not document something, say so on the page in one sentence instead of filling the gap.
- No marketing language. Describe what the code does, not how good it is.

## 2. Work in plan mode

Work in three stages. Stage 2 begins with an interview and ends with a halt for approval.

**Stage 1, inspect.** Read, in this order:

1. `README.md`, `CONTRIBUTING.md`, `BENCHMARK.md`.
2. `pom.xml`: parent artifact and version, `defaultGoal`, `commons.bc.version`, the plugins configured, the `apache-rat-plugin` excludes, the surefire and compiler test excludes.
3. `.github/workflows/maven.yml`.
4. `src/main/java/org/apache/commons/csv/package-info.java`, then the class-level Javadoc and the public method signatures of every class in that package. Read the bodies of `Lexer`, `Token` and the header-handling methods of `CSVParser` and `CSVFormat`.
5. `src/site/xdoc/index.xml` and `src/site/xdoc/user-guide.xml`.
6. `src/site/resources/checkstyle/checkstyle.xml` and the top of `src/changes/changes.xml`.
7. The directory listings of `src/test/java/org/apache/commons/csv/` and `src/test/resources/org/apache/commons/csv/`.

**Stage 2, interview, then plan.**

Before drafting anything, interview me with the `ask_question` tool: one question card at a time, each with a short list of options to pick from (the card adds a free-text field on its own). Ask only about decisions the repository cannot settle and this prompt leaves open. Do not ask anything the files or this prompt already answer. Six questions at most. Suggested topics, in this order:

1. How much Java and Maven knowledge the reader is assumed to have.
2. Whether to keep the nine pages of section 3 or merge or split some of them, and which.
3. How deep `parsing-internals.html` should go: method-level walkthrough or a state overview.
4. Whether the read-path diagram and other plain-text diagrams are wanted.
5. How the pages should relate to the existing Maven site under `src/site/xdoc/`: link to it, summarize it, or ignore it.
6. Any topic I want added or removed.

If the `ask_question` tool is not available in this session, ask the same questions in the chat, one at a time, each with numbered options, and wait for the answer before the next.

Then produce the implementation plan as an artifact for review. It must contain:

- A `Decisions` section that records each interview answer in one line.
- The nine pages of section 3, each with a three-to-five-line outline and the list of source files it draws from.
- The page skeleton you chose under the rules of section 4, shown once as literal markup, so it can be reviewed before any page exists.
- Every gap you found: things a developer would want to know that the repository does not document. Each becomes one sentence on the relevant page, not an invention.
- The one-line change to `pom.xml` from section 5.

Halt. Answer review comments and revise the plan until it is approved.

**Stage 3, implement.** Write the pages in reading order, one page per step, then make the `pom.xml` change. Finish with the checks of section 6 and report them.

## 3. Content structure: the reading order

Nine pages. Each answers one question a developer asks before changing the code, and the pages are ordered the way the questions arise. A reader who follows the order from the first page to the last is ready to make a small change and submit it.

Every page, except the index, opens with two short paragraphs, labelled `Read this if` and `After this page you can`, and closes with a `Next:` link to the following page. The index opens with the description and the reading order instead.

| # | File | Question it answers | Required content | Cap |
| --- | --- | --- | --- | --- |
| 1 | `index.html` | What is this library, and in what order do I read these pages? | A description of the library in three sentences, from `package-info.java`; the ordered list of pages 2 to 9 with one line each | 40 lines |
| 2 | `build.html` | How do I get a working build? | Prerequisites, with the JDK versions taken from the CI matrix; the build and test commands, copied verbatim from `README.md`, `pom.xml` or the CI workflow; what a plain `mvn` runs; the license header check, in which phase it runs and what fails it; the benchmark profile as a pointer to `BENCHMARK.md` | 80 lines |
| 3 | `architecture.html` | How does data flow through the code? | The read path from input to `CSVRecord` through `ExtendedBufferedReader`, `Lexer`, `Token` and `CSVParser`; the write path through `CSVPrinter`; configuration through `CSVFormat`, its `Builder`, `Predefined` and `QuoteMode`; one plain-text diagram; which types are public API and which are package-private | 100 lines |
| 4 | `public-api.html` | Which types may I change, and how carefully? | One heading per public type: its purpose, its key methods by name, and the stability rule that applies (deprecate, never remove in a minor release; `@since` on new members; the binary-compatibility baseline from `pom.xml`) | 120 lines |
| 5 | `parsing-internals.html` | What happens inside the parser and the lexer? | Lexer states and token types; how quotes, escapes and comments are handled; line endings and the byte order mark; how a header is detected or set, and where duplicate header names are rejected. Refer to method names, never to line numbers | 120 lines |
| 6 | `conventions.html` | What does "done" mean here? | The license header; the Checkstyle rules a first-time contributor trips on; Javadoc requirements; the shape of a `changes.xml` entry; the binary-compatibility rule; the issue key in branch names and commit messages. If a root `AGENTS.md` exists, link to it and do not repeat it | 80 lines |
| 7 | `testing.html` | How are the tests organized, and how do I add one? | The test layout and naming; how the fixture files under `CSVFileParser/` pair input with expected output; the one-class-per-issue pattern under `issues/`; which tests are excluded from the normal run and how they are run instead; why a new fixture file needs a license-check exclusion | 80 lines |
| 8 | `making-a-change.html` | How does a small change travel from idea to merged? | An ordered list of steps, from issue to branch, failing test, code, Javadoc, changelog entry, full build and pull request. Each step links to the page that covers it in detail rather than repeating it | 60 lines |
| 9 | `glossary.html` | What do the words in the code mean? | One short entry per term, only for terms that appear in `CSVFormat` or `Constants`: record, header, delimiter, quote, escape, comment marker, null string, byte order mark, trailing delimiter, surrounding spaces, and any other you met while reading | 60 lines |

Rules for all pages:

- No page repeats another. Link to the page that owns the topic.
- Where the repository is silent, write one sentence saying so. Do not guess.
- No numbers the files do not contain: no test counts, build times, download sizes or dates.
- Use the names the code uses. Do not rename concepts to make them friendlier.

## 4. HTML: minimal by design

You choose the markup. These are the constraints:

- Plain semantic HTML that reads well in any browser with no styling applied.
- The smallest markup that carries the content. No wrapper elements, no classes or ids, no CSS, no JavaScript, no images, no fonts, no external resources, no frameworks and no generators.
- The same structure on every page, so a reader learns it once. Show that structure in the plan.
- Relative links only, between the pages in `docs/`.
- Code appears as text, with `<`, `>` and `&` escaped. Code samples are short and are taken or condensed from `user-guide.xml` or from Javadoc examples, never written from imagination.
- Prose in short sentences, one idea each. Headings say what the section contains, not how important it is.

## 5. The license check

The Apache RAT plugin runs in the `validate` phase of every build and rejects any file without an Apache license header. HTML pages with no header would make the next build fail before compiling. Add one line inside the existing `<excludes>` element of the `apache-rat-plugin` configuration in `pom.xml`, next to any agent-file excludes already there:

```xml
<exclude>docs/**</exclude>
```

Change nothing else in `pom.xml`. State on `build.html`, in one sentence, that the `docs/` folder is excluded from the license check and why.

## 6. Verification and report

Check all of these by reading files, without running the build or any tool, and report the results:

1. Nine files exist under `docs/`, named as in section 3, and nothing else was created. `pom.xml` differs by the one line of section 5.
2. Every link in every page points to a file that exists under `docs/`.
3. Every class, method or constant named in the pages exists under `src/main/java`.
4. Every page except the index opens with the two labelled paragraphs and closes with the `Next:` link. The index has the description and the ordered list.
5. Every page uses the structure the plan showed, and contains no CSS, script, image or external reference.
6. Every page is within its line cap.
7. A closing table with one row per page: file, line count, and the question it answers.

Then stop. A human will read the pages and remove anything the code already says.
