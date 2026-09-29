import { useQuery } from '@tanstack/react-query';
import { API_CONFIG } from '../config/api';
import { dataService } from '../services/dataService';
import { Suspect } from '../types/api';

export function useSuspects(useMock: boolean) {
  return useQuery<Suspect[]>({
    queryKey: ['suspects', useMock],
    queryFn: () => dataService.getSuspects(useMock),
    refetchInterval: useMock ? API_CONFIG.POLL_INTERVAL_SUSPECTS_MS : false,
    staleTime: 10_000,
  });
}
