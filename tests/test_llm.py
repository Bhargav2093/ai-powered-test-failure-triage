from unittest.mock import MagicMock

from triage.llm import narrate_cluster
from triage.models import Category, Classification, ClassifiedFailure, Cluster, Confidence, FailureRecord


def _cluster() -> Cluster:
    record = FailureRecord(
        test_name="pingInternalService",
        class_name="com.example.ApiHealthTests",
        message="Connection refused: connect",
        stack_trace="java.net.ConnectException: Connection refused: connect",
        source_format="junit",
        source_file="dummy.xml",
    )
    classification = Classification(category=Category.INFRA, confidence=Confidence.HIGH)
    member = ClassifiedFailure(record=record, classification=classification)
    return Cluster(id=0, members=[member], signature="ConnectException Connection refused")


class TestNarrateCluster:
    def test_no_api_key_falls_back_to_template(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("LLM_PROVIDER", raising=False)

        result = narrate_cluster(_cluster())

        assert "infra" in result
        assert "pingInternalService" in result

    def test_template_mentions_cluster_size(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        cluster = _cluster()
        cluster.members.append(cluster.members[0])

        result = narrate_cluster(cluster)

        assert "2 tests" in result

    def test_injected_client_is_used_when_provided(self):
        fake_block = MagicMock(type="text", text="Root cause: the internal health-check service was down.")
        fake_response = MagicMock(content=[fake_block])
        fake_client = MagicMock()
        fake_client.messages.create.return_value = fake_response

        result = narrate_cluster(_cluster(), client=fake_client)

        assert result == "Root cause: the internal health-check service was down."
        fake_client.messages.create.assert_called_once()

    def test_injected_client_uses_default_model(self):
        fake_block = MagicMock(type="text", text="narrative")
        fake_client = MagicMock()
        fake_client.messages.create.return_value = MagicMock(content=[fake_block])

        narrate_cluster(_cluster(), client=fake_client)

        _, kwargs = fake_client.messages.create.call_args
        assert kwargs["model"] == "claude-opus-5"

    def test_model_override_via_env_var(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_MODEL", "claude-sonnet-5")
        fake_block = MagicMock(type="text", text="narrative")
        fake_client = MagicMock()
        fake_client.messages.create.return_value = MagicMock(content=[fake_block])

        narrate_cluster(_cluster(), client=fake_client)

        _, kwargs = fake_client.messages.create.call_args
        assert kwargs["model"] == "claude-sonnet-5"

    def test_api_error_degrades_to_template_instead_of_raising(self):
        fake_client = MagicMock()
        fake_client.messages.create.side_effect = RuntimeError("network down")

        result = narrate_cluster(_cluster(), client=fake_client)

        assert "infra" in result


class TestNarrateClusterOpenAI:
    def test_injected_openai_client_is_used_when_provided(self):
        fake_message = MagicMock(content="Root cause: the internal health-check service was down.")
        fake_choice = MagicMock(message=fake_message)
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = MagicMock(choices=[fake_choice])

        result = narrate_cluster(_cluster(), openai_client=fake_client)

        assert result == "Root cause: the internal health-check service was down."
        fake_client.chat.completions.create.assert_called_once()

    def test_injected_openai_client_uses_default_model(self):
        fake_choice = MagicMock(message=MagicMock(content="narrative"))
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = MagicMock(choices=[fake_choice])

        narrate_cluster(_cluster(), openai_client=fake_client)

        _, kwargs = fake_client.chat.completions.create.call_args
        assert kwargs["model"] == "gpt-4o-mini"

    def test_openai_model_override_via_env_var(self, monkeypatch):
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4.1")
        fake_choice = MagicMock(message=MagicMock(content="narrative"))
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = MagicMock(choices=[fake_choice])

        narrate_cluster(_cluster(), openai_client=fake_client)

        _, kwargs = fake_client.chat.completions.create.call_args
        assert kwargs["model"] == "gpt-4.1"

    def test_openai_api_error_degrades_to_template_instead_of_raising(self):
        fake_client = MagicMock()
        fake_client.chat.completions.create.side_effect = RuntimeError("network down")

        result = narrate_cluster(_cluster(), openai_client=fake_client)

        assert "infra" in result

    def test_empty_choices_falls_back_to_template(self):
        fake_client = MagicMock()
        fake_client.chat.completions.create.return_value = MagicMock(choices=[])

        result = narrate_cluster(_cluster(), openai_client=fake_client)

        assert "infra" in result


class TestProviderSelection:
    def test_openai_key_alone_selects_openai_provider(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
        monkeypatch.setattr("triage.llm._narrate_openai", lambda cluster: "openai-path")

        result = narrate_cluster(_cluster())

        assert result == "openai-path"

    def test_both_keys_set_prefers_anthropic_by_default(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
        monkeypatch.delenv("LLM_PROVIDER", raising=False)
        monkeypatch.setattr("triage.llm._narrate_anthropic", lambda cluster: "anthropic-path")

        result = narrate_cluster(_cluster())

        assert result == "anthropic-path"

    def test_forced_provider_env_var_overrides_key_precedence(self, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-fake")
        monkeypatch.setenv("LLM_PROVIDER", "openai")
        monkeypatch.setattr("triage.llm._narrate_openai", lambda cluster: "openai-path")

        result = narrate_cluster(_cluster())

        assert result == "openai-path"
