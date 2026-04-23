import json
import unittest
from pathlib import Path

from src.tools.validate_routes import (
    canonical_flow_repr,
    compute_digest,
    load_config,
    validate_expected_paths,
    validate_host_ports,
)


class StaticRouteTests(unittest.TestCase):
    def test_path_plan_is_valid(self):
        config = load_config()
        self.assertEqual(validate_expected_paths(config), [])

    def test_local_host_ports_are_consistent(self):
        config = load_config()
        self.assertEqual(validate_host_ports(config), [])

    def test_flow_digest_is_stable(self):
        config = load_config()
        digest = compute_digest(canonical_flow_repr(config))
        snapshot_path = Path(__file__).resolve().parent / "route_snapshot.sha256"
        expected = snapshot_path.read_text(encoding="utf-8").strip()
        self.assertEqual(digest, expected)

    def test_config_contains_eight_expected_paths(self):
        config_path = Path(__file__).resolve().parents[1] / "src" / "config" / "static_routes.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(len(config["expected_paths"]), 8)


if __name__ == "__main__":
    unittest.main()
