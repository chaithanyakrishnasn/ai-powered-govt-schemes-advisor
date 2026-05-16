'use client';

import { useRef, useEffect } from 'react';
import { ChatMessage } from '@/types/chat';
import { MessageBubble } from './MessageBubble';

interface MessageListProps {
  messages: ChatMessage[];
}

export function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="flex-1 w-full overflow-y-auto px-4 py-6 custom-scrollbar">
      <div className="max-w-3xl mx-auto w-full flex flex-col">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} className="h-4 shrink-0" />
      </div>
    </div>
  );
}
