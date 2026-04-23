"""Validate static route consistency and regression expectations."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Dict, List


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "static_routes.json"
SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "tests" / "route_snapshot.sha256"


def load_config() -> Dict:
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def canonical_flow_repr(config: Dict) -> str:
    return json.dumps(config["flows"], indent=2, sort_keys=True)


def compute_digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def trace_path(config: Dict, source_host: str, dest_host: str) -> List[str]:
    flows = config["flows"]
    hosts = config["hosts"]
    switches = config["switches"]
    dest_mac = hosts[dest_host]["mac"]
    current_switch = hosts[source_host]["switch"]
    destination_switch = hosts[dest_host]["switch"]
    path = [current_switch]

    while current_switch != destination_switch:
        dpid = str(switches[current_switch]["dpid"])
        out_port = flows[dpid][dest_mac]
        next_switch = None
        for neighbor, port in switches[current_switch]["uplinks"].items():
            if port == out_port:
                next_switch = neighbor
                break
        if next_switch is None:
            raise ValueError(
                f"Could not continue path from {current_switch} towards {dest_host}; "
                f"port {out_port} does not match any uplink."
            )
        current_switch = next_switch
        path.append(current_switch)

    return path


def validate_expected_paths(config: Dict) -> List[str]:
    errors = []
    for entry in config["expected_paths"]:
        source_host, dest_host = [part.strip() for part in entry["traffic"].split("->")]
        actual = trace_path(config, source_host, dest_host)
        if actual != entry["path"]:
            errors.append(
                f"{entry['traffic']}: expected {' -> '.join(entry['path'])}, "
                f"got {' -> '.join(actual)}"
            )
    return errors


def validate_host_ports(config: Dict) -> List[str]:
    errors = []
    for host_name, host in config["hosts"].items():
        switch_name = host["switch"]
        dpid = str(config["switches"][switch_name]["dpid"])
        learned_port = config["flows"][dpid][host["mac"]]
        if learned_port != host["port"]:
            errors.append(
                f"{host_name}: switch {switch_name} should forward local traffic "
                f"to port {host['port']} but config uses port {learned_port}"
            )
    return errors


def compare_snapshot(digest: str) -> bool:
    if not SNAPSHOT_PATH.exists():
        print(f"Snapshot file not found: {SNAPSHOT_PATH}")
        return False
    saved = SNAPSHOT_PATH.read_text(encoding="utf-8").strip()
    return saved == digest


def write_snapshot(digest: str):
    SNAPSHOT_PATH.write_text(f"{digest}\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Validate SDN static routing plan.")
    parser.add_argument("--write-snapshot", action="store_true", help="Write flow digest snapshot")
    parser.add_argument("--compare-snapshot", action="store_true", help="Compare against saved snapshot")
    args = parser.parse_args()

    config = load_config()
    flow_repr = canonical_flow_repr(config)
    digest = compute_digest(flow_repr)

    errors = []
    errors.extend(validate_expected_paths(config))
    errors.extend(validate_host_ports(config))

    print("Topology:", config["topology_name"])
    print("Flow digest:", digest)
    print("Expected path count:", len(config["expected_paths"]))

    if errors:
        print("\nValidation errors:")
        for error in errors:
            print("-", error)
        raise SystemExit(1)

    if args.write_snapshot:
        write_snapshot(digest)
        print(f"Snapshot written to {SNAPSHOT_PATH}")

    if args.compare_snapshot:
        if compare_snapshot(digest):
            print("Snapshot matches. Route reinstall will preserve the same static path plan.")
        else:
            print("Snapshot mismatch. Static route plan has changed.")
            raise SystemExit(1)

    print("Validation successful.")


if __name__ == "__main__":
    main()
