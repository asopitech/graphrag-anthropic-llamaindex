"""Offline contract tests. The HTTP peer here is a fake, not AlopexDB."""

import json
import math
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import Mock

from graphrag_anthropic_llamaindex.demo_fixture import DOCUMENTS, MARKER, complete_fixture, embed
from graphrag_anthropic_llamaindex.server_client import GraphRAGClient
from graphrag_anthropic_llamaindex.server_demo import run_demo, validate_results


def response_for(mode):
    selected = "global" if mode == "auto" else mode
    return {"results": [{"text": MARKER + " AlopexDB", "score": 1.0,
                         "metadata": {"search_type": selected, "num_entities": 3,
                                      "traceability": {"report_ids": ["report-1"]}}}]}


class DemoContractTests(unittest.TestCase):
    def test_embeddings_stable_normalized_and_distinct(self):
        a = embed("AlopexDB LlamaIndex")
        self.assertEqual(a, embed("AlopexDB LlamaIndex"))
        self.assertNotEqual(a, embed("SearchDemo"))
        self.assertEqual(len(a), 64)
        self.assertAlmostEqual(sum(x*x for x in a), 1)
        self.assertTrue(all(math.isfinite(x) for x in embed("")))

    def test_extraction_uses_document_not_prompt_example(self):
        for text in DOCUMENTS.values():
            result = json.loads(complete_fixture("Extract entities and relationships\nAlice Microsoft\nText: " + text))
            self.assertEqual(len(result["relationships"]), 3)
            names = {entity["name"] for entity in result["entities"]}
            self.assertIn("AlopexDB", names)
            self.assertNotIn("Alice", names)
        with self.assertRaises(ValueError):
            complete_fixture("unexpected prompt")

    def test_map_and_reduce_preserve_retrieved_evidence(self):
        context = "id|title|content|rank|weight\nabc|Report|[DEMO FIXTURE] AlopexDB|0|1.0"
        result = json.loads(complete_fixture("Context Data:\n" + context + "\nUser Question:\nsummary"))
        self.assertEqual(result["points"][0]["report_ids"], ["abc"])
        reduced = complete_fixture("Analyst Reports:\n80|[DEMO FIXTURE] AlopexDB|abc\nUser Question:\nsummary")
        self.assertIn("abc", reduced)
        with self.assertRaises(ValueError):
            complete_fixture("Analyst Reports:\nempty\nUser Question:\nsummary")

    def test_refuses_normal_server_before_upload(self):
        client = Mock()
        client.health.return_value = {"status": "ok", "alopexdb": "ok"}
        with self.assertRaises(ValueError):
            run_demo(client)
        client.add_document.assert_not_called()
        client.search.assert_not_called()

    def test_rejects_empty_error_missing_evidence_and_provenance(self):
        invalid = [{"results": []}]
        for changes in [{"score": 0}, {"score": float("nan")}, {"text": "no information"},
                        {"metadata": {"status": "error"}},
                        {"metadata": {"search_type": "global", "traceability": {}}}]:
            response = response_for("global")
            response["results"][0].update(changes)
            invalid.append(response)
        for response in invalid:
            with self.subTest(response=response), self.assertRaises(ValueError):
                validate_results(response, "global")

    def test_registration_failure_stops_search(self):
        client = Mock()
        client.health.return_value = {"alopexdb": "ok", "runtime": "demo-fixture-v1"}
        client.add_document.return_value = {"status": "failed"}
        with self.assertRaises(ValueError):
            run_demo(client)
        client.search.assert_not_called()

    def test_http_protocol_registration_and_verify_only(self):
        requests = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                self.respond({"alopexdb": "ok", "runtime": "demo-fixture-v1"})

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                requests.append((self.path, body))
                if self.path == "/v1/documents":
                    self.respond({"status": "indexed", "filename": body["filename"]})
                elif self.path == "/v1/search":
                    self.respond(response_for(body["mode"]))
                else:
                    self.send_error(404)

            def respond(self, body):
                data = json.dumps(body).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = GraphRAGClient(f"http://127.0.0.1:{server.server_port}")
            report = run_demo(client)
            self.assertEqual(set(report["searches"]), {"local", "global", "auto"})
            self.assertEqual([body for path, body in requests if path == "/v1/documents"],
                             [{"filename": name, "content": content} for name, content in DOCUMENTS.items()])
            requests.clear()
            run_demo(client, verify_only=True)
            self.assertEqual(len(requests), 3)
            self.assertTrue(all(path == "/v1/search" for path, _ in requests))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
