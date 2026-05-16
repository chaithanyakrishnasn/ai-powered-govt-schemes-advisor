import { apiClient } from './client';
import type { MatchRequest, MatchResponse, UserProfile } from '@/types/api';

export const runMatch = async (req: MatchRequest): Promise<MatchResponse> => {
  const response = await apiClient.post('/match', req);
  return response.data;
};

/**
 * Establishes a Server-Sent Events (SSE) connection for real-time match results.
 *
 * This function constructs a URL with query parameters to send the match request
 * to the backend's SSE endpoint. The user profile is serialized as a JSON string
 * in a query parameter.
 *
 * @param params - The parameters for the match request.
 * @returns A native EventSource instance. The caller is responsible for handling
 *          the 'message', 'error', and 'open' events.
 *
 * @example
 * const eventSource = streamMatch({ profile, query: "scholarship" });
 * eventSource.onmessage = (event) => {
 *   const data = JSON.parse(event.data);
 *   // a an...
 * };
 * eventSource.onerror = (err) => {
 *   console.error("EventSource failed:", err);
 *   eventSource.close();
 * };
 */
export const streamMatch = (params: {
  profile_id?: string;
  profile?: UserProfile;
  query?: string;
  explain?: boolean;
  language?: string;
}): EventSource => {
  const url = new URL(`${apiClient.defaults.baseURL}/match/stream`);
  if (params.profile_id) {
    url.searchParams.append('profile_id', params.profile_id);
  }
  if (params.profile) {
    url.searchParams.append('profile', JSON.stringify(params.profile));
  }
  if (params.query) {
    url.searchParams.append('query', params.query);
  }
  if (params.explain) {
    url.searchParams.append('explain', String(params.explain));
  }
  if (params.language) {
    url.searchParams.append('language', params.language);
  }

  return new EventSource(url.toString());
};
