# AI-Powered Test Failure Triage

> Status: planning — not yet built.

An AI-assisted tool that ingests failing test results (stack traces, logs, screenshots) from CI
runs and automatically:

- Classifies failures — flaky test vs. real regression vs. environment/infrastructure issue
- Clusters similar failures across a run (and across historical runs) so one root cause doesn't
  show up as 30 separate "failures" to triage
- Suggests a likely root cause and owning component/team based on stack trace and change history
- Cuts down manual triage time for QA/dev teams drowning in CI noise

This is the flagship differentiator of the portfolio — kept standalone rather than folded into
the [Enterprise Hybrid Automation Framework](https://github.com/Bhargav2093/enterprise-hybrid-automation-framework).

## Planned approach

- **Ingestion**: parse JUnit/TestNG/Surefire XML, Allure results, and raw CI logs into a common
  failure record (test name, stack trace, timestamp, environment, screenshot if present).
- **Classification**: an LLM-backed classifier (with a rules-based fallback for common patterns —
  timeouts, stale element, connection refused) labels each failure as flaky / regression / infra.
- **Clustering**: embed stack traces + error messages, cluster similar failures so a single root
  cause across many tests surfaces as one triage item, not dozens.
- **Root-cause suggestion**: correlate failure clusters against recent commits/diffs touching the
  same files or components to suggest a likely owner and cause.
- **Output**: a triage report (and optionally a CI check/PR comment) summarizing clusters, likely
  causes, and confidence — not just a wall of red X's.

Tech stack, LLM provider, and exact input formats to be finalized when implementation starts.
