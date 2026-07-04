import csv
import importlib.util
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "bin" / "route_engine.exe"

spec = importlib.util.spec_from_file_location("gui", ROOT / "python" / "city_routes_gui.py")
gui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gui)


class ProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model = gui.GraphModel(ROOT / "data")
        cls.model.load()

    def test_expected_graph_size(self):
        self.assertEqual(len(self.model.cities), 500)
        self.assertGreater(len(self.model.roads), 1000)

    def test_ids_and_weights_are_valid(self):
        ids = {c["id"] for c in self.model.cities}
        self.assertEqual(ids, set(range(500)))
        self.assertTrue(all(r["source"] in ids and r["target"] in ids and r["weight"] > 0 for r in self.model.roads))

    def test_dijkstra_route_endpoints_and_distance(self):
        distance, path = self.model.route(0, 499)
        self.assertEqual((path[0], path[-1]), (0, 499))
        self.assertGreater(distance, 0)

    def test_same_city_route(self):
        distance, path = self.model.route(17, 17)
        self.assertEqual(distance, 0)
        self.assertEqual(path, [17])

    def test_thickness_monotonic(self):
        self.assertLess(self.model.line_width(self.model.weight_min), self.model.line_width(self.model.weight_max))

    def test_geographic_clusters(self):
        clusters = {c["cluster"] for c in self.model.cities}
        self.assertEqual(clusters, set(range(9)))

    def test_engine_stats(self):
        result = subprocess.run([str(ENGINE), "stats", str(ROOT / "data")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("cities,500", result.stdout)


if __name__ == "__main__":
    unittest.main()
