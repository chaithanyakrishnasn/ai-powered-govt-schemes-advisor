import { apiClient } from './client';
import type { SchemeResultItem } from '@/types/api';

export interface ChatMessage {
  role: 'user' | 'model';
  content: string;
}

export interface ChatRequest {
  message: string;
  history: ChatMessage[];
  profile_id?: string;
  language?: string;
}

export interface ChatApiResponse {
  response: string;
  schemes?: SchemeResultItem[];
  should_show_schemes: boolean;
}

export const sendChatMessage = (req: ChatRequest): Promise<ChatApiResponse> =>
  apiClient.post<ChatApiResponse>('/chat', req).then(r => r.data);
