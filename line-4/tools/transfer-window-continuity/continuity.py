#!/usr/bin/env python3
"""Inspect every parent link in a small saved Ethereum transfer window."""
import argparse
import datetime as dt
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "anchors_for_continuity", HERE.parent / "transfer-anchor-audit" / "audit.py")
anchors = importlib.util.module_from_spec(spec)
spec.loader.exec_module(anchors)
window, reader = anchors.window, anchors.reader
MAX_BLOCKS = 64
MAX_EVIDENCE_BYTES = 99_000
LIMITATIONS = (
    "This checks provider-reported number/hash/parentHash/timestamp fields, not "
    "cryptographic header hashes, consensus, finality or event inclusion. A "
    "consistent chain does not prove complete logs, token balances, trade volume, "
    "price or activity in a specific v4 pool. Conflicts are conflicting "
    "observations, not proof of a reorganization. Reads are sequential and not "
    "atomic. The first block's parent lies outside the selected window and is "
    "not checked. Replay checks dated evidence, not the current chain."
)


def plan(capture):
    checked, known = anchors.plan(capture)
    if checked["to_block"] - checked["from_block"] + 1 > MAX_BLOCKS:
        raise window.RpcError("continuity check exceeds 64 blocks; select a smaller capture")
    return checked, {item["number"]: item for item in known}


def header(value, number):
    """Keep only explicitly checked public block fields; null stays unavailable."""
    if value is None:
        return None
    if type(value) is not dict:
        raise window.RpcError("block must be an object or null")
    if window.quantity(value.get("number"), "block number") != number:
        raise window.RpcError("block response has the wrong number")
    timestamp = window.quantity(value.get("timestamp"), "block timestamp")
    if timestamp >= 2**64:
        raise window.RpcError("block timestamp exceeds uint64")
    return {
        "number": hex(number),
        "hash": window.hex_bytes(value.get("hash"), 32, "block hash"),
        "parentHash": window.hex_bytes(value.get("parentHash"), 32, "parent hash"),
        "timestamp": hex(timestamp),
    }


def collect(capture, endpoint=window.DEFAULT_RPC):
    """Make 1..65 finite public reads; validate the entire plan before network I/O."""
    checked, _ = plan(capture)
    window.validate_endpoint(endpoint)
    chain = window.quantity(window.rpc(endpoint, "eth_chainId", []), "chain ID")
    if chain != 1:
        raise window.RpcError("Ethereum mainnet required")
    observations = []
    for number in range(checked["from_block"], checked["to_block"] + 1):
        value = window.rpc(endpoint, "eth_getBlockByNumber", [hex(number), False])
        observations.append({"requested_number": number, "block": header(value, number)})
    return {
        "kind": "erc20-transfer-continuity-observations", "schema_version": 1,
        "chain_id": 1, "rpc": endpoint,
        "observed_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "observations": observations,
    }


