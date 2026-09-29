import unittest
from api.services.scoring import calculate_ais_gap, calculate_suspicion_score

class TestScoring(unittest.TestCase):
    def test_calculate_ais_gap(self):
        # 45 minutes gap
        last_ping = "2026-09-24T10:00:00Z"
        current = "2026-09-24T10:45:00Z"
        gap = calculate_ais_gap(last_ping, current)
        self.assertAlmostEqual(gap, 45.0)

    def test_calculate_ais_gap_no_gap(self):
        last_ping = "2026-09-24T10:00:00Z"
        current = "2026-09-24T10:00:00Z"
        gap = calculate_ais_gap(last_ping, current)
        self.assertAlmostEqual(gap, 0.0)

    def test_calculate_suspicion_score_high(self):
        # High gap, close distance, tanker
        score = calculate_suspicion_score(ais_gap_minutes=150, distance_to_spill_km=0.5, is_tanker=True)
        self.assertAlmostEqual(score, 1.0)

    def test_calculate_suspicion_score_medium(self):
        # Medium gap, medium distance, not tanker
        score = calculate_suspicion_score(ais_gap_minutes=75, distance_to_spill_km=5.5, is_tanker=False)
        # Gap: 0.4 * (45/90) = 0.2
        # Dist: 0.4 * (1 - 4.5/9) = 0.4 * 0.5 = 0.2
        # Total: 0.4
        self.assertAlmostEqual(score, 0.4)

    def test_calculate_suspicion_score_low(self):
        # No gap, far away
        score = calculate_suspicion_score(ais_gap_minutes=10, distance_to_spill_km=15.0, is_tanker=False)
        self.assertAlmostEqual(score, 0.0)

if __name__ == '__main__':
    unittest.main()
