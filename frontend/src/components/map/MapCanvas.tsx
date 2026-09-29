import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { 
  Layers, 
  Crosshair, 
  Maximize2, 
  Compass, 
  Eye, 
  EyeOff,
  Ship,
  Flame,
  Radio,
  Map as MapIcon,
  Globe,
  Anchor
} from 'lucide-react';
import { BasemapType, RegionZone, Spill, Suspect, Vessel } from '../../types/api';
import { escapeHtml } from '../../utils/core';
import { useTheme } from '../../context/ThemeContext';
import { MAP_CONFIG } from '../../config/api';
import { getVesselTrajectory, TrajectoryPoint } from '../../utils/vesselTrajectory';

interface MapCanvasProps {
  currentRegion: RegionZone;
  spills: Spill[];
  vessels: Vessel[];
  suspects: Suspect[];
  selectedSpill: Spill | null;
  selectedVessel: Vessel | null;
  onSelectSpill: (spill: Spill) => void;
  onSelectVessel: (vessel: Vessel) => void;
  scrubbedPoint?: TrajectoryPoint | null;
}

export const MapCanvas: React.FC<MapCanvasProps> = React.memo(({
  currentRegion,
  spills,
  vessels,
  suspects,
  selectedSpill,
  selectedVessel,
  onSelectSpill,
  onSelectVessel,
  scrubbedPoint,
}) => {
  const { theme } = useTheme();
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);

  // Basemap tile layer ref
  const baseTileLayerRef = useRef<L.TileLayer | null>(null);
  const seamarksLayerRef = useRef<L.TileLayer | null>(null);

  const spillsLayerRef = useRef<L.LayerGroup>(L.layerGroup());
  const vesselsLayerRef = useRef<L.LayerGroup>(L.layerGroup());
  const vectorsLayerRef = useRef<L.LayerGroup>(L.layerGroup());
  const historyTrackLayerRef = useRef<L.LayerGroup>(L.layerGroup());
  const vesselMarkersRef = useRef<Map<string, L.Marker>>(new Map());

  // Cursor coordinates readout
  const [cursorCoords, setCursorCoords] = useState<{ lat: number; lng: number } | null>(null);

  // Layer visibility & basemap toggles
  const [basemap, setBasemap] = useState<BasemapType>('dark');
  const [showSeamarks, setShowSeamarks] = useState<boolean>(false);
  const [showSpills, setShowSpills] = useState<boolean>(true);
  const [showVessels, setShowVessels] = useState<boolean>(true);
  const [showVectors, setShowVectors] = useState<boolean>(true);
  const [suspectsOnly, setSuspectsOnly] = useState<boolean>(false);

  // Basemap URLs loaded from central MAP_CONFIG
  const BASEMAP_URLS: Record<BasemapType | 'positron', string> = {
    dark:      MAP_CONFIG.CARTO_DARK_URL,
    positron:  MAP_CONFIG.CARTO_POSITRON_URL,
    satellite: MAP_CONFIG.ESRI_SATELLITE_URL,
    street:    MAP_CONFIG.OSM_STREET_URL,
  };

  // Instantiate clean tile layers with placeholder/error watermark suppressed
  const createTileLayer = (url: string, subdomains: string, maxZoom = 20) => {
    const layer = L.tileLayer(url, {
      subdomains,
      maxZoom,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      errorTileUrl: 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7',
    });
    // Immediately suppress any broken-tile artifact or watermark if network packet drops
    layer.on('tileerror', (e: L.TileEvent) => {
      if (e.tile) {
        e.tile.style.visibility = 'hidden';
        e.tile.style.opacity = '0';
      }
    });
    return layer;
  };

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    const map = L.map(mapContainerRef.current, {
      center: currentRegion.center,
      zoom: currentRegion.zoom,
      zoomControl: false,
      attributionControl: false,
    });

    // Initial Base Tile Layer: CARTO Dark Matter (authenticated via CARTO_API_KEY)
    const baseTile = createTileLayer(BASEMAP_URLS.dark, 'abcd', 20).addTo(map);
    baseTileLayerRef.current = baseTile;

    // CARTO attribution (required by ToS)
    L.control.attribution({ position: 'bottomright', prefix: false })
      .addAttribution('&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>')
      .addTo(map);

    // Attach operational layer groups
    spillsLayerRef.current.addTo(map);
    vesselsLayerRef.current.addTo(map);
    vectorsLayerRef.current.addTo(map);
    historyTrackLayerRef.current.addTo(map);

    // Track cursor coordinates with basic throttle
    let lastUpdate = 0;
    map.on('mousemove', (e: L.LeafletMouseEvent) => {
      const now = Date.now();
      if (now - lastUpdate > 50) {
        lastUpdate = now;
        setCursorCoords({
          lat: Number(e.latlng.lat.toFixed(5)),
          lng: Number(e.latlng.lng.toFixed(5)),
        });
      }
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Switch basemap when global theme changes (dark→dark_all, light→positron)
  useEffect(() => {
    if (!mapRef.current || !baseTileLayerRef.current) return;
    // Only auto-switch if user hasn't manually picked satellite/street
    if (basemap === 'dark' || basemap === 'positron' as BasemapType) {
      const nextBasemap: BasemapType = theme === 'light' ? 'positron' as BasemapType : 'dark';
      if (basemap !== nextBasemap) {
        setBasemap(nextBasemap);
      }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [theme]);

  // Update Basemap Layer when basemap state changes
  useEffect(() => {
    if (!mapRef.current || !baseTileLayerRef.current) return;

    const map = mapRef.current;
    map.removeLayer(baseTileLayerRef.current);

    const subdomains = (basemap === 'dark' || (basemap as string) === 'positron') ? 'abcd' : basemap === 'street' ? 'abc' : '';
    const newBase = createTileLayer(BASEMAP_URLS[basemap], subdomains, 20).addTo(map);

    // Keep basemap at the back
    newBase.bringToBack();
    baseTileLayerRef.current = newBase;
  }, [basemap]);

  // Toggle Nautical OpenSeaMap Seamarks Layer
  useEffect(() => {
    if (!mapRef.current) return;
    const map = mapRef.current;

    if (showSeamarks) {
      if (!seamarksLayerRef.current) {
        seamarksLayerRef.current = L.tileLayer(MAP_CONFIG.OPENSEAMAP_SEAMARK_URL, {
          maxZoom: 18,
          opacity: 0.85,
          errorTileUrl: 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7',
        });
        seamarksLayerRef.current.on('tileerror', (e: L.TileEvent) => {
          if (e.tile) {
            e.tile.style.visibility = 'hidden';
            e.tile.style.opacity = '0';
          }
        });
      }
      seamarksLayerRef.current.addTo(map);
    } else if (seamarksLayerRef.current && map.hasLayer(seamarksLayerRef.current)) {
      map.removeLayer(seamarksLayerRef.current);
    }
  }, [showSeamarks]);

  // Update map center on region change
  useEffect(() => {
    if (!mapRef.current) return;
    mapRef.current.flyTo(currentRegion.center, currentRegion.zoom, {
      duration: 1.2,
      easeLinearity: 0.25,
    });
  }, [currentRegion]);

  // Center on selected spill
  useEffect(() => {
    if (!mapRef.current || !selectedSpill) return;
    mapRef.current.flyTo([selectedSpill.centroid.lat, selectedSpill.centroid.lng], 13, {
      duration: 1.0,
    });
  }, [selectedSpill]);

  // Center on selected vessel
  useEffect(() => {
    if (!mapRef.current || !selectedVessel) return;
    mapRef.current.flyTo([selectedVessel.lat, selectedVessel.lng], 13, {
      duration: 1.0,
    });
  }, [selectedVessel]);

  // Build Suspect Quick Map
  const suspectMmsiMap = new Map<string, Suspect>();
  suspects.forEach((s) => suspectMmsiMap.set(s.vessel_mmsi, s));

  // Render Spills Layer
  useEffect(() => {
    const layer = spillsLayerRef.current;
    layer.clearLayers();

    if (!showSpills) return;

    spills.forEach((spill) => {
      const isSelected = selectedSpill?.id === spill.id;
      const isActive = spill.status === 'active';

      // Polygon boundary
      const polygon = L.polygon(spill.polygon, {
        color: isSelected ? '#FBBF24' : '#F59E0B',
        weight: isSelected ? 3 : 2,
        fillColor: '#F59E0B',
        fillOpacity: isSelected ? 0.35 : 0.22,
        dashArray: isActive ? undefined : '5, 5',
        interactive: true,
      });

      polygon.on('click', () => {
        onSelectSpill(spill);
      });

      // Centroid Marker with Pulsing beacon if active
      const centroidIcon = L.divIcon({
        className: 'custom-spill-centroid',
        html: `
          <div role="button" tabindex="0" aria-label="Spill centroid ${escapeHtml(spill.id)}" class="relative flex items-center justify-center cursor-pointer" style="width: 28px; height: 28px;">
            ${
              isActive 
                ? '<div class="absolute w-7 h-7 rounded-full border border-spill-amber/70 radar-beacon pointer-events-none"></div>'
                : ''
            }
            <div class="w-3.5 h-3.5 rounded-full ${isSelected ? 'bg-amber-400 ring-2 ring-white' : 'bg-spill-amber'} border border-radar-950 flex items-center justify-center shadow-lg transition-transform hover:scale-125">
              <div class="w-1 h-1 rounded-full bg-radar-950"></div>
            </div>
          </div>
        `,
        iconSize: [28, 28],
        iconAnchor: [14, 14],
      });

      const marker = L.marker([spill.centroid.lat, spill.centroid.lng], {
        icon: centroidIcon,
      });

      marker.on('click', () => {
        onSelectSpill(spill);
      });

      marker.bindTooltip(
        `<div class="font-mono text-xs">
          <div class="font-bold text-spill-amber flex items-center gap-1">
            <span>${escapeHtml(spill.id)}</span>
            <span class="text-[9px] px-1 py-0.2 bg-radar-900 border border-radar-700 uppercase">${escapeHtml(spill.status)}</span>
          </div>
          <div class="text-radar-300 mt-0.5">${spill.area_km2.toFixed(1)} km² // Conf: ${(spill.confidence * 100).toFixed(1)}%</div>
        </div>`,
        { direction: 'top', offset: [0, -10], opacity: 0.95 }
      );

      layer.addLayer(polygon);
      layer.addLayer(marker);
    });
  }, [spills, selectedSpill, showSpills, onSelectSpill]);

  // Render Vessels Layer
  useEffect(() => {
    const layer = vesselsLayerRef.current;
    if (!showVessels) {
      layer.clearLayers();
      vesselMarkersRef.current.clear();
      return;
    }

    const currentMmsis = new Set<string>();

    vessels.forEach((vessel) => {
      const suspect = suspectMmsiMap.get(vessel.mmsi);
      const isSuspect = Boolean(suspect);
      const isSelected = selectedVessel?.mmsi === vessel.mmsi;

      if (suspectsOnly && !isSuspect) return;

      currentMmsis.add(vessel.mmsi);

      const markerHtml = `
        <div role="button" tabindex="0" aria-label="Vessel ${escapeHtml(vessel.name)} MMSI ${escapeHtml(vessel.mmsi)}" class="vessel-icon-container relative flex items-center justify-center cursor-pointer" style="width: 34px; height: 34px;">
          ${
            isSuspect
              ? `<div class="absolute w-8 h-8 rounded-full border border-suspect-crimson/80 animate-ping pointer-events-none" style="animation-duration: 2.2s;"></div>
                 <div class="absolute w-7 h-7 rounded-full border border-suspect-crimson bg-suspect-crimson/20"></div>`
              : ''
          }
          <div 
            style="transform: rotate(${vessel.heading}deg);" 
            class="transition-transform duration-300 flex items-center justify-center"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path 
                d="M12 2L20 20L12 16L4 20L12 2Z" 
                fill="${isSuspect ? '#EF4444' : isSelected ? '#38BDF8' : '#14B8A6'}" 
                stroke="${isSelected ? '#FFFFFF' : isSuspect ? '#991B1B' : '#042F2E'}" 
                stroke-width="1.8" 
                stroke-linejoin="round"
              />
            </svg>
          </div>
        </div>
      `;

      const icon = L.divIcon({
        className: 'custom-vessel-marker',
        html: markerHtml,
        iconSize: [34, 34],
        iconAnchor: [17, 17],
      });

      const photoThumbnail = vessel.photo_url || `/ships/${vessel.mmsi}.jpg`;
      const gapBadge = vessel.ais_gap_minutes 
        ? `<div class="mt-1 px-1.5 py-0.5 rounded-xs bg-amber-950 border border-amber-600/60 text-amber-300 text-[10px] font-bold">
            ⚠ AIS SIGNAL GAP: ${vessel.ais_gap_minutes} MIN DARK
           </div>` 
        : '';

      const tooltipHtml = `<div class="font-mono text-xs max-w-xs">
          <div class="flex items-center gap-2 mb-1">
            <img src="${escapeHtml(photoThumbnail)}" onerror="this.style.display='none'" class="w-12 h-8 object-cover rounded-xs border border-radar-700" alt="${escapeHtml(vessel.name)}" />
            <div>
              <div class="font-bold flex items-center gap-1 ${isSuspect ? 'text-suspect-crimson' : 'text-vessel-teal'}">
                <span>${escapeHtml(vessel.name)}</span>
              </div>
              <div class="text-[9px] text-radar-400">MMSI: ${escapeHtml(vessel.mmsi)} ${vessel.flag ? `• ${escapeHtml(vessel.flag)}` : ''}</div>
            </div>
          </div>
          <div class="text-radar-300 text-[11px] border-t border-radar-750 pt-1">
            ${escapeHtml(vessel.vessel_type)} • ${vessel.speed_knots}kt @ ${vessel.heading}°
          </div>
          ${gapBadge}
          ${
            isSuspect && suspect
              ? `<div class="mt-1 text-[10px] text-amber-300 font-bold border-t border-radar-750 pt-0.5">
                  SUSPICION SCORE: ${(suspect.suspicion_score * 100).toFixed(1)}%
                </div>`
              : ''
          }
          <div class="text-[9px] text-radar-500 mt-1 italic">Click ship to view full particulars &amp; photo</div>
        </div>`;

      let marker = vesselMarkersRef.current.get(vessel.mmsi);
      
      if (marker) {
        marker.setLatLng([vessel.lat, vessel.lng]);
        marker.setIcon(icon);
        marker.setTooltipContent(tooltipHtml);
      } else {
        marker = L.marker([vessel.lat, vessel.lng], { icon });
        marker.on('click', () => onSelectVessel(vessel));
        marker.bindTooltip(tooltipHtml, { direction: 'right', offset: [16, 0], opacity: 0.98 });
        layer.addLayer(marker);
        vesselMarkersRef.current.set(vessel.mmsi, marker);
      }
    });

    // Remove stale markers
    for (const [mmsi, marker] of vesselMarkersRef.current.entries()) {
      if (!currentMmsis.has(mmsi)) {
        layer.removeLayer(marker);
        vesselMarkersRef.current.delete(mmsi);
      }
    }
  }, [vessels, suspects, selectedVessel, showVessels, suspectsOnly, onSelectVessel]);

  // Render Suspect Attribution Vectors (dashed connecting line to linked spill)
  useEffect(() => {
    const layer = vectorsLayerRef.current;
    layer.clearLayers();

    if (!showVectors || !showSpills || !showVessels) return;

    suspects.forEach((suspect) => {
      const vessel = vessels.find((v) => v.mmsi === suspect.vessel_mmsi);
      const spill = spills.find((s) => s.id === suspect.spill_id);

      if (!vessel || !spill) return;

      const polyline = L.polyline(
        [
          [vessel.lat, vessel.lng],
          [spill.centroid.lat, spill.centroid.lng],
        ],
        {
          color: '#EF4444',
          weight: 1.8,
          dashArray: '6, 6',
          className: 'animated-suspect-vector',
        }
      );

      polyline.bindTooltip(
        `<div class="font-mono text-[11px] text-suspect-crimson">
          VECTOR: ${escapeHtml(vessel.name)} ➔ ${escapeHtml(spill.id)}
          <div class="text-radar-300 text-[10px]">Attribution Score: ${(suspect.suspicion_score * 100).toFixed(1)}%</div>
        </div>`,
        { sticky: true }
      );

      layer.addLayer(polyline);
    });
  }, [suspects, vessels, spills, showVectors, showSpills, showVessels]);

  // Render Reconstructed Historical Trajectory & Scrubbed Fix Pin
  useEffect(() => {
    const layer = historyTrackLayerRef.current;
    layer.clearLayers();

    if (!selectedVessel) return;

    const trajectory = getVesselTrajectory(selectedVessel, 24, 15);
    const latlngs: [number, number][] = trajectory.map((pt) => [pt.lat, pt.lng]);
    latlngs.push([selectedVessel.lat, selectedVessel.lng]);

    // Dashed historical trajectory polyline
    const trackLine = L.polyline(latlngs, {
      color: '#0D9488',
      weight: 2,
      dashArray: '4, 4',
      opacity: 0.75,
    });
    layer.addLayer(trackLine);

    // If scrubbed to a historical point, render historical position pin
    if (scrubbedPoint) {
      const scrubIcon = L.divIcon({
        className: 'custom-scrub-pin',
        html: `
          <div class="relative flex items-center justify-center cursor-pointer" style="width: 32px; height: 32px;">
            <div class="absolute w-8 h-8 rounded-full border-2 border-amber-400 animate-ping"></div>
            <div class="w-6 h-6 rounded-full bg-amber-500/30 border-2 border-amber-400 flex items-center justify-center shadow-lg">
              <div style="transform: rotate(${scrubbedPoint.heading}deg);">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="#FBBF24">
                  <path d="M12 2L20 20L12 16L4 20L12 2Z" />
                </svg>
              </div>
            </div>
          </div>
        `,
        iconSize: [32, 32],
        iconAnchor: [16, 16],
      });

      const scrubMarker = L.marker([scrubbedPoint.lat, scrubbedPoint.lng], { icon: scrubIcon });
      scrubMarker.bindTooltip(
        `<div class="font-mono text-xs">
          <div class="font-bold text-amber-400">HISTORICAL FIX (-${scrubbedPoint.minutesAgo}m)</div>
          <div class="text-[10px] text-radar-200">${scrubbedPoint.speed_knots}kt @ ${scrubbedPoint.heading}° Course</div>
          ${scrubbedPoint.inGap ? '<div class="text-red-400 font-bold text-[9px] mt-0.5">⚠ AIS SIGNAL GAP INTERVAL</div>' : ''}
        </div>`,
        { permanent: true, direction: 'top', offset: [0, -10], opacity: 0.95 }
      );
      layer.addLayer(scrubMarker);
    }
  }, [selectedVessel, scrubbedPoint]);

  const handleResetZoom = () => {
    if (!mapRef.current) return;
    mapRef.current.flyTo(currentRegion.center, currentRegion.zoom, { duration: 0.8 });
  };

  return (
    <div className="relative w-full h-full bg-radar-950 overflow-hidden">
      {/* Primary Leaflet Canvas */}
      <div ref={mapContainerRef} className="w-full h-full map-crosshair z-0" />

      {/* Floating Tactical Layer Controls (Top Right) */}
      <div className="absolute top-3 right-3 z-10 flex flex-col gap-1.5 bg-radar-900/95 border border-radar-700/90 rounded-xs p-2 shadow-2xl backdrop-blur-sm text-xs font-mono select-none">
        {/* Basemap Selection Tabs */}
        <div className="flex items-center gap-1.5 text-radar-400 text-[10px] tracking-wider uppercase border-b border-radar-700/60 pb-1 mb-0.5">
          <Globe className="w-3 h-3 text-spill-amber" />
          <span>BASEMAP LAYER</span>
        </div>

        <div className="grid grid-cols-3 gap-1 mb-1">
          {(['dark', 'satellite', 'street'] as const).map((b) => (
            <button
              key={b}
              onClick={() => setBasemap(b)}
              className={`px-1.5 py-1 rounded-xs border text-[10px] font-bold uppercase transition-colors ${
                basemap === b
                  ? 'bg-radar-750 text-spill-amber border-spill-amber/60'
                  : 'bg-radar-850 text-radar-400 border-radar-750 hover:text-radar-200'
              }`}
            >
              {b === 'dark' ? 'CARTO DARK' : b === 'satellite' ? 'SAT' : 'CHART'}
            </button>
          ))}
        </div>

        {/* Marine Seamarks Overlay */}
        <button
          onClick={() => setShowSeamarks(!showSeamarks)}
          className={`flex items-center justify-between gap-3 px-2 py-1 rounded-xs border text-[10px] transition-colors ${
            showSeamarks 
              ? 'bg-sky-950/80 text-sky-300 border-sky-600/70 font-bold' 
              : 'bg-radar-850 text-radar-400 border-radar-750'
          }`}
        >
          <div className="flex items-center gap-1.5">
            <Anchor className="w-3 h-3 text-sky-400" />
            <span>NAUTICAL SEAMARKS</span>
          </div>
          <span className="text-[9px]">{showSeamarks ? 'ON' : 'OFF'}</span>
        </button>

        {/* Layer Visibility Section */}
        <div className="flex items-center gap-1.5 text-radar-400 text-[10px] tracking-wider uppercase border-t border-radar-700/60 pt-1 mt-0.5">
          <Layers className="w-3 h-3 text-vessel-teal" />
          <span>TACTICAL OVERLAYS</span>
        </div>

        {/* Spills Layer Toggle */}
        <button
          onClick={() => setShowSpills(!showSpills)}
          className={`flex items-center justify-between gap-3 px-2 py-1 rounded-xs border text-[11px] transition-colors ${
            showSpills 
              ? 'bg-spill-amber/15 text-spill-amber border-spill-amber/40' 
              : 'bg-radar-850 text-radar-500 border-radar-750'
          }`}
        >
          <div className="flex items-center gap-1.5">
            <Flame className="w-3 h-3" />
            <span>SAR SPILLS ({spills.length})</span>
          </div>
          {showSpills ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
        </button>

        {/* Vessels Layer Toggle */}
        <button
          onClick={() => setShowVessels(!showVessels)}
          className={`flex items-center justify-between gap-3 px-2 py-1 rounded-xs border text-[11px] transition-colors ${
            showVessels 
              ? 'bg-vessel-teal/15 text-vessel-teal border-vessel-teal/40' 
              : 'bg-radar-850 text-radar-500 border-radar-750'
          }`}
        >
          <div className="flex items-center gap-1.5">
            <Ship className="w-3 h-3" />
            <span>ALL AIS VESSELS ({vessels.length})</span>
          </div>
          {showVessels ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
        </button>

        {/* Suspects Only Toggle */}
        <button
          onClick={() => setSuspectsOnly(!suspectsOnly)}
          className={`flex items-center justify-between gap-3 px-2 py-1 rounded-xs border text-[11px] transition-colors ${
            suspectsOnly 
              ? 'bg-suspect-crimson/20 text-suspect-crimson border-suspect-crimson/50 font-bold' 
              : 'bg-radar-850 text-radar-400 border-radar-750'
          }`}
        >
          <div className="flex items-center gap-1.5">
            <Radio className="w-3 h-3" />
            <span>SUSPECTS ONLY</span>
          </div>
          <span className="text-[10px]">{suspectsOnly ? 'ACTIVE' : 'OFF'}</span>
        </button>

        {/* Suspect Connecting Vectors Toggle */}
        <button
          onClick={() => setShowVectors(!showVectors)}
          className={`flex items-center justify-between gap-3 px-2 py-1 rounded-xs border text-[11px] transition-colors ${
            showVectors 
              ? 'bg-radar-800 text-radar-200 border-radar-600' 
              : 'bg-radar-850 text-radar-500 border-radar-750'
          }`}
        >
          <div className="flex items-center gap-1.5">
            <Crosshair className="w-3 h-3 text-suspect-crimson" />
            <span>ATTRIBUTION VECTORS</span>
          </div>
          {showVectors ? <Eye className="w-3 h-3" /> : <EyeOff className="w-3 h-3" />}
        </button>

        {/* Reset View Button */}
        <button
          onClick={handleResetZoom}
          className="mt-1 flex items-center justify-center gap-1.5 px-2 py-1 bg-radar-800 hover:bg-radar-750 border border-radar-700 rounded-xs text-[10px] text-radar-300"
        >
          <Maximize2 className="w-3 h-3" />
          <span>RESET SECTOR EXTENT</span>
        </button>
      </div>

      {/* Floating Coordinate Crosshairs Readout (Bottom Left) */}
      <div className="absolute bottom-3 left-3 z-10 flex items-center gap-2 bg-radar-900/90 border border-radar-700/80 rounded-xs px-2.5 py-1 text-[11px] font-mono text-radar-300 select-none backdrop-blur-xs">
        <Crosshair className="w-3.5 h-3.5 text-radar-400" />
        {cursorCoords ? (
          <div className="flex items-center gap-3">
            <span>
              LAT: <strong className="text-radar-100">{Math.abs(cursorCoords.lat).toFixed(4)}° {cursorCoords.lat >= 0 ? 'N' : 'S'}</strong>
            </span>
            <span>
              LNG: <strong className="text-radar-100">{Math.abs(cursorCoords.lng).toFixed(4)}° {cursorCoords.lng >= 0 ? 'E' : 'W'}</strong>
            </span>
            <span className="text-radar-500">|</span>
            <span className="text-radar-400">DATUM: WGS-84</span>
          </div>
        ) : (
          <span className="text-radar-500">HOVER OVER MAP FOR REAL-TIME AIS / SAR FIX</span>
        )}
      </div>

      {/* Map Scale / Reference Legend (Bottom Right above drawer) */}
      <div className="absolute bottom-3 right-3 z-10 flex items-center gap-3 bg-radar-900/90 border border-radar-700/80 rounded-xs px-2 py-1 text-[10px] font-mono text-radar-400 select-none">
        <div className="flex items-center gap-1">
          <div className="w-2.5 h-2.5 bg-spill-amber/40 border border-spill-amber rounded-xs"></div>
          <span>SAR Slick</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rotate-45 bg-vessel-teal"></div>
          <span>AIS Vessel</span>
        </div>
        <div className="flex items-center gap-1">
          <div className="w-2 h-2 rotate-45 bg-suspect-crimson ring-1 ring-white"></div>
          <span>Flagged Suspect</span>
        </div>
      </div>
    </div>
  );
});