def report(capture, evidence):
    """Revalidate logs and all observations; derive every verdict from fields."""
    checked, known = plan(capture)
    if (type(evidence) is not dict or set(evidence) != {
            "kind", "schema_version", "chain_id", "rpc", "observed_at", "observations"}
            or evidence["kind"] != "erc20-transfer-continuity-observations"
            or type(evidence["schema_version"]) is not int or evidence["schema_version"] != 1
            or type(evidence["chain_id"]) is not int or evidence["chain_id"] != 1):
        raise window.RpcError("mainnet continuity evidence schema 1 required")
    if type(evidence["rpc"]) is not str:
        raise window.RpcError("evidence RPC must be a string")
    window.validate_endpoint(evidence["rpc"])
    timestamp = evidence["observed_at"]
    if type(timestamp) is not str or len(timestamp) > 40:
        raise window.RpcError("timezone-aware observation timestamp required")
    try:
        parsed = dt.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("missing timezone")
    except ValueError as exc:
        raise window.RpcError("invalid observation timestamp") from exc
    observations = evidence["observations"]
    start, end = checked["from_block"], checked["to_block"]
    if type(observations) is not list or len(observations) != end - start + 1:
        raise window.RpcError("evidence must cover every window block exactly once")
    rows, links = [], []
    previous = None
    for number, item in zip(range(start, end + 1), observations):
        if (type(item) is not dict or set(item) != {"requested_number", "block"}
                or type(item["requested_number"]) is not int
                or item["requested_number"] != number):
            raise window.RpcError("observations must match every planned number in order")
        if item["block"] is not None and (
                type(item["block"]) is not dict or set(item["block"]) != {
                    "number", "hash", "parentHash", "timestamp"}):
            raise window.RpcError("retained block must contain exactly four header fields")
        current = header(item["block"], number)
        saved = known.get(number)
        anchor_status = ("not_previously_observed" if saved is None else
                         "unavailable" if current is None else
                         "matching" if current["hash"] == saved["saved_hash"] else "conflicting")
        rows.append({
            "number": number, "available": current is not None,
            "observed_hash": None if current is None else current["hash"],
            "parent_hash": None if current is None else current["parentHash"],
            "timestamp_unix": None if current is None else str(int(current["timestamp"], 16)),
            "saved_hash": None if saved is None else saved["saved_hash"],
            "saved_hash_status": anchor_status,
            "transfer_count": 0 if saved is None else saved["transfer_count"],
        })
        if number != start:
            available = previous is not None and current is not None
            links.append({
                "parent_number": number - 1, "child_number": number,
                "parent_hash_status": ("unavailable" if not available else
                    "matching" if current["parentHash"] == previous["hash"] else "conflicting"),
                "timestamp_status": ("unavailable" if not available else
                    "increasing" if int(current["timestamp"], 16) > int(previous["timestamp"], 16)
                    else "non_increasing"),
                "elapsed_seconds": (None if not available else
                    str(int(current["timestamp"], 16) - int(previous["timestamp"], 16))),
            })
        previous = current
    missing = sum(not row["available"] for row in rows)
    anchor_conflicts = sum(row["saved_hash_status"] == "conflicting" for row in rows)
    link_conflicts = sum(link["parent_hash_status"] == "conflicting" for link in links)
    time_conflicts = sum(link["timestamp_status"] == "non_increasing" for link in links)
    conflicts = anchor_conflicts + link_conflicts + time_conflicts
    return {
        "kind": "erc20-transfer-window-continuity", "schema_version": 1,
        "read_only": True, "raw_logs_revalidated": True,
        "status": "conflicting" if conflicts else "unavailable" if missing else "consistent",
        "chain_id": 1, "token": checked["token"], "token_address": checked["token_address"],
        "from_block": start, "to_block": end, "transfer_count": checked["transfer_count"],
        "block_count": len(rows), "available_block_count": len(rows) - missing,
        "unavailable_block_count": missing, "saved_anchor_count": len(known),
        "newly_observed_interior_block_count": sum(
            row["available"] and row["saved_hash"] is None for row in rows),
        "matching_saved_anchor_count": sum(row["saved_hash_status"] == "matching" for row in rows),
        "conflicting_saved_anchor_count": anchor_conflicts,
        "matching_parent_link_count": sum(link["parent_hash_status"] == "matching" for link in links),
        "conflicting_parent_link_count": link_conflicts,
        "unavailable_parent_link_count": sum(link["parent_hash_status"] == "unavailable" for link in links),
        "non_increasing_timestamp_count": time_conflicts,
        "blocks": rows, "links": links, "rpc": evidence["rpc"],
        "observed_at": timestamp, "max_blocks": MAX_BLOCKS,
        "limitations": LIMITATIONS,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--demo", action="store_true", help="replay retained real ZTO evidence offline")
    source.add_argument("--capture", type=Path, help="saved workspace transfer-window capture")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true", help="read every numbered block now")
    mode.add_argument("--evidence", type=Path, help="replay a continuity observations JSON file")
    parser.add_argument("--rpc", help="public mainnet RPC; live only, defaults to PublicNode")
    args = parser.parse_args(argv)
    if args.demo:
        if args.live or args.evidence or args.rpc:
            parser.error("--demo uses its retained observations only")
        capture = reader.read_capture(HERE.parent / "transfer-crosscheck" / "publicnode.json")
        evidence = reader.read_capture(HERE / "observations.json", MAX_EVIDENCE_BYTES)
    else:
        if not (args.live or args.evidence):
            parser.error("choose --live or --evidence explicitly")
        if args.rpc and not args.live:
            parser.error("--rpc requires --live")
        capture = reader.read_capture(args.capture)
        evidence = (collect(capture, args.rpc or window.DEFAULT_RPC) if args.live else
                    reader.read_capture(args.evidence, MAX_EVIDENCE_BYTES))
    result = report(capture, evidence)
    result["mode"] = "live" if args.live else "replay"
    result["evidence"] = evidence
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "consistent" else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, window.RpcError) as exc:
        print("transfer-window-continuity: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
