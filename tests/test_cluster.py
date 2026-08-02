from triage.cluster import cluster_failures
from triage.models import Category, ClassifiedFailure, Classification, Confidence, FailureRecord


def _classified(test_name: str, message: str, stack_trace: str, category: Category) -> ClassifiedFailure:
    record = FailureRecord(
        test_name=test_name,
        class_name="com.example.Tests",
        message=message,
        stack_trace=stack_trace,
        source_format="junit",
        source_file="dummy.xml",
    )
    classification = Classification(category=category, confidence=Confidence.MEDIUM)
    return ClassifiedFailure(record=record, classification=classification)


class TestClusterFailures:
    def test_empty_input_returns_no_clusters(self):
        assert cluster_failures([]) == []

    def test_single_failure_forms_its_own_cluster(self):
        failure = _classified(
            "test1", "Connection refused: connect",
            "java.net.ConnectException: Connection refused: connect\n\tat com.example.Client.ping(Client.java:10)",
            Category.INFRA,
        )

        clusters = cluster_failures([failure])

        assert len(clusters) == 1
        assert clusters[0].size == 1
        assert clusters[0].category == Category.INFRA

    def test_similar_same_category_failures_are_merged(self):
        trace = "java.net.ConnectException: Connection refused: connect\n\tat com.example.Client.ping(Client.java:{})"
        a = _classified("test1", "Connection refused: connect", trace.format(10), Category.INFRA)
        b = _classified("test2", "Connection refused: connect", trace.format(99), Category.INFRA)

        clusters = cluster_failures([a, b])

        assert len(clusters) == 1
        assert clusters[0].size == 2

    def test_different_categories_never_merge_even_if_text_is_similar(self):
        a = _classified(
            "test1", "boom", "java.lang.RuntimeException: boom\n\tat com.example.A.run(A.java:1)", Category.INFRA
        )
        b = _classified(
            "test2", "boom", "java.lang.RuntimeException: boom\n\tat com.example.A.run(A.java:1)",
            Category.REGRESSION,
        )

        clusters = cluster_failures([a, b])

        assert len(clusters) == 2
        categories = {c.category for c in clusters}
        assert categories == {Category.INFRA, Category.REGRESSION}

    def test_dissimilar_same_category_failures_stay_separate(self):
        a = _classified(
            "test1", "Connection refused: connect",
            "java.net.ConnectException: Connection refused: connect\n\tat com.example.Client.ping(Client.java:10)",
            Category.INFRA,
        )
        b = _classified(
            "test2", "unrelated failure about parsing a totally different subsystem entirely",
            "java.lang.IllegalStateException: unrelated failure about parsing a totally different subsystem entirely"
            "\n\tat com.example.OtherThing.parse(OtherThing.java:200)",
            Category.INFRA,
        )

        clusters = cluster_failures([a, b], similarity_threshold=0.6)

        assert len(clusters) == 2

    def test_every_input_failure_is_assigned_to_exactly_one_cluster(self):
        failures = [
            _classified(f"test{i}", "Connection refused: connect",
                        f"java.net.ConnectException: Connection refused: connect\n\tat com.example.C.ping(C.java:{i})",
                        Category.INFRA)
            for i in range(5)
        ]

        clusters = cluster_failures(failures)

        total_members = sum(c.size for c in clusters)
        assert total_members == len(failures)
