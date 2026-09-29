/**
 * VesselPhotoPanel.tsx
 * --------------------
 * Vessel photo display with 4 states:
 *   1. Loading  → animated skeleton + blur-in
 *   2. Found    → real photo with expand modal + credit badge
 *   3. Not found → type-accurate SVG silhouette + "NO PHOTO ON RECORD" label
 *   4. Error     → same silhouette + subtle error indicator
 *
 * Never shows a broken-image browser icon.
 */
import React, { useState } from 'react';
import { Maximize2, Camera, WifiOff } from 'lucide-react';
import { useVesselPhoto } from '../../hooks/useVesselPhoto';
import { VesselSilhouette } from './VesselSilhouettes';

interface VesselPhotoPanelProps {
  mmsi: string;
  imo?: string;
  vesselName: string;
  vesselType: string;
  isFlagged: boolean;
}

export const VesselPhotoPanel: React.FC<VesselPhotoPanelProps> = ({
  mmsi,
  imo,
  vesselName,
  vesselType,
  isFlagged,
}) => {
  const { photoResult, isLoading } = useVesselPhoto(mmsi, imo);
  const [showModal, setShowModal] = useState(false);
  const [imgFailed, setImgFailed] = useState(false);

  // Reset imgFailed when mmsi changes
  React.useEffect(() => {
    setImgFailed(false);
  }, [mmsi]);

  const hasRealPhoto =
    !isLoading &&
    !imgFailed &&
    photoResult?.status === 'found' &&
    photoResult.url;

  return (
    <>
      {/* ── Main Panel ── */}
      <div className="relative rounded-xs overflow-hidden border border-radar-700/80 bg-radar-950 group">
        <div className="relative aspect-video w-full overflow-hidden">

          {/* ── STATE 1: Loading skeleton ── */}
          {isLoading && (
            <div className="absolute inset-0 bg-radar-900 flex flex-col items-center justify-center gap-2 animate-pulse">
              <div className="w-10 h-10 rounded-full bg-radar-800" />
              <div className="h-2 w-24 bg-radar-800 rounded-full" />
              <div className="h-1.5 w-16 bg-radar-850 rounded-full mt-1" />
              <span className="text-[9px] font-mono text-radar-600 uppercase tracking-widest mt-2">
                Fetching Archive...
              </span>
            </div>
          )}

          {/* ── STATE 2: Real photo found ── */}
          {hasRealPhoto && (
            <>
              <img
                src={(photoResult as { status: 'found'; url: string; credit: string }).url}
                alt={`${vesselName} vessel photo`}
                onError={() => setImgFailed(true)}
                className="w-full h-full object-cover transition-all duration-700 group-hover:scale-105"
                style={{ opacity: isLoading ? 0 : 1 }}
              />
              <div className="absolute inset-0 bg-gradient-to-t from-radar-950/90 via-transparent to-black/20 pointer-events-none" />

              {/* Photo credit badge */}
              <div className="absolute top-2 left-2 flex items-center gap-1 px-1.5 py-0.5 bg-radar-950/80 border border-radar-700/70 rounded-xs backdrop-blur-sm">
                <Camera className="w-2.5 h-2.5 text-radar-400" />
                <span className="text-[9px] font-mono text-radar-400 uppercase tracking-wider">
                  {(photoResult as { status: 'found'; url: string; credit: string }).credit}
                </span>
              </div>

              {/* Enlarge button */}
              <button
                onClick={() => setShowModal(true)}
                className="absolute top-2 right-2 p-1.5 rounded-xs bg-radar-950/80 hover:bg-radar-900 text-radar-300 hover:text-white border border-radar-700/80 transition-colors"
                title="Expand Photo"
                aria-label="Expand vessel photo"
              >
                <Maximize2 className="w-3.5 h-3.5" />
              </button>
            </>
          )}

          {/* ── STATES 3 & 4: No photo / Error — silhouette fallback ── */}
          {!isLoading && (!hasRealPhoto) && (
            <div className="absolute inset-0 flex flex-col items-center justify-center bg-radar-900 select-none">
              {/* Subtle grid background */}
              <div
                className="absolute inset-0 opacity-20"
                style={{
                  backgroundImage: 'linear-gradient(#1e3048 1px, transparent 1px), linear-gradient(90deg, #1e3048 1px, transparent 1px)',
                  backgroundSize: '20px 20px',
                }}
              />

              {/* SVG silhouette */}
              <div className="relative w-[85%] max-w-xs opacity-25">
                <VesselSilhouette vesselType={vesselType} />
              </div>

              {/* Error sub-label */}
              {photoResult?.status === 'error' && (
                <div className="absolute top-2 left-2 flex items-center gap-1 px-1.5 py-0.5 bg-radar-950/70 border border-radar-700/50 rounded-xs">
                  <WifiOff className="w-2.5 h-2.5 text-radar-600" />
                  <span className="text-[9px] font-mono text-radar-600">FETCH ERROR</span>
                </div>
              )}

              {/* NO PHOTO ON RECORD label */}
              <div className="absolute bottom-3 left-0 right-0 flex flex-col items-center gap-1 pointer-events-none">
                <div className="h-px w-16 bg-radar-700/60 mb-1" />
                <span className="text-[9px] font-mono tracking-[0.2em] uppercase text-radar-600">
                  No Photo On Record
                </span>
                <span className="text-[8px] font-mono text-radar-700 capitalize">
                  {vesselType}
                </span>
              </div>
            </div>
          )}

          {/* Overlay badges (vessel type + status) — shown when photo exists */}
          {hasRealPhoto && (
            <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between text-[10px]">
              <span className="px-1.5 py-0.5 rounded-xs bg-radar-900/90 border border-radar-700 text-radar-200 font-bold backdrop-blur-xs font-mono">
                {vesselType}
              </span>
              <span className={`px-1.5 py-0.5 rounded-xs font-bold uppercase backdrop-blur-xs border font-mono ${
                isFlagged
                  ? 'bg-suspect-crimson/80 border-suspect-crimson text-white'
                  : 'bg-emerald-950/80 border-emerald-600 text-emerald-300'
              }`}>
                {isFlagged ? 'ATTRIBUTION SUSPECT' : 'NORMAL TRANSIT'}
              </span>
            </div>
          )}

          {/* For silhouette state — show status badge at top right */}
          {!isLoading && !hasRealPhoto && (
            <div className="absolute top-2 right-2">
              <span className={`px-1.5 py-0.5 rounded-xs text-[9px] font-bold uppercase border font-mono ${
                isFlagged
                  ? 'bg-suspect-crimson/80 border-suspect-crimson text-white'
                  : 'bg-emerald-950/70 border-emerald-700/50 text-emerald-500'
              }`}>
                {isFlagged ? 'SUSPECT' : 'CLEAR'}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* ── Lightbox Modal (real photo only) ── */}
      {showModal && hasRealPhoto && (
        <div
          onClick={() => setShowModal(false)}
          className="fixed inset-0 z-[200] bg-black/90 backdrop-blur-md flex items-center justify-center p-4 cursor-zoom-out"
          role="dialog"
          aria-modal="true"
          aria-label={`Full size photo of ${vesselName}`}
        >
          <div
            className="max-w-5xl max-h-[88vh] bg-radar-900 border border-radar-700 rounded-xs overflow-hidden shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <img
              src={(photoResult as { status: 'found'; url: string; credit: string }).url}
              alt={`${vesselName} full resolution`}
              className="max-w-full max-h-[78vh] object-contain"
            />
            <div className="px-4 py-2.5 flex items-center justify-between font-mono text-xs border-t border-radar-800">
              <div className="text-radar-300">
                <strong className="text-radar-100">{vesselName}</strong>
                <span className="text-radar-500 mx-2">·</span>
                <span>MMSI: {mmsi}</span>
                {imo && <><span className="text-radar-500 mx-2">·</span><span>IMO: {imo}</span></>}
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[9px] text-radar-600 uppercase tracking-wider">
                  Photo: {(photoResult as { status: 'found'; url: string; credit: string }).credit}
                </span>
                <span className="text-radar-600">·</span>
                <span className="text-[9px] text-radar-600">Click outside to close</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
