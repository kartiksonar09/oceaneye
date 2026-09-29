/**
 * VesselSilhouettes.tsx
 * ---------------------
 * Inline SVG silhouettes for each vessel type, used as fallbacks when no
 * photo is available. Pure SVG — no network cost, perfectly theme-matched.
 */
import React from 'react';

interface SilhouetteProps {
  className?: string;
}

export const TankerSilhouette: React.FC<SilhouetteProps> = ({ className }) => (
  <svg viewBox="0 0 280 100" xmlns="http://www.w3.org/2000/svg" className={className} aria-hidden>
    {/* Hull */}
    <path
      d="M 8 50 Q 8 28 28 26 L 240 24 Q 268 24 272 50 Q 268 76 240 76 L 28 74 Q 8 72 8 50 Z"
      fill="#1a2535" stroke="#2a3f55" strokeWidth="1.5"
    />
    {/* Bow */}
    <path d="M 240 24 L 272 50 L 240 76" fill="#223344" stroke="#2a3f55" strokeWidth="1" />
    {/* Cargo tanks (row of circles) */}
    {[60, 100, 140, 180].map((cx) => (
      <ellipse key={cx} cx={cx} cy="50" rx="16" ry="13" fill="#0e1a25" stroke="#2d4560" strokeWidth="1" />
    ))}
    {/* Bridge superstructure */}
    <rect x="18" y="35" width="28" height="30" rx="2" fill="#162030" stroke="#2d4560" strokeWidth="1" />
    <rect x="22" y="32" width="20" height="8" rx="1" fill="#0e1a25" stroke="#2d4560" strokeWidth="0.8" />
    {/* Funnel */}
    <rect x="24" y="27" width="8" height="6" rx="1" fill="#243040" />
    {/* Keel line */}
    <line x1="30" y1="50" x2="240" y2="50" stroke="#1e3046" strokeWidth="0.5" strokeDasharray="6,4" />
  </svg>
);

export const BulkCarrierSilhouette: React.FC<SilhouetteProps> = ({ className }) => (
  <svg viewBox="0 0 280 100" xmlns="http://www.w3.org/2000/svg" className={className} aria-hidden>
    {/* Hull */}
    <path
      d="M 8 50 Q 8 30 30 28 L 238 27 Q 266 27 272 50 Q 266 73 238 73 L 30 72 Q 8 70 8 50 Z"
      fill="#1a2535" stroke="#2a3f55" strokeWidth="1.5"
    />
    {/* Bow */}
    <path d="M 238 27 L 272 50 L 238 73" fill="#223344" stroke="#2a3f55" strokeWidth="1" />
    {/* Cargo holds (trapezoids) */}
    {[60, 110, 160, 205].map((x) => (
      <rect key={x} x={x} y="33" width="36" height="34" rx="1" fill="#0e1a25" stroke="#2d4560" strokeWidth="1" />
    ))}
    {/* Hatch covers */}
    {[60, 110, 160, 205].map((x) => (
      <rect key={`h-${x}`} x={x + 3} y="36" width="30" height="8" rx="1" fill="#162030" stroke="#2a4060" strokeWidth="0.8" />
    ))}
    {/* Bridge */}
    <rect x="14" y="34" width="34" height="32" rx="2" fill="#162030" stroke="#2d4560" strokeWidth="1" />
    <rect x="18" y="30" width="26" height="8" rx="1" fill="#0e1a25" stroke="#2d4560" strokeWidth="0.8" />
    {/* Funnel */}
    <rect x="22" y="23" width="10" height="8" rx="1" fill="#243040" />
  </svg>
);

export const ContainerSilhouette: React.FC<SilhouetteProps> = ({ className }) => (
  <svg viewBox="0 0 280 100" xmlns="http://www.w3.org/2000/svg" className={className} aria-hidden>
    {/* Hull */}
    <path
      d="M 8 50 Q 8 30 28 28 L 238 27 Q 264 27 272 50 Q 264 73 238 73 L 28 72 Q 8 70 8 50 Z"
      fill="#1a2535" stroke="#2a3f55" strokeWidth="1.5"
    />
    {/* Bow */}
    <path d="M 238 27 L 272 50 L 238 73" fill="#223344" stroke="#2a3f55" strokeWidth="1" />
    {/* Container stacks */}
    {[50, 80, 110, 140, 170, 200, 228].map((x, i) => (
      <g key={i}>
        <rect x={x} y="36" width="22" height="10" rx="0.5" fill="#0e1a25" stroke="#2d4560" strokeWidth="0.8" />
        <rect x={x} y="48" width="22" height="10" rx="0.5" fill="#162030" stroke="#2d4560" strokeWidth="0.8" />
        <rect x={x} y="60" width="22" height="8" rx="0.5" fill="#0e1a25" stroke="#2d4560" strokeWidth="0.8" />
      </g>
    ))}
    {/* Bridge */}
    <rect x="12" y="30" width="30" height="40" rx="2" fill="#162030" stroke="#2d4560" strokeWidth="1" />
    <rect x="15" y="26" width="24" height="10" rx="1" fill="#0e1a25" stroke="#2d4560" strokeWidth="0.8" />
  </svg>
);

