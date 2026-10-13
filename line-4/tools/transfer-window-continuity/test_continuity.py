#!/usr/bin/env python3
"""Real retained ZTO evidence plus explicitly synthetic rejection mutations."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import socket
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("continuity_under_test", HERE / "continuity.py")
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


def changed_hash(value):
    return value[:-1] + ("1" if value[-1] == "0" else "0")


class ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.capture = c.reader.read_capture(HERE.parent / "transfer-crosscheck" / "publicnode.json")
        self.evidence = c.reader.read_capture(HERE / "observations.json")

    def run_report(self):
        return c.report(self.capture, self.evidence)

    def test_real_demo_without_network(self):
        with patch.object(socket, "socket", side_effect=AssertionError("offline demo attempted network")):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(c.main(["--demo"]), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result["status"], "consistent")
        self.assertEqual(result["block_count"], 12)
        self.assertEqual(result["matching_parent_link_count"], 11)
        self.assertEqual(result["matching_saved_anchor_count"], 2)
        self.assertEqual(result["newly_observed_interior_block_count"], 10)
        self.assertEqual(result["transfer_count"], 3)
        self.assertEqual(sum(row["transfer_count"] for row in result["blocks"]), 3)

    def test_report_does_not_mutate_inputs(self):
        before = copy.deepcopy((self.capture, self.evidence))
        self.run_report()
        self.assertEqual((self.capture, self.evidence), before)

    def test_broken_parent_is_localized(self):
        block = self.evidence["observations"][5]["block"]
        block["parentHash"] = changed_hash(block["parentHash"])
        result = self.run_report()
        self.assertEqual(result["status"], "conflicting")
        self.assertEqual(result["conflicting_parent_link_count"], 1)
        self.assertEqual(result["matching_saved_anchor_count"], 2)
        self.assertEqual(result["links"][4]["child_number"], self.capture["from_block"] + 5)

    def test_missing_interior_breaks_two_links(self):
        self.evidence["observations"][5]["block"] = None
        result = self.run_report()
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["unavailable_block_count"], 1)
        self.assertEqual(result["unavailable_parent_link_count"], 2)
        self.assertEqual(result["matching_parent_link_count"], 9)
        self.assertIsNone(result["blocks"][5]["timestamp_unix"])

    def test_missing_boundary_is_not_matching(self):
        self.evidence["observations"][0]["block"] = None
        result = self.run_report()
        self.assertEqual(result["blocks"][0]["saved_hash_status"], "unavailable")
        self.assertEqual(result["matching_saved_anchor_count"], 1)
        self.assertEqual(result["unavailable_parent_link_count"], 1)

    def test_all_null_is_not_empty_or_consistent(self):
        for item in self.evidence["observations"]:
            item["block"] = None
        result = self.run_report()
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["available_block_count"], 0)
        self.assertEqual(result["unavailable_parent_link_count"], 11)
        self.assertEqual(result["transfer_count"], 3)

    def test_changed_last_anchor(self):
        block = self.evidence["observations"][-1]["block"]
        block["hash"] = changed_hash(block["hash"])
        result = self.run_report()
        self.assertEqual(result["status"], "conflicting")
        self.assertEqual(result["conflicting_saved_anchor_count"], 1)
        self.assertEqual(result["matching_parent_link_count"], 11)

    def test_conflict_takes_precedence_over_missing(self):
        self.evidence["observations"][5]["block"] = None
        block = self.evidence["observations"][-1]["block"]
        block["hash"] = changed_hash(block["hash"])
        self.assertEqual(self.run_report()["status"], "conflicting")

    def test_equal_and_decreasing_timestamps(self):
        before = self.evidence["observations"][4]["block"]["timestamp"]
        for offset in (0, -1):
            with self.subTest(offset=offset):
                self.evidence["observations"][5]["block"]["timestamp"] = hex(int(before, 16) + offset)
                result = self.run_report()
                self.assertEqual(result["status"], "conflicting")
                self.assertEqual(result["non_increasing_timestamp_count"], 1)
                self.assertEqual(result["links"][4]["elapsed_seconds"], str(offset))

    def test_single_block_uses_both_roles_no_parent_assertion(self):
        self.capture["from_block"] = self.capture["to_block"]
        self.capture["from_block_anchor"] = copy.deepcopy(self.capture["to_block_anchor"])
        self.evidence["observations"] = self.evidence["observations"][-1:]
        result = self.run_report()
        self.assertEqual(result["status"], "consistent")
        self.assertEqual(result["saved_anchor_count"], 1)
        self.assertEqual(result["links"], [])
        self.assertEqual(result["transfer_count"], 3)

    def test_empty_transfer_projection_keeps_real_chain(self):
        # Synthetic log omission for behavior testing, not a new chain capture.
        self.capture.update(raw_logs=[], transfers=[], transfer_count=0, duplicate_count=0)
        result = self.run_report()
        self.assertEqual(result["status"], "consistent")
        self.assertEqual(result["transfer_count"], 0)
        self.assertEqual(result["matching_parent_link_count"], 11)

    def test_duplicate_omitted_extra_and_reordered_blocks_rejected(self):
        original = copy.deepcopy(self.evidence["observations"])
        variants = [original[:-1], original + original[-1:], original[::-1],
                    original[:4] + original[3:4] + original[5:]]
        for variant in variants:
            with self.subTest(length=len(variant)):
                self.evidence["observations"] = variant
                with self.assertRaises(c.window.RpcError):
                    self.run_report()

    def test_exact_schema_and_types(self):
        original = copy.deepcopy(self.evidence)
        variants = [dict(original, chain_id=True), dict(original, schema_version=1.0),
                    dict(original, observed_at="2026-10-13T10:00:00"),
                    dict(original, rpc="http://example.com"), dict(original, verdict="consistent")]
        for evidence in variants:
            with self.subTest(evidence=evidence.keys()):
                self.evidence = evidence
                with self.assertRaises(c.window.RpcError):
                    self.run_report()

    def test_requested_number_boolean_and_float_refused(self):
        for value in (True, float(self.capture["from_block"])):
            self.evidence["observations"][0]["requested_number"] = value
            with self.assertRaises(c.window.RpcError):
                self.run_report()

    def test_bad_header_fields(self):
        original = copy.deepcopy(self.evidence["observations"][0]["block"])
        for key, value in (("number", hex(self.capture["from_block"] + 1)),
                           ("timestamp", True), ("timestamp", "0x00"),
                           ("timestamp", hex(2**64)), ("hash", "0x12"),
                           ("parentHash", None), ("extra", "untrusted")):
            with self.subTest(key=key, value=value):
                self.evidence["observations"][0]["block"] = dict(original, **{key: value})
                with self.assertRaises(c.window.RpcError):
                    self.run_report()

    def test_tampered_capture_prevents_network(self):
        self.capture["transfers"][0]["raw_value"] = "1"
        with patch.object(c.window, "rpc", side_effect=AssertionError("network before validation")):
            with self.assertRaises(c.window.RpcError):
                c.collect(self.capture)

    def test_oversized_window_prevents_network(self):
        self.capture["from_block"] = self.capture["to_block"] - 64
        self.capture["from_block_anchor"]["number"] = self.capture["from_block"]
        with patch.object(c.window, "rpc", side_effect=AssertionError("network before bound")):
            with self.assertRaisesRegex(c.window.RpcError, "64 blocks"):
                c.collect(self.capture)

    def test_exactly_64_blocks_plan_is_allowed(self):
        self.capture["from_block"] = self.capture["to_block"] - 63
        self.capture["from_block_anchor"]["number"] = self.capture["from_block"]
        checked, _ = c.plan(self.capture)
        self.assertEqual(checked["to_block"] - checked["from_block"] + 1, 64)

    def test_collect_calls_only_exact_read_plan_and_strips_extras(self):
        def response(endpoint, method, params):
            if method == "eth_chainId":
                self.assertEqual(params, [])
                return "0x1"
            self.assertEqual(method, "eth_getBlockByNumber")
            self.assertIs(params[1], False)
            index = int(params[0], 16) - self.capture["from_block"]
            return dict(self.evidence["observations"][index]["block"], transactions=[])
        with patch.object(c.window, "rpc", side_effect=response) as rpc:
            collected = c.collect(self.capture)
        self.assertEqual(rpc.call_count, 13)
        self.assertEqual(collected["observations"], self.evidence["observations"])
        self.assertEqual(c.report(self.capture, collected)["status"], "consistent")

    def test_wrong_chain_and_rpc_error_abort(self):
        with patch.object(c.window, "rpc", return_value="0x2") as rpc:
            with self.assertRaises(c.window.RpcError):
                c.collect(self.capture)
            self.assertEqual(rpc.call_count, 1)
        with patch.object(c.window, "rpc", side_effect=c.window.RpcError("provider failed")):
            with self.assertRaisesRegex(c.window.RpcError, "provider failed"):
                c.collect(self.capture)

    def test_collect_null_is_retained(self):
        with patch.object(c.window, "rpc", side_effect=["0x1"] + [None] * 12):
            collected = c.collect(self.capture)
        self.assertEqual(c.report(self.capture, collected)["status"], "unavailable")

    def test_cli_live_status_and_no_partial_json_on_failure(self):
        capture_path = str(HERE.parent / "transfer-crosscheck" / "publicnode.json")
        self.evidence["observations"][5]["block"] = None
        with patch.object(c, "collect", return_value=self.evidence):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(c.main(["--capture", capture_path, "--live"]), 1)
            self.assertEqual(json.loads(output.getvalue())["status"], "unavailable")
        with patch.object(c, "collect", side_effect=c.window.RpcError("provider failed")):
            output = io.StringIO()
            with contextlib.redirect_stdout(output), self.assertRaises(c.window.RpcError):
                c.main(["--capture", capture_path, "--live"])
            self.assertEqual(output.getvalue(), "")

    def test_cli_requires_explicit_mode(self):
        for args in (["--demo", "--live"], ["--demo", "--rpc", c.window.DEFAULT_RPC],
                     ["--capture", "missing.json"], ["--capture", "missing.json", "--evidence",
                      "missing.json", "--rpc", c.window.DEFAULT_RPC]):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as exc:
                    c.main(args)
                self.assertEqual(exc.exception.code, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
