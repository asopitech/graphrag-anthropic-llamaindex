"""Standard-library HTTP acceptance runner for the isolated fixture server."""

import argparse
import json
import math
import sys

from .demo_fixture import DOCUMENTS, MARKER
from .server_client import GraphRAGClient


def validate_results(response, mode):
    """Reject empty results and error nodes, including HTTP-200 failures."""
    results = response.get("results")
    if not isinstance(results, list) or not results:
        raise ValueError(f"{mode}: empty results")
    for result in results:
        metadata = result.get("metadata", {})
        if metadata.get("error") or metadata.get("status") in {"error", "no_entities_found"}:
            raise ValueError(f"{mode}: error/no-entity node: {metadata}")
        score = result.get("score")
        if not isinstance(score, (float, int)) or not math.isfinite(score) or score <= 0:
            raise ValueError(f"{mode}: invalid score")
        if MARKER not in result.get("text", "") or "AlopexDB" not in result["text"]:
            raise ValueError(f"{mode}: fixture evidence missing")
    metadata = results[0]["metadata"]
    expected = "global" if mode == "auto" else mode
    if metadata.get("search_type") != expected:
        raise ValueError(f"{mode}: unexpected search_type")
    if expected == "local" and metadata.get("num_entities", 0) < 2:
        raise ValueError("local: fewer than two entities")
    if expected == "global" and not metadata.get("traceability", {}).get("report_ids"):
        raise ValueError("global: community report provenance missing")


def run_demo(client, verify_only=False):
    """Register two documents and validate local/global/auto retrieval."""
    health = client.health()
    if health.get("runtime") != "demo-fixture-v1" or health.get("alopexdb") != "ok":
        raise ValueError("Refusing to index: use the isolated demo-fixture-v1 server")
    registrations = []
    if not verify_only:
        for filename, content in DOCUMENTS.items():
            result = client.add_document(filename, content)
            if result != {"status": "indexed", "filename": filename}:
                raise ValueError(f"Registration failed: {result}")
            registrations.append(result)
    searches = {}
    for mode, query in [("local", "AlopexDB specific details"),
                        ("global", "AlopexDB GraphRAG overview"),
                        ("auto", "AlopexDB GraphRAG overview")]:
        response = client.search(query, mode)
        validate_results(response, mode)
        searches[mode] = response
    return {"runtime": "demo-fixture-v1", "verification_only": verify_only,
            "documents": registrations, "searches": searches}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    try:
        report = run_demo(GraphRAGClient(args.url), args.verify_only)
    except Exception as error:
        print(f"DEMO FAILED: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
