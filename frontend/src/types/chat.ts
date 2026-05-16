export type MessageRole = 'user' | 'assistant' | 'system';

import { SchemeResultItem, SchemeExplanation } from './api';

export interface ChatMessage {
  id: string;                     // uuid
  role: MessageRole;
  content: string;                // text content
  timestamp: Date;
  schemes?: SchemeResultItem[];   // attached scheme results (stage1)
  explanations?: SchemeExplanation[]; // attached explanations (stage3)
  isStreaming?: boolean;          // true while SSE is open
  error?: string;
}
