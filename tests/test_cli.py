import json
from pathlib import Path

import pytest

from triage.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


class TestCli:
    def test_no_input_paths_is_a_usage_error(self, capsys):
        # argparse.error() prints usage and calls sys.exit(2)
        with pytest.raises(SystemExit) as exc_info:
            main([])

        assert exc_info.value.code != 0

    def test_junit_input_writes_html_report_by_default(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        exit_code = main(
            ["--junit-xml", str(FIXTURES / "synthetic" / "mixed_failures.xml")]
        )

        assert exit_code == 0
        assert (tmp_path / "triage-report.html").exists()
        assert "<!DOCTYPE html>" in (tmp_path / "triage-report.html").read_text(encoding="utf-8")

    def test_json_output_reflects_all_categories(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        output_path = tmp_path / "report.json"

        exit_code = main(
            [
                "--junit-xml", str(FIXTURES / "synthetic" / "mixed_failures.xml"),
                "--format", "json",
                "--output", str(output_path),
            ]
        )

        assert exit_code == 0
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data["total_failures"] == 4
        assert data["counts"]["flaky"] == 2
        assert data["counts"]["infra"] == 1
        assert data["counts"]["regression"] == 1

    def test_allure_dir_input_works(self, tmp_path, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        output_path = tmp_path / "report.json"

        exit_code = main(
            [
                "--allure-dir", str(FIXTURES / "real_framework_failure"),
                "--format", "json",
                "--output", str(output_path),
            ]
        )

        assert exit_code == 0
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data["total_failures"] == 1

    def test_no_matching_failures_still_exits_cleanly(self, tmp_path, capsys):
        empty_xml = tmp_path / "empty.xml"
        empty_xml.write_text(
            '<?xml version="1.0"?><testsuite tests="0"></testsuite>', encoding="utf-8"
        )

        exit_code = main(["--junit-xml", str(empty_xml)])

        assert exit_code == 0
        assert "No failures found" in capsys.readouterr().out
