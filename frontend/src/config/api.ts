/**
 * Ocean Eye API Configuration
 * Supports one-line toggle between High-Fidelity Mock Mode and Live Backend API.
 */

const getInitialMockMode = (): boolean => {
  const stored = localStorage.getItem('oceaneye_use_mock');
  if (stored !== null) {
    return stored === 'true';
  }
  // If env var is explicitly provided, respect it; otherwise default to true for instant demo
  return import.meta.env.VITE_USE_MOCK !== 'false';
};

export const API_CONFIG = {
  // Base URL for backend API. When using Vite proxy, '/api' proxies to http://127.0.0.1:8000
  BASE_URL: import.meta.env.VITE_API_BASE_URL || '/api',
  
  // Dynamic mock mode (can be overridden at runtime or via env)
  DEFAULT_USE_MOCK: getInitialMockMode(),
  
  // Auth Headers: customize with Bearer token or custom secret as needed
  AUTH_HEADER_NAME: import.meta.env.VITE_AUTH_HEADER_NAME || 'Authorization',
  AUTH_TOKEN: import.meta.env.VITE_AUTH_TOKEN || '',
  
  // Polling Intervals in milliseconds
  POLL_INTERVAL_VESSELS_MS: 15_000, // 15s live AIS tracking simulation
  POLL_INTERVAL_SPILLS_MS: 60_000,  // 60s SAR pass detection refresh
  POLL_INTERVAL_SUSPECTS_MS: 60_000,// 60s attribution model refresh
};

// ─── CARTO API key ─────────────────────────────────────────────────────────
// Provided key is the hardcoded fallback so the app works without a .env reload.
const CARTO_API_KEY =
  (import.meta.env.VITE_CARTO_API_KEY as string | undefined) ||
  'cb1_3wp0_1_cee154ad870156318472e10f';

const cartoUrl = (style: string) =>
  `https://{s}.basemaps.cartocdn.com/${style}/{z}/{x}/{y}{r}.png?api_key=${CARTO_API_KEY}`;

export const MAP_CONFIG = {
  CARTO_DARK_URL:       import.meta.env.VITE_CARTO_DARK_URL     || cartoUrl('dark_all'),
  CARTO_POSITRON_URL:   import.meta.env.VITE_CARTO_POSITRON_URL || cartoUrl('light_all'),
  ESRI_SATELLITE_URL:   import.meta.env.VITE_ESRI_SATELLITE_URL || 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  OSM_STREET_URL:       import.meta.env.VITE_OSM_STREET_URL     || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  OPENSEAMAP_SEAMARK_URL: import.meta.env.VITE_OPENSEAMAP_URL   || 'https://tiles.openseamap.org/seamark/{z}/{x}/{y}.png',
};

export const setStoredMockMode = (useMock: boolean) => {
  localStorage.setItem('oceaneye_use_mock', String(useMock));
};

export const getStoredMockMode = (): boolean => {
  return getInitialMockMode();
};

