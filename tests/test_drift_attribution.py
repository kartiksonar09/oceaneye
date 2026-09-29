"""
OceanEye Phase 4: Drift & Attribution Pipeline Unit & Integration Tests
Tests:
  - Haversine distance & bearing
  - Coordinate displacement projections
  - Spatio-temporal environmental forcing interpolation
  - Forward and backward Lagrangian trajectory integration
  - Particle ensemble simulation & source region geometry
  - AIS vessel trajectory correlation
  - Missing and out-of-bounds forcing handling
  - Empty AIS and invalid timestamp handling
  - End-to-end pipeline execution
"""

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

import sys
SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from drift.geo import (
    calculate_bearing,
    calculate_trajectory_length,
    compute_bounding_box,
    compute_convex_hull,
    displacement_to_latlon,
    haversine_distance,
    latlon_to_displacement,
    point_to_trajectory_distance,
)
from drift.interpolation import EnvironmentalForcing
from drift.model import (
    calculate_trajectory_summary,
    simulate_backward_drift,
    simulate_forward_drift,
)
from drift.ensemble import simulate_particle_ensemble
from drift.attribution import (
    correlate_and_rank_vessels,
    correlate_vessel_with_drift,
)
from run_drift_attribution import run_pipeline


class TestDriftAttributionPipeline(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    # 1. Geospatial Calculations
    def test_haversine_distance(self):
        # London to Paris ~ 343 km
        dist = haversine_distance(51.5074, -0.1278, 48.8566, 2.3522)
        self.assertAlmostEqual(dist, 343.5, delta=10.0)

        # Identical point should be 0.0
        dist_zero = haversine_distance(-20.4, 57.7, -20.4, 57.7)
        self.assertEqual(dist_zero, 0.0)

    def test_calculate_bearing(self):
        # Bearing due North: 0 deg
        b_north = calculate_bearing(0.0, 0.0, 1.0, 0.0)
        self.assertAlmostEqual(b_north, 0.0, delta=1.0)

        # Bearing due East: 90 deg
        b_east = calculate_bearing(0.0, 0.0, 0.0, 1.0)
        self.assertAlmostEqual(b_east, 90.0, delta=1.0)

    def test_displacement_projections(self):
        lat0, lon0 = -20.0, 57.0
        # Displace 111139 meters north (~ 1.0 degree lat)
        new_lat, new_lon = displacement_to_latlon(lat0, lon0, dx_meters=0.0, dy_meters=111139.0)
        self.assertAlmostEqual(new_lat, -19.0, delta=0.01)
        self.assertAlmostEqual(new_lon, 57.0, delta=0.01)

        # Inverse conversion
        dx, dy = latlon_to_displacement(lat0, lon0, new_lat, new_lon)
        self.assertAlmostEqual(dy, 111139.0, delta=50.0)
        self.assertAlmostEqual(dx, 0.0, delta=50.0)

    def test_trajectory_metrics_and_convex_hull(self):
        df_traj = pd.DataFrame([
            {"latitude": 0.0, "longitude": 0.0, "timestamp": "2020-08-01T00:00:00Z"},
            {"latitude": 0.0, "longitude": 1.0, "timestamp": "2020-08-01T01:00:00Z"},
            {"latitude": 1.0, "longitude": 1.0, "timestamp": "2020-08-01T02:00:00Z"},
        ])
        # Trajectory length should be ~ 111 km + 111 km ~ 222 km
        length_km = calculate_trajectory_length(df_traj)
        self.assertAlmostEqual(length_km, 222.0, delta=10.0)

        # Distance to point (0.0, 0.5) should be 0 (lies along first segment)
        p_res = point_to_trajectory_distance(0.0, 0.5, df_traj)
        self.assertLess(p_res["min_distance_km"], 60.0)
        self.assertEqual(p_res["closest_index"], 0)

        # Convex hull
        pts = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.5, 0.5)]
        hull = compute_convex_hull(pts)
        self.assertGreaterEqual(len(hull), 4)

    # 2. Environmental Forcing Interpolation
    def test_environmental_forcing_synthetic_dataset(self):
        # Create minimal synthetic NetCDF files for testing
        curr_file = self.temp_dir / "test_currents.nc"
        wind_file = self.temp_dir / "test_wind.nc"

        lats = np.array([-21.0, -20.0, -19.0])
        lons = np.array([57.0, 58.0, 59.0])
        times = pd.date_range("2020-08-05", periods=5, freq="D")

        ds_c = xr.Dataset(
            {
                "uo_surface": (["time", "latitude", "longitude"], np.ones((5, 3, 3)) * 0.25),
                "vo_surface": (["time", "latitude", "longitude"], np.ones((5, 3, 3)) * -0.15),
            },
            coords={"time": times, "latitude": lats, "longitude": lons},
        )
        ds_c.to_netcdf(curr_file)

        ds_w = xr.Dataset(
            {
                "eastward_wind": (["time", "latitude", "longitude"], np.ones((5, 3, 3)) * 4.0),
                "northward_wind": (["time", "latitude", "longitude"], np.ones((5, 3, 3)) * 2.0),
            },
            coords={"time": times, "latitude": lats, "longitude": lons},
        )
        ds_w.to_netcdf(wind_file)

        forcing = EnvironmentalForcing(currents_path=curr_file, wind_path=wind_file)
        self.assertTrue(forcing.is_currents_available())
        self.assertTrue(forcing.is_wind_available())

        # Test valid query
        u_c, v_c, valid_c = forcing.get_current_vector(-20.0, 58.0, "2020-08-06T12:00:00Z")
        self.assertTrue(valid_c)
        self.assertAlmostEqual(u_c, 0.25, delta=0.01)
        self.assertAlmostEqual(v_c, -0.15, delta=0.01)

        u_w, v_w, valid_w = forcing.get_wind_vector(-20.0, 58.0, "2020-08-06T12:00:00Z")
        self.assertTrue(valid_w)
        self.assertAlmostEqual(u_w, 4.0, delta=0.01)
        self.assertAlmostEqual(v_w, 2.0, delta=0.01)

        # Net velocity: u_curr + 0.03 * u_wind = 0.25 + 0.12 = 0.37
        net = forcing.get_net_velocity(-20.0, 58.0, "2020-08-06T12:00:00Z", windage=0.03)
        self.assertAlmostEqual(net["u_total"], 0.37, delta=0.01)
        self.assertEqual(net["forcing_status"], "complete")

        # Out-of-bounds test
        u_oob, v_oob, valid_oob = forcing.get_current_vector(45.0, 10.0, "2020-08-06T12:00:00Z")
        self.assertFalse(valid_oob)
        self.assertEqual(u_oob, 0.0)

        forcing.close()

    # 3. Drift Model Forward & Backward Integration
    def test_forward_and_backward_drift_simulation(self):
        # Create uniform forcing
        curr_file = self.temp_dir / "test_curr2.nc"
        lats = np.array([-21.0, -19.0])
        lons = np.array([57.0, 59.0])
        times = pd.date_range("2020-08-05", periods=3, freq="D")

        ds_c = xr.Dataset(
            {
                "uo_surface": (["time", "latitude", "longitude"], np.ones((3, 2, 2)) * 0.1),
                "vo_surface": (["time", "latitude", "longitude"], np.zeros((3, 2, 2))),
            },
            coords={"time": times, "latitude": lats, "longitude": lons},
        )
        ds_c.to_netcdf(curr_file)

        forcing = EnvironmentalForcing(currents_path=curr_file)

        # Forward drift: should drift eastward (longitude increases)
        df_fwd = simulate_forward_drift(
            start_lat=-20.0,
            start_lon=58.0,
            start_time="2020-08-05T00:00:00Z",
            duration_hours=12.0,
            timestep_seconds=3600,
            forcing=forcing,
            windage=0.0,
        )
        self.assertEqual(len(df_fwd), 13)
        self.assertGreater(df_fwd.iloc[-1]["longitude"], df_fwd.iloc[0]["longitude"])
        self.assertAlmostEqual(df_fwd.iloc[-1]["latitude"], df_fwd.iloc[0]["latitude"], delta=0.01)

        # Backward drift: should backtrack westward (longitude decreases)
        df_bwd = simulate_backward_drift(
            start_lat=-20.0,
            start_lon=58.0,
            start_time="2020-08-05T12:00:00Z",
            duration_hours=12.0,
            timestep_seconds=3600,
            forcing=forcing,
            windage=0.0,
        )
        self.assertEqual(len(df_bwd), 13)
        self.assertLess(df_bwd.iloc[-1]["longitude"], df_bwd.iloc[0]["longitude"])

        fwd_sum = calculate_trajectory_summary(df_fwd, mode="forward")
        self.assertIn("cumulative_path_km", fwd_sum)

        forcing.close()

    # 4. Particle Ensemble & Source Region Generation
    def test_particle_ensemble_and_source_region(self):
        curr_file = self.temp_dir / "test_curr3.nc"
        times = pd.date_range("2020-08-05", periods=3, freq="D")
        ds_c = xr.Dataset(
            {
                "uo_surface": (["time", "latitude", "longitude"], np.ones((3, 2, 2)) * 0.1),
                "vo_surface": (["time", "latitude", "longitude"], np.ones((3, 2, 2)) * -0.1),
            },
            coords={"time": times, "latitude": [-21.0, -19.0], "longitude": [57.0, 59.0]},
        )
        ds_c.to_netcdf(curr_file)
        forcing = EnvironmentalForcing(currents_path=curr_file)

        ens_df, src_meta = simulate_particle_ensemble(
            start_lat=-20.0,
            start_lon=58.0,
            start_time="2020-08-06T00:00:00Z",
            duration_hours=6.0,
            timestep_seconds=3600,
            forcing=forcing,
            num_particles=10,
            seed=42,
        )
        self.assertEqual(src_meta["region_type"], "estimated_possible_source_region")
        self.assertIn("centroid", src_meta)
        self.assertIn("dispersion_radius_95_km", src_meta)
        self.assertEqual(len(src_meta["terminal_endpoints"]), 10)
        self.assertTrue(len(ens_df) >= 70)  # 10 particles * 7 steps

        forcing.close()

    # 5. AIS Correlation & Ranking Adapter
    def test_ais_correlation_and_ranking(self):
        bwd_traj = pd.DataFrame([
            {"latitude": -20.4, "longitude": 57.7, "timestamp": "2020-08-06T12:00:00Z"},
            {"latitude": -20.3, "longitude": 57.6, "timestamp": "2020-08-06T06:00:00Z"},
            {"latitude": -20.2, "longitude": 57.5, "timestamp": "2020-08-06T00:00:00Z"},
        ])
        src_meta = {
            "centroid": {"latitude": -20.2, "longitude": 57.5},
            "dispersion_radius_95_km": 15.0,
            "estimated_release_timestamp": "2020-08-06T00:00:00Z",
        }

        # Vessel 1: close to source region at release time
        v1_pings = pd.DataFrame([
            {"mmsi": "111", "vessel_name": "V1", "latitude": -20.21, "longitude": 57.51, "timestamp": "2020-08-06T00:30:00Z", "speed_knots": 3.0, "course_deg": 45.0}
        ])
        # Vessel 2: distant
        v2_pings = pd.DataFrame([
            {"mmsi": "222", "vessel_name": "V2", "latitude": -21.50, "longitude": 59.00, "timestamp": "2020-08-06T00:30:00Z", "speed_knots": 15.0, "course_deg": 180.0}
        ])
        vessels_df = pd.concat([v1_pings, v2_pings], ignore_index=True)

        feats_df, ranked = correlate_and_rank_vessels(
            vessels_df=vessels_df,
            backward_trajectory_df=bwd_traj,
            source_region_meta=src_meta,
            model_path=None,  # Tests heuristic fallback
        )
        self.assertEqual(len(ranked), 2)
        # Vessel 1 should be ranked #1
        self.assertEqual(ranked[0]["vessel_id"], "111")
        self.assertEqual(ranked[0]["rank"], 1)
        self.assertGreater(ranked[0]["prioritization_score"], ranked[1]["prioritization_score"])
        self.assertIn("disclaimer", ranked[0])

    # 6. Edge Cases & Robustness
    def test_empty_ais_handling(self):
        bwd_traj = pd.DataFrame([{"latitude": -20.0, "longitude": 57.0, "timestamp": "2020-08-06T00:00:00Z"}])
        src_meta = {"centroid": {"latitude": -20.0, "longitude": 57.0}}
        df_empty = pd.DataFrame()
        f_df, ranked = correlate_and_rank_vessels(df_empty, bwd_traj, src_meta)
        self.assertEqual(len(ranked), 0)
        self.assertTrue(f_df.empty)

    # 7. End-to-End Synthetic Pipeline Execution
    def test_end_to_end_synthetic_pipeline(self):
        # Run pipeline against Wakashio event (which has real CMEMS processed NetCDFs)
        res = run_pipeline(
            event_name="wakashio",
            forward_hours=6.0,
            backward_hours=6.0,
            timestep_seconds=3600,
            num_particles=5,
            overwrite=True,
        )
        self.assertEqual(res["status"], "success")
        self.assertTrue(Path(res["forward_path"]).exists())
        self.assertTrue(Path(res["backward_path"]).exists())
        self.assertTrue(Path(res["source_region_path"]).exists())
        self.assertTrue(Path(res["candidates_path"]).exists())
        self.assertGreater(len(res["ranked_candidates"]), 0)


if __name__ == "__main__":
    unittest.main()
