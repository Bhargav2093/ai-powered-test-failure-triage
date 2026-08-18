# Test Failure Triage Report

_Generated 2026-08-18 10:17 UTC - 5 failure(s) in 3 cluster(s)_

| Category | Count |
|---|---|
| flaky | 2 |
| regression | 2 |
| infra | 1 |


## [REGRESSION] com.automation.hybrid.tests.api.PostsApiTests.getSinglePostReturnsValidSchema (+1 more)

- **Confidence:** medium
- **Affected tests (2):** `com.automation.hybrid.tests.api.PostsApiTests.getSinglePostReturnsValidSchema`, `com.example.tests.CartTests.cartTotalMatchesLineItems`

2 tests failed with a matching regression signature (representative: com.automation.hybrid.tests.api.PostsApiTests.getSinglePostReturnsValidSchema - expected [999] but found [1]). No known flaky/infra signal matched - treat as a genuine candidate regression until a human rules it out.

## [FLAKY] com.example.tests.LoginTests.loginButtonClickable (+1 more)

- **Confidence:** medium
- **Affected tests (2):** `com.example.tests.LoginTests.loginButtonClickable`, `com.example.tests.CheckoutTests.submitButtonStaleAfterReload`

2 tests failed with a matching flaky signature (representative: com.example.tests.LoginTests.loginButtonClickable - element click intercepted: Element is not clickable at point (120, 340)). Likely environment/timing-related rather than a real product defect - consider adding explicit waits or a retry policy before assuming a regression.

## [INFRA] com.example.tests.ApiHealthTests.pingInternalService (+0 more)

- **Confidence:** high
- **Affected tests (1):** `com.example.tests.ApiHealthTests.pingInternalService`

1 test failed with a matching infra signature (representative: com.example.tests.ApiHealthTests.pingInternalService - Connection refused: connect). Likely an environment/connectivity problem outside the application under test - check that dependent services and network access were available during this run.
