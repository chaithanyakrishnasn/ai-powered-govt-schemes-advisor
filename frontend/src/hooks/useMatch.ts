import { useMutation } from '@tanstack/react-query';
import { runMatch } from '@/lib/api/match';
import type { MatchRequest, MatchResponse } from '@/types/api';

export function useMatch() {
  return useMutation<MatchResponse, Error, MatchRequest>({
    mutationFn: runMatch,
  });
}
