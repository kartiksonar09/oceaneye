import { useQuery } from '@tanstack/react-query';
import { API_CONFIG } from '../config/api';
import { dataService } from '../services/dataService';
import { Vessel } from '../types/api';

export function useVessels(useMock: boolean) {
  return useQuery<Vessel[]>({
    queryKey: ['vessels', useMock],
    queryFn: () => dataService.getVessels(useMock),
    refetchInterval: useMock ? API_CONFIG.POLL_INTERVAL_VESSELS_MS : false,
    staleTime: 5_000,
  });
}
