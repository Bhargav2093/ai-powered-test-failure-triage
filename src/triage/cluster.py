"""Groups classified failures that likely share the same root cause.

Each failure is reduced to a normalized "signature" (exception type + top
stack frame + message with volatile bits like numbers/paths/ids stripped),
then signatures are vectorized with TF-IDF and grouped by cosine-similarity
so one root cause spanning many tests surfaces as one triage item instead of
dozens of near-duplicate ones.
"""

from __future__ import annotations

import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from triage.models import ClassifiedFailure, Cluster

_NUMBER_RE = re.compile(r"\d+")
_PATH_RE = re.compile(r"(?:[A-Za-z]:)?[/\\][\w./\\-]+")
_EXCEPTION_TYPE_RE = re.compile(r"([A-Za-z_][\w.]*(?:Exception|Error))")
_STACK_FRAME_RE = re.compile(r"^\s*at\s+(\S+)", re.MULTILINE)

_DEFAULT_SIMILARITY_THRESHOLD = 0.6


def build_signature(failure: ClassifiedFailure) -> str:
    """Normalize a failure into text that captures *what kind* of failure it
    is while stripping the volatile specifics (numbers, ids, file paths) that
    would otherwise make two instances of the same root cause look distinct.
    """
    record = failure.record

    exception_match = _EXCEPTION_TYPE_RE.search(record.stack_trace) or _EXCEPTION_TYPE_RE.search(
        record.message
    )
    exception_type = exception_match.group(1) if exception_match else "UnknownError"

    top_frame_match = _STACK_FRAME_RE.search(record.stack_trace)
    top_frame = top_frame_match.group(1) if top_frame_match else ""

    normalized_message = _PATH_RE.sub("<path>", record.message)
    normalized_message = _NUMBER_RE.sub("<n>", normalized_message)

    return f"{exception_type} {top_frame} {normalized_message}"


def cluster_failures(
    failures: list[ClassifiedFailure],
    similarity_threshold: float = _DEFAULT_SIMILARITY_THRESHOLD,
) -> list[Cluster]:
    """Group failures into clusters of shared root cause.

    Two failures are put in the same cluster when they have the same
    classification category AND their normalized signatures are similar
    enough (cosine similarity on TF-IDF vectors >= similarity_threshold).
    Clustering never crosses category boundaries - a flaky failure and a
    regression should never be merged even if their text happens to overlap.
    """
    if not failures:
        return []

    signatures = [build_signature(f) for f in failures]

    if len(failures) == 1:
        similarity = np.ones((1, 1))
    else:
        vectorizer = TfidfVectorizer()
        try:
            matrix = vectorizer.fit_transform(signatures)
            similarity = cosine_similarity(matrix)
        except ValueError:
            # All signatures were empty/stopword-only - treat as dissimilar.
            similarity = np.eye(len(failures))

    assigned = [-1] * len(failures)
    clusters: list[Cluster] = []

    for i, failure in enumerate(failures):
        if assigned[i] != -1:
            continue

        cluster_id = len(clusters)
        members = [failure]
        assigned[i] = cluster_id

        for j in range(i + 1, len(failures)):
            if assigned[j] != -1:
                continue
            same_category = failures[j].classification.category == failure.classification.category
            similar_enough = similarity[i, j] >= similarity_threshold
            if same_category and similar_enough:
                members.append(failures[j])
                assigned[j] = cluster_id

        clusters.append(Cluster(id=cluster_id, members=members, signature=signatures[i]))

    return clusters
