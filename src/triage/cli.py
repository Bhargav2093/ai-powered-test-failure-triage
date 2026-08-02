"""`triage` command-line entrypoint - plug JUnit XML and/or Allure result
directories in, get a classified/clustered/narrated report out."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from triage.classify import classify
from triage.cluster import cluster_failures
from triage.llm import narrate_cluster
from triage.models import ClassifiedFailure, TriageResult
from triage.parsers.allure_json import parse_allure_results
from triage.parsers.junit_xml import parse_junit_xml
from triage.report import render_html, render_json, render_markdown

_RENDERERS = {"html": render_html, "json": render_json, "markdown": render_markdown}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="triage",
        description="Classify, cluster, and narrate automated test failures from "
        "JUnit XML and/or Allure result output.",
    )
    parser.add_argument(
        "--junit-xml", nargs="*", default=[], metavar="FILE",
        help="One or more JUnit-style testsuite/testcase XML files "
        "(Surefire, TestNG, pytest --junitxml all emit this).",
    )
    parser.add_argument(
        "--allure-dir", nargs="*", default=[], metavar="DIR",
        help="One or more directories containing Allure *-result.json files.",
    )
    parser.add_argument(
        "--format", choices=sorted(_RENDERERS), default="html", help="Report format (default: html).",
    )
    parser.add_argument(
        "--output", "-o", type=Path, default=None,
        help="Output file path. Defaults to triage-report.html for --format html, "
        "or stdout for json/markdown.",
    )
    parser.add_argument(
        "--similarity-threshold", type=float, default=0.6,
        help="Cosine-similarity threshold for clustering same-category failures (default: 0.6).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.junit_xml and not args.allure_dir:
        parser.error("provide at least one --junit-xml file or --allure-dir directory")

    records = []
    for path in args.junit_xml:
        records.extend(parse_junit_xml(path))
    for path in args.allure_dir:
        records.extend(parse_allure_results(path))

    if not records:
        print("No failures found in the given input - nothing to triage.")
        return 0

    classified = [ClassifiedFailure(record=r, classification=classify(r)) for r in records]
    clusters = cluster_failures(classified, similarity_threshold=args.similarity_threshold)
    result = TriageResult(clusters=clusters)

    narratives = {cluster.id: narrate_cluster(cluster) for cluster in clusters}

    content = _RENDERERS[args.format](result, narratives)

    output_path = args.output
    if output_path is None and args.format == "html":
        output_path = Path("triage-report.html")

    if output_path:
        output_path.write_text(content, encoding="utf-8")
        print(
            f"Triaged {result.total_failures} failure(s) into {len(clusters)} cluster(s). "
            f"Wrote {args.format} report to {output_path}"
        )
    else:
        print(content)

    return 0


if __name__ == "__main__":
    sys.exit(main())
