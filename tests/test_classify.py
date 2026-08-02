from triage.classify import classify
from triage.models import Category, Confidence, FailureRecord


def _record(message: str, stack_trace: str) -> FailureRecord:
    return FailureRecord(
        test_name="someTest",
        class_name="com.example.SomeTests",
        message=message,
        stack_trace=stack_trace,
        source_format="junit",
        source_file="dummy.xml",
    )


class TestClassify:
    def test_stale_element_is_flaky(self):
        record = _record(
            "stale element reference: element is not attached to the page document",
            "org.openqa.selenium.StaleElementReferenceException: stale element reference",
        )

        result = classify(record)

        assert result.category == Category.FLAKY
        assert "StaleElementReferenceException" in result.matched_signals

    def test_click_intercepted_is_flaky(self):
        record = _record(
            "element click intercepted",
            "org.openqa.selenium.ElementClickInterceptedException: element click intercepted",
        )

        assert classify(record).category == Category.FLAKY

    def test_connection_refused_is_infra(self):
        record = _record(
            "Connection refused: connect",
            "java.net.ConnectException: Connection refused: connect",
        )

        result = classify(record)

        assert result.category == Category.INFRA
        assert result.confidence == Confidence.HIGH  # both "ConnectException" and "connection refused" match

    def test_unknown_host_is_infra(self):
        record = _record(
            "api.internal.example.com",
            "java.net.UnknownHostException: api.internal.example.com",
        )

        assert classify(record).category == Category.INFRA

    def test_plain_assertion_error_defaults_to_regression(self):
        record = _record(
            "expected [42.50] but found [39.99]",
            "java.lang.AssertionError: expected [42.50] but found [39.99]",
        )

        result = classify(record)

        assert result.category == Category.REGRESSION
        assert result.matched_signals == ()

    def test_regression_never_matches_flaky_or_infra_signals(self):
        record = _record("some totally different failure", "java.lang.NullPointerException")

        result = classify(record)

        assert result.category == Category.REGRESSION

    def test_matching_is_case_insensitive(self):
        record = _record("timeout waiting for element", "org.openqa.selenium.timeoutexception")

        assert classify(record).category == Category.FLAKY
