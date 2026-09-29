import React from 'react';
import { 
  Radar, 
  Radio, 
  Clock, 
  MapPin, 
  Server, 
  Volume2, 
  VolumeX, 
  Layers,
  ChevronDown,
  Sun,
  Moon
} from 'lucide-react';
import { useLiveClock } from '../../hooks/useLiveClock';
import { SURVEILLANCE_REGIONS } from '../../services/mockData';
import { RegionZone } from '../../types/api';
import { useTheme } from '../../context/ThemeContext';

interface TopNavProps {
  currentRegion: RegionZone;
  onSelectRegion: (region: RegionZone) => void;
  useMock: boolean;
  onToggleMock: () => void;
  audioMuted: boolean;
  onToggleAudio: () => void;
  activeSpillCount: number;
  trackedVesselCount: number;
  suspectCount: number;
  onOpenFleetDirectory: () => void;
}

export const TopNav: React.FC<TopNavProps> = ({
  currentRegion,
  onSelectRegion,
  useMock,
  onToggleMock,
  audioMuted,
  onToggleAudio,
  activeSpillCount,
  trackedVesselCount,
  suspectCount,
  onOpenFleetDirectory,
}) => {
  const { utcString, secondsUntilPoll } = useLiveClock(15000);
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="h-12 bg-radar-900 border-b border-radar-700/80 px-4 flex items-center justify-between select-none z-30 relative">
      {/* Brand & System Identifier */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-radar-100">
          <div className="w-7 h-7 rounded-sm bg-radar-800 border border-radar-700 flex items-center justify-center text-spill-amber relative overflow-hidden">
            <Radar className="w-4 h-4 animate-spin" style={{ animationDuration: '8s' }} />
            <div className="absolute inset-0 bg-spill-amber/10 pointer-events-none" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center gap-1.5">
              <span className="font-mono font-bold tracking-wider text-sm text-radar-100">OCEAN EYE</span>
              <span className="text-[10px] font-mono px-1 py-0.2 rounded-xs bg-radar-800 border border-radar-700 text-radar-400">
                v2.4-OPS
              </span>
            </div>
            <span className="text-[9px] font-mono tracking-widest text-radar-500 uppercase">
              SAR SLICK // AIS ATTRIBUTION CONSOLE
            </span>
          </div>
        </div>

        {/* Operational Telemetry Chips */}
        <div className="hidden lg:flex items-center gap-2 ml-4 pl-4 border-l border-radar-700/60 font-mono text-[11px]">
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-xs bg-radar-850 border border-radar-700/80">
            <span className="w-1.5 h-1.5 rounded-full bg-spill-amber animate-pulse" />
            <span className="text-radar-400">ACTIVE SPILLS:</span>
            <span className="text-spill-amber font-semibold">{activeSpillCount}</span>
          </div>

          <button
            onClick={onOpenFleetDirectory}
            title="Open Live Vessel Fleet Directory & Photometry"
            className="flex items-center gap-1.5 px-2 py-0.5 rounded-xs bg-radar-850 hover:bg-radar-800 border border-radar-700/80 text-radar-300 hover:text-white transition-colors cursor-pointer"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-vessel-teal" />
            <span className="text-radar-400">TRACKED:</span>
            <span className="text-vessel-teal font-semibold">{trackedVesselCount}</span>
            <span className="text-[9px] text-radar-500 ml-0.5 underline">FLEET [ALL]</span>
          </button>

          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-xs bg-radar-850 border border-radar-700/80">
            <span className="w-1.5 h-1.5 rounded-full bg-suspect-crimson animate-ping" />
            <span className="text-radar-400">SUSPECTS:</span>
            <span className="text-suspect-crimson font-bold">{suspectCount}</span>
          </div>
        </div>
      </div>

      {/* Center: Surveillance Sector Selector */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1.5 bg-radar-850 border border-radar-700/90 rounded-xs px-2.5 py-1 text-xs font-mono">
          <MapPin className="w-3.5 h-3.5 text-radar-400" />
          <span className="text-radar-400 text-[11px]">ZONE:</span>
          <select 
            aria-label="Surveillance Zone"
            value={currentRegion.id}
            onChange={(e) => {
              const reg = SURVEILLANCE_REGIONS.find((r) => r.id === e.target.value);
              if (reg) onSelectRegion(reg);
            }}
            className="bg-transparent text-radar-200 font-semibold focus:outline-none cursor-pointer pr-1"
          >
            {SURVEILLANCE_REGIONS.map((r) => (
              <option key={r.id} value={r.id} className="bg-radar-900 text-radar-200">
                {r.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Right Controls: Mode Toggle, Telemetry Polling, UTC Clock */}
      <div className="flex items-center gap-3">
        {/* Mock / Live Backend Toggle */}
        <button
          onClick={onToggleMock}
          title={useMock ? "Running High-Fidelity Local Simulation. Click to switch to Live FastAPI Backend" : "Connected to Live FastAPI Backend. Click to switch to Mock"}
          className={`flex items-center gap-1.5 px-2.5 py-1 rounded-xs border text-[11px] font-mono transition-colors ${
            useMock 
              ? 'bg-radar-800 text-radar-300 border-radar-600 hover:bg-radar-750' 
              : 'bg-emerald-950/60 text-emerald-300 border-emerald-600/80 hover:bg-emerald-900/60'
          }`}
        >
          <Server className="w-3 h-3 text-current" />
          <span>FEED: {useMock ? 'SIMULATED (MOCK)' : 'LIVE FASTAPI'}</span>
        </button>

        {/* Polling Countdown Indicator */}
        <div 
          className="hidden sm:flex items-center gap-1.5 px-2 py-1 rounded-xs bg-radar-850 border border-radar-700 text-[11px] font-mono text-radar-300"
          title="Automatic AIS Vessel Kinematic Poll Interval"
        >
          <Radio className="w-3 h-3 text-vessel-teal animate-pulse" />
          <span className="text-radar-400">NEXT PING:</span>
          <span className="w-5 text-right font-bold text-radar-200">{secondsUntilPoll}s</span>
        </div>

        {/* Audio Alert Toggle */}
        <button
          onClick={onToggleAudio}
          title={audioMuted ? "Unmute Tactical Alerts" : "Mute Alerts"}
          className="p-1.5 rounded-xs bg-radar-850 border border-radar-700 hover:bg-radar-800 text-radar-400 hover:text-radar-200"
        >
          {audioMuted ? <VolumeX className="w-3.5 h-3.5 text-radar-500" /> : <Volume2 className="w-3.5 h-3.5 text-spill-amber" />}
        </button>

        {/* Light / Dark Theme Toggle */}
        <button
          onClick={toggleTheme}
          title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          aria-label={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
          className="p-1.5 rounded-xs bg-radar-850 border border-radar-700 hover:bg-radar-800 text-radar-400 hover:text-radar-200 transition-colors"
        >
          {theme === 'dark'
            ? <Sun className="w-3.5 h-3.5 text-spill-amber" />
            : <Moon className="w-3.5 h-3.5 text-radar-400" />
          }
        </button>

        {/* Monospace Operational Clock */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-xs bg-radar-850 border border-radar-700/90 font-mono text-xs text-radar-200">
          <Clock className="w-3.5 h-3.5 text-radar-400" />
          <span className="tracking-tight">{utcString}</span>
        </div>
      </div>
    </header>
  );
};
