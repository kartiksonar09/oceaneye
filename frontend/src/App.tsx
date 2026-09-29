import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { TopNav } from './components/layout/TopNav';
import { SpillList } from './components/sidebar/SpillList';
import { MapCanvas } from './components/map/MapCanvas';
import { DetailDrawer } from './components/detail/DetailDrawer';
import { ActivityFeed } from './components/activity/ActivityFeed';
import { VesselDirectoryModal } from './components/vessels/VesselDirectoryModal';
import { API_CONFIG, setStoredMockMode, getStoredMockMode } from './config/api';
import { useSpills } from './hooks/useSpills';
import { useVessels } from './hooks/useVessels';
import { useSuspects } from './hooks/useSuspects';
import { useWebSockets } from './hooks/useWebSockets';
import { dataService } from './services/dataService';
import { SURVEILLANCE_REGIONS } from './services/mockData';
import { OperationalAlert, RegionZone, Spill, Vessel } from './types/api';
import { TrajectoryPoint } from './utils/vesselTrajectory';

type WindowWithWebkitAudio = Window & {
  webkitAudioContext?: typeof AudioContext;
};

export const App: React.FC = () => {
  // Region & Mode State
  const [currentRegion, setCurrentRegion] = useState<RegionZone>(SURVEILLANCE_REGIONS[0]);
  const [useMock, setUseMock] = useState<boolean>(getStoredMockMode());
  const [audioMuted, setAudioMuted] = useState<boolean>(true);

  // Layout UI State
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);
  const [selectedSpill, setSelectedSpill] = useState<Spill | null>(null);
  const [selectedVessel, setSelectedVessel] = useState<Vessel | null>(null);
  const [scrubbedPoint, setScrubbedPoint] = useState<TrajectoryPoint | null>(null);
  const [showFleetModal, setShowFleetModal] = useState<boolean>(false);

  // Queries with automatic polling
  const { data: spills = [], isLoading: isLoadingSpills } = useSpills(useMock);
  const { data: vessels = [], isLoading: isLoadingVessels } = useVessels(useMock);
  const { data: suspects = [], isLoading: isLoadingSuspects } = useSuspects(useMock);

  // Initialize WebSockets
  useWebSockets(useMock);

  // Operational alerts query
  const { data: alerts = [], isLoading: isLoadingAlerts } = useQuery<OperationalAlert[]>({
    queryKey: ['alerts', useMock],
    queryFn: () => dataService.getAlerts(useMock),
    refetchInterval: useMock ? 15_000 : false,
  });

  // Default selection on load
  useEffect(() => {
    if (spills.length > 0 && !selectedSpill) {
      setSelectedSpill(spills[0]);
    }
  }, [spills, selectedSpill]);

  // Global Audio Context Singleton
  const audioCtxRef = React.useRef<AudioContext | null>(null);

  const getAudioContext = () => {
    if (!audioCtxRef.current) {
      const AudioContextClass = window.AudioContext || (window as WindowWithWebkitAudio).webkitAudioContext;
      if (AudioContextClass) {
        audioCtxRef.current = new AudioContextClass();
      }
    }
    if (audioCtxRef.current && audioCtxRef.current.state === 'suspended') {
      audioCtxRef.current.resume();
    }
    return audioCtxRef.current;
  };

  // Lifecycle cleanup of AudioContext on unmount
  useEffect(() => {
    return () => {
      if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
        audioCtxRef.current.close().catch(() => {});
      }
    };
  }, []);

  // Audio ping on critical alerts
  const playTacticalAlert = React.useCallback(() => {
    if (audioMuted) return;
    try {
      const audioCtx = getAudioContext();
      if (!audioCtx) return;
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, audioCtx.currentTime); // A5
      osc.frequency.exponentialRampToValueAtTime(440, audioCtx.currentTime + 0.15);
      gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.25);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.25);
    } catch {
      // AudioContext not allowed before user gesture
    }
  }, [audioMuted]);

  // Trigger alert on new critical events
  const lastAlertCount = React.useRef(0);
  useEffect(() => {
    if (alerts.length > lastAlertCount.current) {
      const newAlerts = alerts.slice(0, alerts.length - lastAlertCount.current);
      if (newAlerts.some(a => a.severity === 'CRITICAL')) {
        playTacticalAlert();
      }
    }
    lastAlertCount.current = alerts.length;
  }, [alerts, playTacticalAlert]);

  const handleToggleMock = React.useCallback(() => {
    const nextVal = !useMock;
    setUseMock(nextVal);
    setStoredMockMode(nextVal);
  }, [useMock]);

  const handleSelectSpill = React.useCallback((spill: Spill) => {
    setSelectedSpill(spill);
    // Find if there is a primary suspect for this spill
    const linkedSuspect = suspects.find(s => s.spill_id === spill.id);
    if (linkedSuspect) {
      const v = vessels.find(vs => vs.mmsi === linkedSuspect.vessel_mmsi);
      if (v) setSelectedVessel(v);
    }
  }, [suspects, vessels]);

  const handleSelectVessel = React.useCallback((vessel: Vessel) => {
    setSelectedVessel(vessel);
    setScrubbedPoint(null);
  }, []);

  const handleCloseDetail = () => {
    setSelectedSpill(null);
    setSelectedVessel(null);
    setScrubbedPoint(null);
  };

  return (
    <div className="w-screen h-screen flex flex-col bg-radar-950 text-radar-200 overflow-hidden font-sans">
      {/* Top Operations Header */}
      <TopNav
        currentRegion={currentRegion}
        onSelectRegion={setCurrentRegion}
        useMock={useMock}
        onToggleMock={handleToggleMock}
        audioMuted={audioMuted}
        onToggleAudio={() => {
          setAudioMuted(!audioMuted);
          if (audioMuted) playTacticalAlert();
        }}
        activeSpillCount={spills.filter((s) => s.status === 'active').length}
        trackedVesselCount={vessels.length}
        suspectCount={suspects.length}
        onOpenFleetDirectory={() => setShowFleetModal(true)}
      />

      {/* Main Operational Workspace */}
      <div className="flex-1 flex relative overflow-hidden">
        {/* Left: Collapsible Spill Feed */}
        <SpillList
          spills={spills}
          selectedSpill={selectedSpill}
          onSelectSpill={handleSelectSpill}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          isLoading={isLoadingSpills}
        />

        {/* Central Map Canvas */}
        <div className="flex-1 h-full relative">
          <MapCanvas
            currentRegion={currentRegion}
            spills={spills}
            vessels={vessels}
            suspects={suspects}
            selectedSpill={selectedSpill}
            selectedVessel={selectedVessel}
            onSelectSpill={handleSelectSpill}
            onSelectVessel={handleSelectVessel}
            scrubbedPoint={scrubbedPoint}
          />
        </div>

        {/* Right: Slide-in Detail Analysis Drawer */}
        <DetailDrawer
          selectedSpill={selectedSpill}
          selectedVessel={selectedVessel}
          suspects={suspects}
          vessels={vessels}
          spills={spills}
          onSelectSpill={handleSelectSpill}
          onSelectVessel={handleSelectVessel}
          onClose={handleCloseDetail}
          onScrubPoint={setScrubbedPoint}
        />
      </div>

      {/* Bottom Operational Activity Log Drawer */}
      <ActivityFeed
        alerts={alerts}
        spills={spills}
        vessels={vessels}
        onSelectSpill={handleSelectSpill}
        onSelectVessel={handleSelectVessel}
        isLoading={isLoadingAlerts}
      />

      {/* Full Fleet Directory & Photometry Modal */}
      <VesselDirectoryModal
        isOpen={showFleetModal}
        onClose={() => setShowFleetModal(false)}
        vessels={vessels}
        suspects={suspects}
        onSelectVessel={handleSelectVessel}
        isLoading={isLoadingVessels || isLoadingSuspects}
      />
    </div>
  );
};

export default App;
