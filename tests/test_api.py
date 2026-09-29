"""
OceanEye Phase 5: FastAPI Backend Automated Unit & Integration Tests
Validates:
- Root & Health status endpoints
- Dynamic Events listing & details retrieval
- 404 handling on non-existent events without traceback leakage
- Sentinel-1 Detection metadata & strict geometry: null contract
- Phase 4 Drift trajectories & source region GeoJSON conversion
- Phase 4 Attribution rankings & legal non-responsibility confirmation
- On-demand Lagrangian drift simulation endpoint & validation limits
- RFC 7946 GeoJSON [longitude, latitude] coordinate ordering & closed polygons
- CORS headers for frontend integration
"""

import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

from api.main import app
from api.utils.geojson import (
    point_to_geojson_feature,
    source_region_to_polygon_feature,
    trajectory_to_linestring_feature,
)


class TestOceanEyeAPI(unittest.TestCase):
    """Test suite for OceanEye FastAPI backend service."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    # -------------------------------------------------------------
    # 1. System & Health Endpoints
    # -------------------------------------------------------------

    def test_root_endpoint(self):
        """GET / returns service status and app metadata."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("OceanEye", data["app_name"])
        self.assertEqual(data["version"], "1.0.0")
        self.assertEqual(data["docs_url"], "/docs")

    def test_health_endpoint(self):
        """GET /health returns healthy status, version, and ISO timestamp."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["version"], "1.0.0")
        self.assertIn("timestamp", data)

    # -------------------------------------------------------------
    # 2. Events API
    # -------------------------------------------------------------

    def test_list_events(self):
        """GET /api/events returns dynamically configured events."""
        response = self.client.get("/api/events")
        self.assertEqual(response.status_code, 200)
        events = response.json()
        self.assertIsInstance(events, list)
        self.assertGreaterEqual(len(events), 2)

        event_ids = [e["event_id"] for e in events]
        self.assertIn("wakashio", event_ids)
        self.assertIn("sanchi", event_ids)

        for event in events:
            self.assertIn("name", event)
            self.assertIn("latitude", event)
            self.assertIn("longitude", event)
            self.assertIn("start_date", event)
            self.assertIn("end_date", event)
            self.assertIn("radius_km", event)

    def test_get_valid_event(self):
        """GET /api/events/{event_id} returns detailed metadata and bounding box."""
        response = self.client.get("/api/events/wakashio")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["event_id"], "wakashio")
        self.assertEqual(data["name"], "Wakashio Oil Spill")
        self.assertEqual(data["latitude"], -20.4)
        self.assertEqual(data["longitude"], 57.75)
        self.assertIn("bounding_box", data)
        self.assertIn("data_availability", data)
        self.assertTrue(data["data_availability"]["sentinel"])
        self.assertTrue(data["data_availability"]["drift"])

    def test_get_invalid_event_404(self):
        """GET /api/events/{event_id} returns 404 with clean detail message for missing events."""
        response = self.client.get("/api/events/nonexistent_incident_999")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("detail", data)
        self.assertIn("not found", data["detail"].lower())
        # Ensure no python stack trace is leaked
        self.assertNotIn("Traceback", response.text)
        self.assertNotIn("File \"", response.text)

    # -------------------------------------------------------------
    # 3. Detection API
    # -------------------------------------------------------------

    def test_get_detection_wakashio(self):
        """
        GET /api/events/wakashio/detection returns Sentinel-1 metadata
        and STRICTLY enforces geometry=None when real pixel segmentation is unavailable.
        """
        response = self.client.get("/api/events/wakashio/detection")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["event_id"], "wakashio")
        self.assertEqual(data["detection_status"], "metadata_available")
        # Critical contract: geometry must be null
        self.assertIsNone(data["geometry"])
        self.assertIn("geometry_notice", data)
        self.assertIn("unavailable", data["geometry_notice"].lower())
        self.assertEqual(data["platform"], "Synthetic Aperture Radar")
        self.assertEqual(data["sensor_mode"], "IW")
        self.assertEqual(data["product_type"], "GRD")
        self.assertIn("footprint_polygon", data)
        self.assertIn("disclaimer", data)

    def test_get_detection_event_without_sentinel(self):
        """GET /api/events/event3/detection returns clean no_sentinel_data status and null geometry."""
        response = self.client.get("/api/events/event3/detection")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["event_id"], "event3")
        self.assertEqual(data["detection_status"], "no_sentinel_data")
        self.assertIsNone(data["geometry"])

    def test_get_detection_invalid_event_404(self):
        """GET /api/events/{invalid}/detection returns 404."""
        response = self.client.get("/api/events/invalid_event_abc/detection")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("detail", data)

    # -------------------------------------------------------------
    # 4. Drift API
    # -------------------------------------------------------------

    def test_get_drift_wakashio(self):
        """GET /api/events/wakashio/drift returns stored trajectories as GeoJSON."""
        response = self.client.get("/api/events/wakashio/drift")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["event_id"], "wakashio")

        # Forward trajectory LineString verification
        fwd = data["forward_trajectory"]
        self.assertIsNotNone(fwd)
        self.assertEqual(fwd["type"], "Feature")
        self.assertEqual(fwd["geometry"]["type"], "LineString")
        coords_fwd = fwd["geometry"]["coordinates"]
        self.assertGreaterEqual(len(coords_fwd), 2)
        # Check coordinates order: [longitude, latitude]
        # Wakashio is roughly lon ~ 57.8, lat ~ -19.8
        self.assertGreater(coords_fwd[0][0], 50.0)  # Longitude > 50
        self.assertLess(coords_fwd[0][1], 0.0)     # Latitude < 0 (Southern Hemisphere)

        # Backward trajectory LineString verification
        bwd = data["backward_trajectory"]
        self.assertIsNotNone(bwd)
        self.assertEqual(bwd["type"], "Feature")
        self.assertEqual(bwd["geometry"]["type"], "LineString")

        # Source region Polygon verification
        src = data["source_region"]
        self.assertIsNotNone(src)
        self.assertEqual(src["type"], "Feature")
        self.assertEqual(src["geometry"]["type"], "Polygon")
        poly_ring = src["geometry"]["coordinates"][0]
        self.assertGreaterEqual(len(poly_ring), 4)
        # Verify closed ring (first vertex == last vertex)
        self.assertEqual(poly_ring[0], poly_ring[-1])
        # Verify GeoJSON order [lon, lat]
        self.assertGreater(poly_ring[0][0], 50.0)
        self.assertLess(poly_ring[0][1], 0.0)

        # Metadata checks
        self.assertIn("disclaimer", data)
        self.assertEqual(data["validation_data_mode"], "operational_forcing")

    def test_get_drift_missing_event_404(self):
        """GET /api/events/sanchi/drift returns 404 when drift outputs do not exist."""
        response = self.client.get("/api/events/sanchi/drift")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("detail", data)

    # -------------------------------------------------------------
    # 5. Attribution API
    # -------------------------------------------------------------

    def test_get_attribution_wakashio(self):
        """
        GET /api/events/wakashio/attribution returns candidate vessels
        with responsibility_confirmed=False and operational disclaimer.
        """
        response = self.client.get("/api/events/wakashio/attribution")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["event_id"], "wakashio")
        self.assertGreater(data["total_vessels_evaluated"], 0)
        self.assertIn("candidates", data)

        for cand in data["candidates"]:
            self.assertIn("vessel_id", cand)
            self.assertIn("vessel_name", cand)
            self.assertIn("prioritization_score", cand)
            self.assertIn("rank", cand)
            self.assertIn("min_distance_to_trajectory_km", cand)
            self.assertIn("min_distance_to_source_region_km", cand)
            self.assertIn("temporal_offset_to_source_hours", cand)
            # Critical contract: responsibility is strictly unconfirmed
            self.assertFalse(cand["responsibility_confirmed"])
            self.assertIn("disclaimer", cand)
            self.assertIn("DOES NOT constitute legal proof", cand["disclaimer"])

        self.assertIn("disclaimer", data)

    def test_get_attribution_missing_event_404(self):
        """GET /api/events/sanchi/attribution returns 404 when attribution is not generated."""
        response = self.client.get("/api/events/sanchi/attribution")
        self.assertEqual(response.status_code, 404)

    # -------------------------------------------------------------
    # 6. On-Demand Drift Simulation (POST /api/drift/simulate)
    # -------------------------------------------------------------

    def test_simulate_drift_valid_request(self):
        """POST /api/drift/simulate executes lightweight simulation and returns GeoJSON."""
        payload = {
            "latitude": -19.79856,
            "longitude": 57.88786,
            "timestamp": "2020-08-10T01:37:55Z",
            "forward_duration_hours": 2.0,
            "backward_duration_hours": 2.0,
            "timestep_seconds": 1800,
            "windage": 0.03,
            "particle_count": 3,
            "event_id": "wakashio",
        }
        response = self.client.post("/api/drift/simulate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["is_simulation"])
        self.assertEqual(data["simulation_type"], "on_demand_simulation")

        # Check forward trajectory
        fwd = data["forward_trajectory"]
        self.assertIsNotNone(fwd)
        self.assertEqual(fwd["type"], "Feature")
        self.assertEqual(fwd["geometry"]["type"], "LineString")
        coords = fwd["geometry"]["coordinates"]
        self.assertGreaterEqual(len(coords), 2)
        # Coordinate order: [longitude, latitude]
        self.assertGreater(coords[0][0], 50.0)
        self.assertLess(coords[0][1], 0.0)

        # Check backward trajectory
        bwd = data["backward_trajectory"]
        self.assertIsNotNone(bwd)
        self.assertEqual(bwd["geometry"]["type"], "LineString")

        # Check source region
        src = data["source_region"]
        self.assertIsNotNone(src)
        self.assertEqual(src["geometry"]["type"], "Polygon")
        ring = src["geometry"]["coordinates"][0]
        self.assertEqual(ring[0], ring[-1])  # Closed loop

        self.assertIn("summary", data)
        self.assertIn("disclaimer", data)

    def test_simulate_drift_invalid_inputs(self):
        """POST /api/drift/simulate rejects invalid latitudes, durations, and counts."""
        # 1. Latitude > 90
        res1 = self.client.post(
            "/api/drift/simulate",
            json={"latitude": 99.0, "longitude": 50.0, "timestamp": "2020-08-10T01:00:00Z"},
        )
        self.assertEqual(res1.status_code, 422)

        # 2. Longitude < -180
        res2 = self.client.post(
            "/api/drift/simulate",
            json={"latitude": 20.0, "longitude": -195.0, "timestamp": "2020-08-10T01:00:00Z"},
        )
        self.assertEqual(res2.status_code, 422)

        # 3. Particle count > 50 (DoS prevention)
        res3 = self.client.post(
            "/api/drift/simulate",
            json={"latitude": 20.0, "longitude": 50.0, "timestamp": "2020-08-10T01:00:00Z", "particle_count": 200},
        )
        self.assertEqual(res3.status_code, 422)

        # 4. Invalid timestamp format
        res4 = self.client.post(
            "/api/drift/simulate",
            json={"latitude": 20.0, "longitude": 50.0, "timestamp": "not-a-valid-date"},
        )
        self.assertEqual(res4.status_code, 422)

        # 5. Non-existent event_id
        res5 = self.client.post(
            "/api/drift/simulate",
            json={
                "latitude": 20.0,
                "longitude": 50.0,
                "timestamp": "2020-08-10T01:00:00Z",
                "event_id": "nonexistent_event_abc",
            },
        )
        self.assertEqual(res5.status_code, 404)

    # -------------------------------------------------------------
    # 7. Strict RFC 7946 GeoJSON Coordinate Ordering Tests
    # -------------------------------------------------------------

    def test_geojson_point_order(self):
        """GeoJSON Point coordinates must strictly follow [longitude, latitude]."""
        lat, lon = -20.4, 57.75
        pt = point_to_geojson_feature(lat, lon, {"name": "Test Point"})
        self.assertEqual(pt["type"], "Feature")
        self.assertEqual(pt["geometry"]["type"], "Point")
        # [0] is longitude, [1] is latitude
        self.assertEqual(pt["geometry"]["coordinates"][0], lon)
        self.assertEqual(pt["geometry"]["coordinates"][1], lat)

    def test_geojson_linestring_order(self):
        """GeoJSON LineString coordinates must strictly follow [longitude, latitude]."""
        records = [
            {"latitude": 10.0, "longitude": 20.0},
            {"latitude": 11.0, "longitude": 21.0},
        ]
        line = trajectory_to_linestring_feature(records)
        self.assertIsNotNone(line)
        self.assertEqual(line["geometry"]["type"], "LineString")
        self.assertEqual(line["geometry"]["coordinates"][0], [20.0, 10.0])
        self.assertEqual(line["geometry"]["coordinates"][1], [21.0, 11.0])

    def test_geojson_polygon_order_and_closed_loop(self):
        """GeoJSON Polygon must use [lon, lat] and automatically close the linear ring."""
        # Triangular vertices provided as [latitude, longitude]
        hull_pts = [
            [-20.0, 57.0],
            [-21.0, 58.0],
            [-20.5, 59.0],
        ]
        poly = source_region_to_polygon_feature(hull_pts)
        self.assertIsNotNone(poly)
        self.assertEqual(poly["geometry"]["type"], "Polygon")
        ring = poly["geometry"]["coordinates"][0]
        # Should have 4 vertices (3 + closed 4th)
        self.assertEqual(len(ring), 4)
        # Ring coordinates are [lon, lat]
        self.assertEqual(ring[0], [57.0, -20.0])
        self.assertEqual(ring[1], [58.0, -21.0])
        self.assertEqual(ring[2], [59.0, -20.5])
        self.assertEqual(ring[3], [57.0, -20.0])  # Closed loop matching first vertex

    # -------------------------------------------------------------
    # 8. CORS Headers Verification
    # -------------------------------------------------------------

    def test_cors_headers(self):
        """CORS preflight and GET request return proper Access-Control-Allow-Origin headers."""
        headers = {"Origin": "http://localhost:5173"}
        response = self.client.get("/health", headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:5173")

    # -------------------------------------------------------------
    # 9. Information Leakage & Error Handling
    # -------------------------------------------------------------

    def test_unhandled_exception_does_not_leak_traceback(self):
        """Unexpected internal 500 error returns generic error message without stack trace."""
        client_no_raise = TestClient(app, raise_server_exceptions=False)
        with patch("api.services.event_service.EventService.list_events", side_effect=RuntimeError("Simulated secret failure")):
            response = client_no_raise.get("/api/events")
            self.assertEqual(response.status_code, 500)
            data = response.json()
            self.assertIn("detail", data)
            self.assertNotIn("Simulated secret failure", data["detail"])
            self.assertNotIn("Traceback", response.text)
            self.assertNotIn("File \"", response.text)


if __name__ == "__main__":
    unittest.main()
