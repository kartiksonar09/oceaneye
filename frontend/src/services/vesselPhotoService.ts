/**
 * Vessel Photo API Service
 * ========================
 * Provides a single `getVesselPhoto(mmsi, imo?, vesselType?)` function that is
 * fully swappable between photo providers by changing ACTIVE_PROVIDER below.
 *
 * Supported providers (add API key to .env to activate):
 *   - 'vesselFinder'  → VITE_VESSELFINDER_API_KEY
 *   - 'marineTraffic' → VITE_MARINETRAFFIC_API_KEY
 *   - 'fallback'      → Always returns null (uses local silhouette SVGs)
 *
 * Cache: localStorage with 24h TTL. Falls through to null on any error.
 */

export type PhotoResult =
  | { status: 'found'; url: string; credit: string }
  | { status: 'not_found' }
  | { status: 'error'; reason: string };

// ─────────────────────────────────────────────
// PROVIDER SELECTION  ← Change this to activate a provider
// ─────────────────────────────────────────────
type Provider = 'vesselFinder' | 'marineTraffic' | 'fallback';
const ACTIVE_PROVIDER: Provider = 'fallback'; // Change to 'vesselFinder' once key is provided

// ─────────────────────────────────────────────
// CACHE CONFIG
// ─────────────────────────────────────────────
const CACHE_PREFIX = 'oceaneye_photo_v1_';
const CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

interface CacheEntry {
  result: PhotoResult;
  expiresAt: number;
}

function readCache(mmsi: string): PhotoResult | null {
  try {
    const raw = localStorage.getItem(`${CACHE_PREFIX}${mmsi}`);
    if (!raw) return null;
    const entry: CacheEntry = JSON.parse(raw);
    if (Date.now() > entry.expiresAt) {
      localStorage.removeItem(`${CACHE_PREFIX}${mmsi}`);
      return null;
    }
    return entry.result;
  } catch {
    return null;
  }
}

function writeCache(mmsi: string, result: PhotoResult): void {
  try {
    const entry: CacheEntry = {
      result,
      expiresAt: Date.now() + CACHE_TTL_MS,
    };
    localStorage.setItem(`${CACHE_PREFIX}${mmsi}`, JSON.stringify(entry));
  } catch {
    // Storage quota exceeded — silently skip caching
  }
}

// ─────────────────────────────────────────────
// PROVIDER IMPLEMENTATIONS
// ─────────────────────────────────────────────

/**
 * VesselFinder Photo API
 * Docs: https://api.vesselfinder.com/docs
 * Endpoint: GET https://api.vesselfinder.com/vessels?userkey={KEY}&mmsi={MMSI}
 *
 * TO ACTIVATE:
 *   1. Add VITE_VESSELFINDER_API_KEY=your_key_here to frontend/.env
 *   2. Change ACTIVE_PROVIDER above to 'vesselFinder'
 */
async function fetchVesselFinderPhoto(mmsi: string): Promise<PhotoResult> {
  // ⬇️ INSERT YOUR API KEY HERE via .env variable
  const apiKey = import.meta.env.VITE_VESSELFINDER_API_KEY;

  if (!apiKey) {
    console.warn('[VesselPhoto] VesselFinder API key not set. Set VITE_VESSELFINDER_API_KEY in .env');
    return { status: 'not_found' };
  }

  try {
    // VesselFinder returns vessel data including photo_url in its vessel endpoint
    const response = await fetch(
      `https://api.vesselfinder.com/vessels?userkey=${apiKey}&mmsi=${mmsi}`,
      { signal: AbortSignal.timeout(6000) }
    );

    if (!response.ok) {
      return { status: 'error', reason: `HTTP ${response.status}` };
    }

    const data = await response.json();
    // VesselFinder nests photo under AIS.PHOTO
    const photoUrl = data?.AIS?.PHOTO;

    if (photoUrl && typeof photoUrl === 'string' && photoUrl.startsWith('http')) {
      return { status: 'found', url: photoUrl, credit: 'VesselFinder' };
    }

    return { status: 'not_found' };
  } catch (err) {
    const reason = err instanceof Error ? err.message : 'Network error';
    return { status: 'error', reason };
  }
}

/**
 * MarineTraffic Photo API  (Official API — NOT scraping)
 * Docs: https://www.marinetraffic.com/en/ais-api-services/
 * Endpoint: GET https://services.marinetraffic.com/api/exportvessel/{API_KEY}?v=8&mmsi={MMSI}&msgtype=extended
 *
 * TO ACTIVATE:
 *   1. Add VITE_MARINETRAFFIC_API_KEY=your_key_here to frontend/.env
 *   2. Change ACTIVE_PROVIDER above to 'marineTraffic'
 *
 * NOTE: MarineTraffic charges per API call. The photo is returned in the
 *       PHOTO field of the vessel record when using msgtype=extended.
 */
async function fetchMarineTrafficPhoto(mmsi: string): Promise<PhotoResult> {
  // ⬇️ INSERT YOUR API KEY HERE via .env variable
  const apiKey = import.meta.env.VITE_MARINETRAFFIC_API_KEY;

  if (!apiKey) {
    console.warn('[VesselPhoto] MarineTraffic API key not set. Set VITE_MARINETRAFFIC_API_KEY in .env');
    return { status: 'not_found' };
  }

  try {
    const response = await fetch(
      `https://services.marinetraffic.com/api/exportvessel/${apiKey}?v=8&mmsi=${mmsi}&msgtype=extended&protocol=jsono`,
      { signal: AbortSignal.timeout(8000) }
    );

    if (!response.ok) {
      return { status: 'error', reason: `HTTP ${response.status}` };
    }

    const data = await response.json();
    // MarineTraffic returns an array of vessel objects
    const vessel = Array.isArray(data) ? data[0] : null;
    const photoUrl = vessel?.PHOTO;

    if (photoUrl && typeof photoUrl === 'string' && photoUrl.startsWith('http')) {
      return { status: 'found', url: photoUrl, credit: 'MarineTraffic' };
    }

    return { status: 'not_found' };
  } catch (err) {
    const reason = err instanceof Error ? err.message : 'Network error';
    return { status: 'error', reason };
  }
}

// ─────────────────────────────────────────────
// PUBLIC API
// ─────────────────────────────────────────────

/**
 * Look up a vessel photo by MMSI.
 * Checks localStorage cache first (24h TTL).
 * Provider is swappable via ACTIVE_PROVIDER constant above.
 *
 * @param mmsi - Vessel MMSI string (9 digits)
 * @param _imo - Optional IMO, reserved for future provider fallback chain
 * @returns PhotoResult — { status: 'found', url, credit } | { status: 'not_found' } | { status: 'error' }
 */
export async function getVesselPhoto(mmsi: string, _imo?: string): Promise<PhotoResult> {
  // 1. Check in-memory + localStorage cache
  const cached = readCache(mmsi);
  if (cached) return cached;

  // 2. Dispatch to active provider
  let result: PhotoResult;

  switch (ACTIVE_PROVIDER) {
    case 'vesselFinder':
      result = await fetchVesselFinderPhoto(mmsi);
      break;
    case 'marineTraffic':
      result = await fetchMarineTrafficPhoto(mmsi);
      break;
    case 'fallback':
    default:
      result = { status: 'not_found' };
      break;
  }

  // 3. Cache result (we cache not_found too — avoids repeat calls for vessels without photos)
  writeCache(mmsi, result);
  return result;
}
