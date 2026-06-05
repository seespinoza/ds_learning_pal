"""
Eval runner for DS Learning Pal.

Usage:
    python src/evals/run_evals.py [--base-url http://localhost:8000] [--token <jwt>]

Calls the running backend endpoints, scores against gold manifests, prints a results table.
Requires the backend to be running with ANTHROPIC_API_KEY set.
"""
import argparse
import json
import os
import sys

import httpx

BASE_DIR = os.path.dirname(__file__)
FIXTURES_DIR = os.path.join(BASE_DIR, "fixtures")


def _headers(token: str | None) -> dict:
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


# ---------------------------------------------------------------------------
# Ingest evals
# ---------------------------------------------------------------------------

def _score_ingest(proposed: dict, gold: dict) -> dict:
    """Compute node/relationship recall and precision against a gold set."""

    def node_key(n: dict) -> tuple:
        return (n.get("label", "").lower(), n.get("name", "").lower())

    def rel_key(r: dict) -> tuple:
        return (r.get("from", "").lower(), r.get("to", "").lower(), r.get("type", "").lower())

    gold_nodes = {node_key(n) for n in gold.get("nodes", [])}
    gold_rels = {rel_key(r) for r in gold.get("relationships", [])}
    prop_nodes = {node_key(n) for n in proposed.get("nodes", [])}
    prop_rels = {rel_key(r) for r in proposed.get("relationships", [])}

    correct_nodes = gold_nodes & prop_nodes
    correct_rels = gold_rels & prop_rels

    node_recall = len(correct_nodes) / len(gold_nodes) if gold_nodes else 1.0
    node_precision = len(correct_nodes) / len(prop_nodes) if prop_nodes else 0.0
    rel_recall = len(correct_rels) / len(gold_rels) if gold_rels else 1.0
    rel_precision = len(correct_rels) / len(prop_rels) if prop_rels else 0.0

    return {
        "node_recall": node_recall,
        "node_precision": node_precision,
        "rel_recall": rel_recall,
        "rel_precision": rel_precision,
        "correct_nodes": len(correct_nodes),
        "gold_nodes": len(gold_nodes),
        "proposed_nodes": len(prop_nodes),
        "correct_rels": len(correct_rels),
        "gold_rels": len(gold_rels),
        "proposed_rels": len(prop_rels),
    }


def run_ingest_evals(base_url: str, token: str | None) -> list[dict]:
    ingest_dir = os.path.join(FIXTURES_DIR, "ingest")
    results = []

    for fixture_name in sorted(os.listdir(ingest_dir)):
        fixture_path = os.path.join(ingest_dir, fixture_name)
        if not os.path.isdir(fixture_path):
            continue

        # Find input file
        input_file = None
        for candidate in ("input.txt", "input.pdf", "input.url"):
            if os.path.exists(os.path.join(fixture_path, candidate)):
                input_file = candidate
                break
        if not input_file:
            print(f"  [skip] {fixture_name}: no input file found")
            continue

        gold_path = os.path.join(fixture_path, "gold.json")
        if not os.path.exists(gold_path):
            print(f"  [skip] {fixture_name}: no gold.json")
            continue

        with open(gold_path) as f:
            gold = json.load(f)

        full_input_path = os.path.join(fixture_path, input_file)

        if input_file.endswith(".url"):
            with open(full_input_path) as f:
                url = f.read().strip()
            payload = {"input_type": "url", "input_value": url}
        elif input_file.endswith(".txt"):
            with open(full_input_path) as f:
                text = f.read()
            payload = {"input_type": "text", "input_value": text}
        else:
            payload = {"input_type": "pdf", "input_value": full_input_path}

        try:
            resp = httpx.post(
                f"{base_url}/ingest",
                json=payload,
                headers=_headers(token),
                timeout=120,
            )
            resp.raise_for_status()
            proposed = resp.json()
        except Exception as e:
            results.append({"fixture": fixture_name, "agent": "ingest", "error": str(e)})
            continue

        scores = _score_ingest(proposed, gold)
        results.append({"fixture": fixture_name, "agent": "ingest", **scores})

    return results


# ---------------------------------------------------------------------------
# Lint evals
# ---------------------------------------------------------------------------

