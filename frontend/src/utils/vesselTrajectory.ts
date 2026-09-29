import { AisHistoryPoint, Vessel } from '../types/api';

export interface TrajectoryPoint extends AisHistoryPoint {
  inGap: boolean;
  minutesAgo: number;
}

/**
 * Generates reconstructed historical AIS track points backwards from the current position.
 * Models historical dead-reckoning with realistic course variations and flags any
 * interval where the vessel's transponder was dark (AIS signal gap).
 */
export function getVesselTrajectory(
  vessel: Vessel,
  totalSteps = 24,
  intervalMinutes = 15
): TrajectoryPoint[] {
  const points: TrajectoryPoint[] = [];
  const baseTime = new Date(vessel.last_ais_update || Date.now()).getTime();

  // Gap definition: if vessel has an AIS gap, place it between [gapEndMin, gapStartMin] in the past
  const hasGap = Boolean(vessel.ais_gap_minutes && vessel.ais_gap_minutes > 0);
  const gapDurationMin = vessel.ais_gap_minutes || 0;
  const gapEndMin = 30; // ended 30m ago before re-appearing
  const gapStartMin = gapEndMin + gapDurationMin;

  let currentLat = vessel.lat;
  let currentLng = vessel.lng;
  let currentHeading = vessel.heading;
  let currentSpeed = vessel.speed_knots;

  // Step backwards in time
  for (let i = 0; i <= totalSteps; i++) {
    const minutesAgo = i * intervalMinutes;
    const timestamp = new Date(baseTime - minutesAgo * 60 * 1000).toISOString();

    const inGap = hasGap && minutesAgo >= gapEndMin && minutesAgo <= gapStartMin;

    points.unshift({
      timestamp,
      lat: Number(currentLat.toFixed(5)),
      lng: Number(currentLng.toFixed(5)),
      speed_knots: Number(currentSpeed.toFixed(1)),
      heading: Math.round(currentHeading),
      inGap,
      minutesAgo,
    });

    // Back-calculate previous position using reverse heading
    // 1 knot ≈ 0.514444 m/s. For intervalMinutes:
    const distanceMeters = currentSpeed * 0.514444 * (intervalMinutes * 60);
    // Reverse direction is (heading + 180) % 360
    const reverseRad = (((currentHeading + 180) % 360) * Math.PI) / 180;
    const deltaLat = (distanceMeters * Math.cos(reverseRad)) / 111139;
    const cosLat = Math.cos((currentLat * Math.PI) / 180);
    const deltaLng = (distanceMeters * Math.sin(reverseRad)) / (111139 * Math.max(0.1, cosLat));

    currentLat += deltaLat;
    currentLng += deltaLng;

    // Gradual drift in course and speed further in the past (deterministic based on index)
    const curve = Math.sin(i * 0.4) * 2.5;
    currentHeading = (currentHeading - curve + 360) % 360;
    currentSpeed = Math.max(3.0, Math.min(22.0, currentSpeed + Math.cos(i * 0.5) * 0.3));
  }

  return points;
}
