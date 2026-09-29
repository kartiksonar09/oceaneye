import React, { useState, useEffect, useRef } from 'react';
import { 
  Play, 
  Pause, 
  RotateCcw, 
  SkipBack, 
  SkipForward, 
  Clock, 
  AlertTriangle, 
  Compass, 
  Gauge, 
  MapPin,
  Radio
} from 'lucide-react';
import { Vessel } from '../../types/api';
import { getVesselTrajectory, TrajectoryPoint } from '../../utils/vesselTrajectory';
import { safeFormatTimestamp } from '../../utils/core';

interface TimelineScrubberProps {
  vessel: Vessel;
  onScrubPoint?: (point: TrajectoryPoint | null) => void;
}

export const TimelineScrubber: React.FC<TimelineScrubberProps> = ({
  vessel,
  onScrubPoint,
}) => {
  const trajectory = React.useMemo(
    () => getVesselTrajectory(vessel, 24, 15),
    [vessel]
  );

  // currentIndex: defaults to the latest live point (last in array)
  const [currentIndex, setCurrentIndex] = useState<number>(trajectory.length - 1);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const playTimerRef = useRef<number | null>(null);

  // Reset to live point when vessel changes
  useEffect(() => {
    const liveIdx = trajectory.length - 1;
    setCurrentIndex(liveIdx);
    setIsPlaying(false);
    onScrubPoint?.(null);
  }, [vessel.mmsi, trajectory, onScrubPoint]);

  // Handle Playback animation
  useEffect(() => {
    if (isPlaying) {
      playTimerRef.current = window.setInterval(() => {
        setCurrentIndex((prev) => {
          if (prev >= trajectory.length - 1) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, 400);
    } else if (playTimerRef.current) {
      clearInterval(playTimerRef.current);
      playTimerRef.current = null;
    }

    return () => {
      if (playTimerRef.current) clearInterval(playTimerRef.current);
    };
  }, [isPlaying, trajectory.length]);

  // Notify parent on scrub
  useEffect(() => {
    const isLive = currentIndex === trajectory.length - 1;
    const pt = trajectory[currentIndex] || null;
    onScrubPoint?.(isLive ? null : pt);
  }, [currentIndex, trajectory, onScrubPoint]);

  const currentPoint = trajectory[currentIndex] || trajectory[trajectory.length - 1];
  const isLive = currentIndex === trajectory.length - 1;

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setIsPlaying(false);
    setCurrentIndex(Number(e.target.value));
  };

  const handleStepBack = () => {
    setIsPlaying(false);
    setCurrentIndex((prev) => Math.max(0, prev - 1));
  };

  const handleStepForward = () => {
    setIsPlaying(false);
    setCurrentIndex((prev) => Math.min(trajectory.length - 1, prev + 1));
  };

  const handleResetLive = () => {
    setIsPlaying(false);
    setCurrentIndex(trajectory.length - 1);
  };

  return (
    <div className="bg-radar-850 border border-radar-700/80 rounded-xs p-3 font-mono text-xs space-y-2.5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-radar-750 pb-1.5">
        <div className="flex items-center gap-1.5 text-radar-200 font-bold text-[11px]">
          <Clock className="w-3.5 h-3.5 text-vessel-teal" />
          <span>HISTORICAL AIS TRAJECTORY SCRUBBER</span>
        </div>
        <div className="flex items-center gap-1.5">
          {isLive ? (
            <span className="flex items-center gap-1 px-1.5 py-0.2 rounded-xs bg-emerald-950/60 border border-emerald-600/70 text-emerald-400 text-[10px] font-bold">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              LIVE REAL-TIME
            </span>
          ) : (
            <span className="flex items-center gap-1 px-1.5 py-0.2 rounded-xs bg-spill-amber/20 border border-spill-amber/60 text-spill-amber text-[10px] font-bold">
              HISTORICAL (-{currentPoint.minutesAgo}m)
            </span>
          )}
        </div>
      </div>

      {/* AIS Gap Alert if currently scrubbed into a dark gap */}
      {currentPoint.inGap && (
        <div className="bg-suspect-crimson/15 border border-suspect-crimson/70 p-2 rounded-xs flex items-center gap-2 text-suspect-crimson text-[11px] animate-pulse">
          <AlertTriangle className="w-4 h-4 shrink-0" />
          <span>
            <strong>DARK AIS INTERVAL:</strong> Vessel transponder was silenced during this reconstruction window.
          </span>
        </div>
      )}

      {/* Telemetry at Scrubbed Timestamp */}
      <div className="grid grid-cols-2 gap-2 bg-radar-900/90 p-2 rounded-xs border border-radar-750 text-[11px]">
        <div>
          <span className="text-[9px] text-radar-500 block uppercase">RECONSTRUCTED TIME</span>
          <span className="text-radar-100 font-bold">{safeFormatTimestamp(currentPoint.timestamp)}</span>
        </div>
        <div>
          <span className="text-[9px] text-radar-500 block uppercase">OFFSET FROM LIVE</span>
          <span className={`font-semibold ${isLive ? 'text-emerald-400' : 'text-spill-amber'}`}>
            {isLive ? '0 min (Current Fix)' : `-${currentPoint.minutesAgo} min ago`}
          </span>
        </div>
        <div>
          <span className="text-[9px] text-radar-500 block uppercase">SPEED / HEADING</span>
          <span className="text-radar-200">
            {currentPoint.speed_knots} kt @ {currentPoint.heading}°
          </span>
        </div>
        <div>
          <span className="text-[9px] text-radar-500 block uppercase">ESTIMATED FIX</span>
          <span className="text-radar-200">
            {currentPoint.lat.toFixed(4)}°, {currentPoint.lng.toFixed(4)}°
          </span>
        </div>
      </div>

      {/* Scrub Slider with Visual Gap Bar */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-[10px] text-radar-500 font-mono">
          <span>-6h 00m</span>
          <span>-3h 00m</span>
          <span>LIVE</span>
        </div>

        {/* Visual tick timeline showing gaps */}
        <div className="relative h-2 w-full bg-radar-900 rounded-xs overflow-hidden flex">
          {trajectory.map((pt, idx) => (
            <div
              key={idx}
              className={`flex-1 border-r border-radar-950/40 ${
                pt.inGap
                  ? 'bg-suspect-crimson/60'
                  : idx === currentIndex
                  ? 'bg-vessel-teal'
                  : 'bg-radar-700/50'
              }`}
              title={`${safeFormatTimestamp(pt.timestamp)} (-${pt.minutesAgo}m)${pt.inGap ? ' [AIS DARK]' : ''}`}
            />
          ))}
        </div>

        {/* Range Slider */}
        <input
          type="range"
          min={0}
          max={trajectory.length - 1}
          step={1}
          value={currentIndex}
          onChange={handleSliderChange}
          aria-label="AIS Trajectory Timeline Scrubber"
          className="w-full accent-vessel-teal cursor-pointer h-1.5 bg-radar-750 rounded-xs appearance-none"
        />
      </div>

      {/* Playback & Step Controls */}
      <div className="flex items-center justify-between pt-1">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            title={isPlaying ? 'Pause Trajectory Playback' : 'Play Trajectory Forward'}
            aria-label={isPlaying ? 'Pause Playback' : 'Play Trajectory'}
            className="flex items-center gap-1 px-2.5 py-1 bg-radar-800 hover:bg-radar-750 border border-radar-700 rounded-xs text-[11px] text-radar-200 transition-colors"
          >
            {isPlaying ? (
              <>
                <Pause className="w-3 h-3 text-spill-amber" />
                <span>PAUSE</span>
              </>
            ) : (
              <>
                <Play className="w-3 h-3 text-emerald-400" />
                <span>PLAY</span>
              </>
            )}
          </button>

          <button
            onClick={handleStepBack}
            disabled={currentIndex === 0}
            title="Step Back 15 min"
            aria-label="Step back in timeline"
            className="p-1 rounded-xs bg-radar-800 hover:bg-radar-750 disabled:opacity-40 border border-radar-700 text-radar-300"
          >
            <SkipBack className="w-3 h-3" />
          </button>

          <button
            onClick={handleStepForward}
            disabled={currentIndex === trajectory.length - 1}
            title="Step Forward 15 min"
            aria-label="Step forward in timeline"
            className="p-1 rounded-xs bg-radar-800 hover:bg-radar-750 disabled:opacity-40 border border-radar-700 text-radar-300"
          >
            <SkipForward className="w-3 h-3" />
          </button>
        </div>

        <button
          onClick={handleResetLive}
          disabled={isLive}
          title="Jump to Current Live Position"
          aria-label="Jump to live fix"
          className="flex items-center gap-1 px-2 py-1 bg-radar-800 hover:bg-radar-750 disabled:opacity-40 border border-radar-700 rounded-xs text-[10px] text-radar-300 transition-colors"
        >
          <RotateCcw className="w-2.5 h-2.5" />
          <span>RETURN TO LIVE</span>
        </button>
      </div>
    </div>
  );
};