def _score_lint(report: dict, manifest: dict) -> dict:
    """Compute issue recall and precision against a manifest."""
    expected = manifest.get("issues", [])

    def issue_key(issue: dict) -> tuple:
        nodes = tuple(sorted(n.lower() for n in issue.get("nodes", [issue.get("node", "")])))
        return (issue.get("type", "").lower(), nodes)

    gold_keys = {issue_key(i) for i in expected}

    found_issues = []
    for finding in report.get("per_node_findings", []):
        for issue in finding.get("issues", []):
            found_issues.append({
                "type": issue.get("type", ""),
                "nodes": [finding.get("node", "")],
            })
    for issue in report.get("cross_node_issues", []):
        found_issues.append(issue)

    prop_keys = {issue_key(i) for i in found_issues}
    correct = gold_keys & prop_keys

    recall = len(correct) / len(gold_keys) if gold_keys else 1.0
    precision = len(correct) / len(prop_keys) if prop_keys else 0.0

    return {
        "issue_recall": recall,
        "issue_precision": precision,
        "correct_issues": len(correct),
        "gold_issues": len(gold_keys),
        "proposed_issues": len(prop_keys),
    }


def run_lint_evals(base_url: str, token: str | None) -> list[dict]:
    lint_dir = os.path.join(FIXTURES_DIR, "lint")
    results = []

    for fixture_name in sorted(os.listdir(lint_dir)):
        fixture_path = os.path.join(lint_dir, fixture_name)
        if not os.path.isdir(fixture_path):
            continue

        graph_path = os.path.join(fixture_path, "graph.json")
        manifest_path = os.path.join(fixture_path, "manifest.json")
        if not os.path.exists(graph_path) or not os.path.exists(manifest_path):
            print(f"  [skip] {fixture_name}: missing graph.json or manifest.json")
            continue

        with open(graph_path) as f:
            graph = json.load(f)
        with open(manifest_path) as f:
            manifest = json.load(f)

        # For lint evals, we call a special fixture endpoint that loads the graph snapshot
        # and runs lint against it in-memory (bypassing Neo4j).
        # If no such endpoint is available, fall back to the main /lint endpoint.
        try:
            resp = httpx.post(
                f"{base_url}/lint/fixture",
                json={"graph": graph},
                headers=_headers(token),
                timeout=120,
            )
            if resp.status_code == 404:
                # Fallback: run against live graph (less deterministic)
                resp = httpx.post(
                    f"{base_url}/lint",
                    headers=_headers(token),
                    timeout=120,
                )
            resp.raise_for_status()
            report = resp.json()
        except Exception as e:
            results.append({"fixture": fixture_name, "agent": "lint", "error": str(e)})
            continue

        scores = _score_lint(report, manifest)
        results.append({"fixture": fixture_name, "agent": "lint", **scores})

    return results


# ---------------------------------------------------------------------------
# Table printer
# ---------------------------------------------------------------------------

def _print_table(results: list[dict]):
    print("\n" + "=" * 80)
    print(f"{'Fixture':<30} {'Agent':<8} {'Metric':<25} {'Score':>8}")
    print("=" * 80)

    passed = 0
    failed = 0
    THRESHOLD = 0.5

    for r in results:
        fixture = r["fixture"]
        agent = r["agent"]
        if "error" in r:
            print(f"  {'ERROR':<30} {fixture:<30} {agent:<8} {r['error']}")
            failed += 1
            continue

        if agent == "ingest":
            metrics = [
                ("node_recall", r.get("node_recall", 0)),
                ("node_precision", r.get("node_precision", 0)),
                ("rel_recall", r.get("rel_recall", 0)),
                ("rel_precision", r.get("rel_precision", 0)),
            ]
        else:
            metrics = [
                ("issue_recall", r.get("issue_recall", 0)),
                ("issue_precision", r.get("issue_precision", 0)),
            ]

        for metric_name, score in metrics:
            status = "PASS" if score >= THRESHOLD else "FAIL"
            if score >= THRESHOLD:
                passed += 1
            else:
                failed += 1
            print(f"  {fixture:<30} {agent:<8} {metric_name:<25} {score:>7.1%}  {status}")

    print("=" * 80)
    print(f"  Results: {passed} passed, {failed} failed  (threshold: {THRESHOLD:.0%})")
    print("=" * 80 + "\n")

    return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Run DS Learning Pal evals")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--token", default=None, help="JWT Bearer token for auth")
    args = parser.parse_args()

    print(f"\nRunning evals against {args.base_url}")
    print("Running ingest evals...")
    ingest_results = run_ingest_evals(args.base_url, args.token)

    print("Running lint evals...")
    lint_results = run_lint_evals(args.base_url, args.token)

    all_results = ingest_results + lint_results
    success = _print_table(all_results)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
