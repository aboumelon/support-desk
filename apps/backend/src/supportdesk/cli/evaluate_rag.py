"""Reproducible retrieval and fixture-provider evidence, without paid API calls."""

import hashlib
import json
import statistics
import time

from sqlalchemy import select
from sqlalchemy.orm import Session

from supportdesk.config import get_settings, project_root
from supportdesk.infrastructure.worker_database import worker_engine
from supportdesk.modules.assistant.embeddings.e5 import encode
from supportdesk.modules.assistant.prompts import build_messages
from supportdesk.modules.assistant.providers.fake import FakeProvider
from supportdesk.modules.knowledge.retrieval import retrieve
from supportdesk.modules.workspaces.models import Workspace


def main() -> None:
    root = project_root()
    source = root / "evals/rag/cases.jsonl"
    cases = [json.loads(line) for line in source.read_text().splitlines()]
    vectors = encode([case["question"] for case in cases], "query")
    results = []
    with Session(worker_engine()) as db:
        workspaces = {w.public_key: w.id for w in db.scalars(select(Workspace)).all()}
    for case, vector in zip(cases, vectors, strict=True):
        start = time.perf_counter()
        with Session(worker_engine()) as db:
            passages = retrieve(db, workspaces[case["workspace"]], vector, limit=5)
        handoff = not passages or passages[0].score < 0.65
        row = {
            **case,
            "retrieved": [p.title for p in passages],
            "scores": [p.score for p in passages],
            "predicted_handoff": handoff,
            "handoff_correct": handoff == case["handoff"],
            "retrieval_ms": (time.perf_counter() - start) * 1000,
            "isolation_pass": all(
                p.chunk.workspace_id == workspaces[case["workspace"]] for p in passages
            ),
        }
        if case.get("expected_source"):
            row["recall_at_5"] = any(
                p.title == f"Fictional fixture: {case['expected_source']}"
                for p in passages
            )
        if not handoff:
            start = time.perf_counter()
            first = None
            answer = ""
            for delta in FakeProvider().stream(
                build_messages(
                    [{"label": "S1", "text": passages[0].chunk.text}],
                    [("user", case["question"])],
                    get_settings().input_allowance(),
                ),
                8192,
            ):
                if delta.text and first is None:
                    first = (time.perf_counter() - start) * 1000
                answer += delta.text
            if "NO_ANSWER" in answer:
                row["predicted_handoff"] = True
                row["handoff_correct"] = case["handoff"]
            row.update(
                first_token_ms=first,
                full_answer_ms=(time.perf_counter() - start) * 1000,
                source_id_valid="NO_ANSWER" in answer
                or ("[S1]" in answer and "[S99]" not in answer),
                answer=answer,
            )
        results.append(row)
    answerable = [r for r in results if r["category"] == "answerable"]
    latencies = [r["full_answer_ms"] for r in results if "full_answer_ms" in r]
    report = {
        "mode": "deterministic fixture excerpt provider",
        "embedding_revision": get_settings().embedding_revision,
        "cases_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "case_count": len(results),
        "recall_at_5": sum(r["recall_at_5"] for r in answerable) / len(answerable),
        "correct_handoff_rate": sum(r["handoff_correct"] for r in results)
        / len(results),
        "source_isolation_failures": sum(not r["isolation_pass"] for r in results),
        "source_id_validity": all(r.get("source_id_valid", True) for r in results),
        "full_answer_p50_ms": statistics.median(latencies) if latencies else None,
        "human_claim_support_ratings": "not collected; requires independent review",
        "live_provider": "unverified; no credentials or paid API calls used",
        "results": results,
    }
    path = root / "docs/evidence/rag-portfolio.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))


if __name__ == "__main__":
    main()
