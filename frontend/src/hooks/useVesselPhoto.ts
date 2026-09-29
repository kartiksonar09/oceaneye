import { useState, useEffect } from 'react';
import { getVesselPhoto, PhotoResult } from '../services/vesselPhotoService';

interface UseVesselPhotoResult {
  photoResult: PhotoResult | null;
  isLoading: boolean;
}

/**
 * Fetches a vessel photo (with caching) for the given MMSI.
 * Resets on vessel change and handles concurrent fetch cancellation.
 */
export function useVesselPhoto(mmsi: string, imo?: string): UseVesselPhotoResult {
  const [photoResult, setPhotoResult] = useState<PhotoResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    let cancelled = false;

    setPhotoResult(null);
    setIsLoading(true);

    getVesselPhoto(mmsi, imo).then((result) => {
      if (!cancelled) {
        setPhotoResult(result);
        setIsLoading(false);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [mmsi, imo]);

  return { photoResult, isLoading };
}
