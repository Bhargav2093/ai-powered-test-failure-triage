# AI-Powered Test Failure Triage

Ingests failing test output from JUnit-style XML (Maven Surefire, TestNG, pytest `--junitxml`)
and Allure `*-result.json` files, then automatically:

- **Classifies** each failure as `flaky`, `regression`, or `infra` using a deterministic,
  rule-based core (no API key, no network call, always available)
- **Clusters** failures that likely share one root cause using TF-IDF + cosine similarity, so
  a single break spanning many tests shows up as one triage item instead of dozens
- **Narrates** each cluster with a short root-cause summary — a template by default, or a real
  Claude-generated narrative when `ANTHROPIC_API_KEY` is set
- **Reports** the result as a self-contained HTML page, JSON, or Markdown (ready to paste into a
  PR comment)

Built to be plug-and-play with the [Enterprise Hybrid Automation Framework](https://github.com/Bhargav2093/enterprise-hybrid-automation-framework)'s
own Surefire/Allure output, but works with any tool that emits the same JUnit XML schema —
that includes TestNG, pytest, and most CI runners.

## Why deterministic-core-plus-optional-LLM

The classification and clustering pipeline is 100% rule-based and offline — it never calls an
API and never requires a key. The LLM layer only adds a nicer, human-readable narrative on top
of a result that's already fully computed. If `ANTHROPIC_API_KEY` is unset, `narrate_cluster()`
returns a clear template-based summary instead — same return type, same call site, zero cost.
If the API call fails for any reason (rate limit, network, bad key), it degrades to the same
template rather than crashing the whole triage run.

## Install

Requires Python 3.11+.

```bash
python -m venv .venv
.venv/Scripts/activate          # .venv/bin/activate on macOS/Linux
pip install -e ".[dev]"
```

## Usage

```bash
# Point it at JUnit-style XML (Surefire, TestNG, pytest --junitxml)
triage --junit-xml target/surefire-reports/junitreports/*.xml

# Or at a directory of Allure *-result.json files
triage --allure-dir target/allure-results

# Both at once, and pick a format
triage --junit-xml report1.xml report2.xml --allure-dir allure-results --format markdown

# Real root-cause narratives instead of templates
export ANTHROPIC_API_KEY=sk-ant-...
triage --junit-xml report.xml --format html --output triage-report.html
```

Formats: `html` (default, self-contained single file), `json` (machine-readable, e.g. for a CI
gate), `markdown` (PR-comment ready). Model defaults to `claude-opus-5`; override with
`CLAUDE_MODEL`.

## Architecture

```
src/triage/
├── models.py           # FailureRecord, Classification, Cluster, TriageResult
├── parsers/
│   ├── junit_xml.py    # JUnit/Surefire-style testsuite/testcase XML
│   └── allure_json.py  # Allure *-result.json
├── classify.py          # rule-based: flaky / regression / infra, with confidence
├── cluster.py            # TF-IDF + cosine-similarity grouping within a category
├── llm.py                 # Claude-backed root-cause narrator, graceful no-key fallback
├── report.py               # HTML / JSON / Markdown rendering
└── cli.py                   # `triage` entrypoint
```

**Classification** parses the exception type and message out of each failure's stack trace.
`StaleElementReferenceException`, `ElementClickInterceptedException`, and Selenium
`TimeoutException` signal `flaky`. `ConnectException`, `SocketTimeoutException`,
`UnknownHostException`, and connection-refused text signal `infra`. Everything else defaults to
`regression` — a real assertion failure is never silently relabeled as flaky.

**Clustering** never merges failures across categories, even if their text is similar. Within a
category, each failure is reduced to a normalized signature (exception type + top stack frame +
message with numbers/paths stripped), vectorized with `TfidfVectorizer`, and grouped by
cosine-similarity threshold (default `0.6`, tune with `--similarity-threshold`).

## Testing

```bash
pytest -v
```

34 tests cover both parsers against a **real captured failure** from the Enterprise Hybrid
Automation Framework repo (`tests/fixtures/real_framework_failure/`) plus hand-written synthetic
fixtures covering flaky/infra/regression variety
(`tests/fixtures/synthetic/mixed_failures.xml`), the classifier's signal matching, clustering's
category/similarity rules, the LLM narrator's no-key template path and mocked-client real path
(no API key needed to run the suite), and all three report formats end-to-end via the CLI.

The real fixture was captured by temporarily breaking an assertion in the framework repo,
running `mvn test`, and copying the genuine `TEST-*.xml`/`*-result.json` output — the framework
repo itself was left untouched afterward.

## CI

GitHub Actions runs the full pytest suite plus a CLI smoke test against the bundled fixtures on
every push/PR — no `ANTHROPIC_API_KEY` required, matching how the tool is designed to run
anywhere out of the box.
