import { useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Vessel, Spill, Suspect, OperationalAlert, WebSocketMessageType } from '../types/api';
import { API_CONFIG } from '../config/api';

export function useWebSockets(useMock: boolean) {
  const queryClient = useQueryClient();
  const wsRef = useRef<WebSocket | null>(null);
  
  useEffect(() => {
    if (useMock) return;

    let reconnectTimeout: ReturnType<typeof setTimeout>;
    
    const connect = () => {
      // Build WS URL
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}${API_CONFIG.BASE_URL}/ws/feed`;
      
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as WebSocketMessageType;
          
          if (msg.type === 'vessel_update') {
            queryClient.setQueryData<Vessel[]>(['vessels', false], (old = []) => {
              const idx = old.findIndex(v => v.mmsi === msg.data.mmsi);
              if (idx >= 0) {
                const newArr = [...old];
                newArr[idx] = { ...newArr[idx], ...msg.data };
                return newArr;
              }
              return [...old, msg.data];
            });
          } else if (msg.type === 'spill_update') {
            queryClient.setQueryData<Spill[]>(['spills', false], (old = []) => {
              const idx = old.findIndex(s => s.id === msg.data.id);
              if (idx >= 0) {
                const newArr = [...old];
                newArr[idx] = { ...newArr[idx], ...msg.data };
                return newArr;
              }
              return [...old, msg.data];
            });
          } else if (msg.type === 'suspect_flagged') {
            queryClient.setQueryData<Suspect[]>(['suspects', false], (old = []) => {
              const idx = old.findIndex(s => s.vessel_mmsi === msg.data.vessel_mmsi);
              if (idx >= 0) {
                const newArr = [...old];
                newArr[idx] = { ...newArr[idx], ...msg.data };
                return newArr;
              }
              return [...old, msg.data];
            });
          } else if (msg.type === 'spill_resolved') {
             queryClient.setQueryData<Spill[]>(['spills', false], (old = []) => 
                old.map(s => s.id === msg.data.id ? { ...s, status: 'resolved' } : s)
             );
          }
        } catch (e) {
          console.error("Failed to parse WS message", e);
        }
      };

      ws.onclose = () => {
        reconnectTimeout = setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectTimeout);
      if (wsRef.current) {
        wsRef.current.onclose = null; // Prevent reconnect on explicit unmount
        wsRef.current.close();
      }
    };
  }, [useMock, queryClient]);
}
