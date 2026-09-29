import { OperationalAlert, Spill, Suspect, Vessel } from '../types/api';
import { INITIAL_ALERTS, INITIAL_SPILLS, INITIAL_SUSPECTS, INITIAL_VESSELS } from './mockData';

class MockEngine {
  private spills: Spill[] = JSON.parse(JSON.stringify(INITIAL_SPILLS));
  private vessels: Vessel[] = JSON.parse(JSON.stringify(INITIAL_VESSELS));
  private suspects: Suspect[] = JSON.parse(JSON.stringify(INITIAL_SUSPECTS));
  private alerts: OperationalAlert[] = JSON.parse(JSON.stringify(INITIAL_ALERTS));
  private lastTick: number = Date.now();

  constructor() {
    this.startBackgroundSimulation();
  }

  private startBackgroundSimulation() {
    // Run simulation step every 10 seconds to update positions
    setInterval(() => {
      this.stepKinematics();
    }, 10_000);
  }

  private stepKinematics() {
    const now = Date.now();
    const dtSeconds = (now - this.lastTick) / 1000;
    this.lastTick = now;

    this.vessels = this.vessels.map((v) => {
      // 1 knot ≈ 0.514444 m/s. Convert to degrees: 1 deg lat ≈ 111,139 m
      const speedMs = v.speed_knots * 0.514444;
      const distanceMeters = speedMs * dtSeconds;
      const radHeading = (v.heading * Math.PI) / 180;

      const deltaLat = (distanceMeters * Math.cos(radHeading)) / 111139;
      const cosLat = Math.cos((v.lat * Math.PI) / 180);
      const deltaLng = (distanceMeters * Math.sin(radHeading)) / (111139 * Math.max(0.1, cosLat));

      // Realistic subtle heading/speed adjustment (simulating autopilot wave drift)
      const headingJitter = (Math.random() - 0.5) * 0.8;
      const speedJitter = (Math.random() - 0.5) * 0.1;
      const newHeading = (v.heading + headingJitter + 360) % 360;
      const newSpeed = Math.max(3.0, Math.min(24.0, v.speed_knots + speedJitter));

      return {
        ...v,
        lat: Number((v.lat + deltaLat).toFixed(6)),
        lng: Number((v.lng + deltaLng).toFixed(6)),
        heading: Number(newHeading.toFixed(1)),
        speed_knots: Number(newSpeed.toFixed(1)),
        last_ais_update: new Date(now).toISOString(),
      };
    });
  }

  public getSpills(): Promise<Spill[]> {
    return new Promise((resolve) => {
      // Simulate micro network delay
      setTimeout(() => {
        resolve(JSON.parse(JSON.stringify(this.spills)));
      }, 80);
    });
  }

  public getVessels(): Promise<Vessel[]> {
    this.stepKinematics();
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve(JSON.parse(JSON.stringify(this.vessels)));
      }, 100);
    });
  }

  public getSuspects(): Promise<Suspect[]> {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve(JSON.parse(JSON.stringify(this.suspects)));
      }, 90);
    });
  }

  public getAlerts(): Promise<OperationalAlert[]> {
    return new Promise((resolve) => {
      setTimeout(() => {
        resolve(JSON.parse(JSON.stringify(this.alerts)));
      }, 70);
    });
  }

  public addAlert(alert: Omit<OperationalAlert, 'id' | 'timestamp'>) {
    const newAlert: OperationalAlert = {
      ...alert,
      id: `ALT-${Math.floor(1000 + Math.random() * 9000)}`,
      timestamp: new Date().toISOString(),
    };
    this.alerts = [newAlert, ...this.alerts.slice(0, 49)];
    return newAlert;
  }
}

export const mockEngine = new MockEngine();
