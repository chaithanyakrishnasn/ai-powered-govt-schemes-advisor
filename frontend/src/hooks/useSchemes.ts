import { useQuery } from '@tanstack/react-query';
import { getSchemes, getScheme } from '@/lib/api/schemes';
import type { PaginatedSchemes, SchemeDetail } from '@/types/api';

export function useSchemes(params?: Record<string, string>) {
  return useQuery<PaginatedSchemes, Error>({
    queryKey: ['schemes', params],
    queryFn: () => getSchemes(params),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useScheme(slug: string) {
  return useQuery<SchemeDetail, Error>({
    queryKey: ['scheme', slug],
    queryFn: () => getScheme(slug),
    staleTime: 10 * 60 * 1000, // 10 minutes
    enabled: !!slug,
  });
}