export const FishingVesselSilhouette: React.FC<SilhouetteProps> = ({ className }) => (
  <svg viewBox="0 0 280 100" xmlns="http://www.w3.org/2000/svg" className={className} aria-hidden>
    {/* Hull — shorter and wider */}
    <path
      d="M 50 50 Q 50 28 72 27 L 200 26 Q 240 26 248 50 Q 240 74 200 74 L 72 73 Q 50 72 50 50 Z"
      fill="#1a2535" stroke="#2a3f55" strokeWidth="1.5"
    />
    {/* Bow */}
    <path d="M 200 26 L 248 50 L 200 74" fill="#223344" stroke="#2a3f55" strokeWidth="1" />
    {/* Bridge & wheelhouse */}
    <rect x="58" y="30" width="50" height="40" rx="3" fill="#162030" stroke="#2d4560" strokeWidth="1" />
    <rect x="63" y="25" width="40" height="10" rx="2" fill="#0e1a25" stroke="#2d4560" strokeWidth="0.8" />
    {/* Fishing gear / trawl equipment */}
    <line x1="120" y1="28" x2="180" y2="28" stroke="#2d4560" strokeWidth="1.5" />
    <line x1="150" y1="20" x2="150" y2="60" stroke="#2d4560" strokeWidth="1.5" />
    {/* Mast */}
    <line x1="80" y1="10" x2="80" y2="30" stroke="#2a3f55" strokeWidth="2" />
    <line x1="60" y1="18" x2="100" y2="18" stroke="#2a3f55" strokeWidth="1" />
  </svg>
);

export const GenericVesselSilhouette: React.FC<SilhouetteProps> = ({ className }) => (
  <svg viewBox="0 0 280 100" xmlns="http://www.w3.org/2000/svg" className={className} aria-hidden>
    {/* Generic ship hull */}
    <path
      d="M 20 50 Q 20 30 40 28 L 230 27 Q 258 27 264 50 Q 258 73 230 73 L 40 72 Q 20 70 20 50 Z"
      fill="#1a2535" stroke="#2a3f55" strokeWidth="1.5"
    />
    {/* Bow */}
    <path d="M 230 27 L 264 50 L 230 73" fill="#223344" stroke="#2a3f55" strokeWidth="1" />
    {/* Bridge */}
    <rect x="28" y="33" width="40" height="34" rx="2" fill="#162030" stroke="#2d4560" strokeWidth="1" />
    {/* Deck fixtures */}
    <rect x="85" y="38" width="120" height="24" rx="1" fill="#0e1a25" stroke="#2d4560" strokeWidth="0.8" />
    {/* Mast / antennae */}
    <line x1="45" y1="12" x2="45" y2="33" stroke="#2a3f55" strokeWidth="2" />
    <line x1="30" y1="20" x2="60" y2="20" stroke="#2a3f55" strokeWidth="1" />
  </svg>
);

// ─── Type map ────────────────────────────────────────────────────────────────
export type VesselSilhouetteType = 'tanker' | 'bulk_carrier' | 'container' | 'fishing' | 'unknown';

export function resolveVesselType(vesselType: string): VesselSilhouetteType {
  const vt = vesselType.toLowerCase();
  if (vt.includes('tanker') || vt.includes('chemical') || vt.includes('lpg') || vt.includes('lng')) return 'tanker';
  if (vt.includes('bulk')) return 'bulk_carrier';
  if (vt.includes('container')) return 'container';
  if (vt.includes('fishing') || vt.includes('trawl')) return 'fishing';
  return 'unknown';
}

interface VesselSilhouetteProps {
  vesselType: string;
  className?: string;
}

export const VesselSilhouette: React.FC<VesselSilhouetteProps> = ({ vesselType, className }) => {
  const type = resolveVesselType(vesselType);
  const shared = className ?? 'w-full h-full';
  switch (type) {
    case 'tanker':       return <TankerSilhouette className={shared} />;
    case 'bulk_carrier': return <BulkCarrierSilhouette className={shared} />;
    case 'container':    return <ContainerSilhouette className={shared} />;
    case 'fishing':      return <FishingVesselSilhouette className={shared} />;
    default:             return <GenericVesselSilhouette className={shared} />;
  }
};
