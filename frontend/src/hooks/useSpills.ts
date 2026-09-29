import { useQuery } from '@tanstack/react-query';
import { API_CONFIG } from '../config/api';
import { dataService } from '../services/dataService';
import { Spill } from '../types/api';

export function useSpills(useMock: boolean) {
  return useQuery<Spill[]>({
    queryKey: ['spills', useMock],
    queryFn: () => dataService.getSpills(useMock),
    refetchInterval: useMock ? API_CONFIG.POLL_INTERVAL_SPILLS_MS : false,
    staleTime: 10_000,
  });
}
