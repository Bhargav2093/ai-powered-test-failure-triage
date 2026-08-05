# Capabilities

A detailed inventory of what the AI-Powered Test Failure Triage tool does today. For the
high-level pitch and setup instructions, see the [README](README.md).

## Input formats

Plug-and-play with two industry-standard formats — no custom schema to adopt:

- **JUnit-style XML** (`--junit-xml`) — the `<testsuite>/<testcase>` schema emitted by Maven
  Surefire, TestNG's `JUnitReportReporter`, and `pytest --junitxml`. One parser covers all three
  since they share the same wire format.
- **Allure `*-result.json`** (`--allure-dir`) — parses `status`, `statusDetails.message/trace`,
  and labels (`testClass`, `testMethod`, `package`) directly from Allure's own result files.

Both parsers were built against and tested with a **real captured failure** from the
[Enterprise Hybrid Automation Framework](https://github.com/Bhargav2093/enterprise-hybrid-automation-framework)
— not a hand-written fixture guessing at the schema. A genuine assertion failure was triggered in
that repo, its actual Surefire XML and Allure JSON output were captured, and both parsers were
proven against that real data before being trusted.

## Classification (rule-based, always available)

- Every failure is scanned for exception-type and message signals in its stack trace:
  `StaleElementReferenceException`, `ElementClickInterceptedException`, and Selenium
  `TimeoutException`/`NoSuchElementException` signal **flaky**; `ConnectException`,
  `SocketTimeoutException`, `UnknownHostException`, and connection-refused text signal **infra**.
- **Everything else defaults to `regression`** — the safe default. A real assertion failure is
  never silently relabeled as flaky just because no known signal matched.
- Each classification carries a **confidence** (`high`/`medium`) based on how many independent
  signals matched, not a single brittle string check.
- Matching is case-insensitive and pattern-based, not exact-string, so `timeoutexception` and
  `TimeoutException` both resolve the same way.

## Clustering

- **Never crosses category boundaries** — a flaky failure and a regression are never merged into
  one cluster even if their text happens to be similar.
- Within a category, each failure is reduced to a normalized signature: exception type + top
  stack frame + message with numbers/paths stripped (so `expected [42.50] but found [39.99]` and
  `expected [17.00] but found [12.25]` normalize to the same shape).
- Signatures are vectorized with `TfidfVectorizer` and grouped by cosine-similarity threshold
  (default `0.6`, tunable via `--similarity-threshold`), so one root cause spanning many tests
  surfaces as one triage item instead of dozens of near-duplicate entries.

## LLM root-cause narrator (optional, graceful degradation)

- **The deterministic core never needs an API key.** Classification and clustering are 100%
  rule-based and offline; the LLM layer only adds a nicer, human-readable narrative on top of a
  result that's already fully computed.
- `ANTHROPIC_API_KEY` unset → `narrate_cluster()` returns a clear template-based summary — same
  return type, same call site, zero network calls, zero cost.
- `ANTHROPIC_API_KEY` set → a real request to `claude-opus-5` (overridable via `CLAUDE_MODEL`)
  generates a 2–4 sentence root-cause narrative from the cluster's signature, category, and a
  representative stack trace.
- **Any API failure degrades to the same template** rather than crashing the triage run — a rate
  limit, bad key, or network blip never takes down the whole tool.
- Tested via a mocked Anthropic client for both the success path and the failure-degrades-gracefully
  path, so the full test suite proves the behavior without ever needing a real key or network
  access.

## Reporting

Three formats from one shared data model (`build_report_context`), so all three are always in
sync:

- **HTML** — a single self-contained file (`triage-report.html` by default), inline CSS, no
  external assets, no server needed. Color-coded by category, collapsible stack traces, a summary
  card row.
- **JSON** — machine-readable, suited for a CI gate or downstream tooling.
- **Markdown** — PR-comment ready, with a summary table and one section per cluster.

## CLI

`triage` (installed as a console entry point) accepts `--junit-xml` and `--allure-dir` — either,
both, or multiple of each — plus `--format` (`html`/`json`/`markdown`), `--output`, and
`--similarity-threshold`. Exits cleanly with a clear message when no failures are found, rather
than erroring on an empty input.

## Testing

**34 tests**, covering:

- Both parsers against the real captured framework-repo fixture and hand-written synthetic
  fixtures covering flaky/infra/regression variety in one file.
- The classifier's signal-matching, confidence scoring, and the "unknown signal → regression"
  safe-default behavior.
- Clustering's category-boundary rule, similarity threshold behavior, and the invariant that every
  input failure ends up in exactly one output cluster.
- The LLM narrator's no-key template path, mocked-client real-call path, model-override-via-env-var
  behavior, and API-failure-degrades-gracefully path.
- All three report formats' actual rendered output (not just "didn't throw").
- The CLI end-to-end: JUnit input, Allure input, all three output formats, and the empty-input
  case.

**Verified reproducible, not just "tests pass here":** the full suite was re-run from a
completely fresh `git clone` into a scratch directory with a brand-new virtual environment (no
reused state from development) — 34/34 passed. It was also run through the exact PowerShell +
`Activate.ps1` flow a real user would follow, not just via a Python interpreter invoked directly.

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on every push/PR to `develop`:

1. Installs the package with dev dependencies (`pip install -e ".[dev]"`) — proves the package
   installs cleanly, not just that the source directory happens to work.
2. Runs the full pytest suite — deliberately **without** `ANTHROPIC_API_KEY` set, proving the tool
   works with zero API cost, matching how it's designed to run anywhere out of the box.
3. Runs a real CLI smoke test against the bundled fixtures and prints the resulting JSON report.

## Project engineering

- `src/` layout with `pyproject.toml` (setuptools backend), so the package installs and imports
  the same way a published PyPI package would.
- Dataclass-based domain model (`FailureRecord`, `Classification`, `Cluster`, `TriageResult`) —
  immutable where it matters (`frozen=True` on records/classifications), so a classified failure
  can't be silently mutated mid-pipeline.
- Zero custom exception-swallowing outside the two places it's deliberately load-bearing: the LLM
  API-failure fallback, and best-effort overlay/page-source checks — everywhere else, real errors
  surface instead of being hidden.

## Verified locally, not just claimed

Every capability above was exercised with real data before being committed: the real captured
framework-repo failure (both JUnit XML and Allure JSON forms), hand-written synthetic fixtures
covering all three categories, a from-scratch clean-clone reproducibility check, and a PowerShell-
native run matching exactly how a user on this platform would invoke the tool. See the
[README's testing section](README.md#testing) for the reproduction commands.

## Tech stack

Python 3.11+ · `src/` layout · scikit-learn (`TfidfVectorizer`, cosine similarity) · Jinja2 ·
Anthropic SDK (`claude-opus-5`) · pytest + pytest-mock · GitHub Actions
