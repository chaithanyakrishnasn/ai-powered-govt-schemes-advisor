'use client';

import { useState, useCallback } from 'react';
import { useLocale } from 'next-intl';
import { v4 as uuidv4 } from 'uuid';
import { sendChatMessage, type ChatMessage as ApiChatMessage } from '@/lib/api/chat';
import { useProfileStore } from '@/lib/store/profileStore';
import type { ChatMessage } from '@/types/chat';

import { WelcomeMessage } from './WelcomeMessage';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { Button } from '@/components/ui/button';
import { Trash2, MessageSquare } from 'lucide-react';

export default function ChatShell() {
  const locale = useLocale();
  const { profileId } = useProfileStore();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const handleSend = useCallback(async (messageContent: string) => {
    if (!messageContent.trim() || isLoading) return;

    const userMessage: ChatMessage = {
      id: uuidv4(),
      role: 'user',
      content: messageContent,
      timestamp: new Date(),
    };

    const assistantId = uuidv4();
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true,
    };

    setMessages(prev => [...prev, userMessage, assistantMessage]);
    setIsLoading(true);

    try {
      const history: ApiChatMessage[] = messages
        .filter(m => m.content && !m.isStreaming)
        .map(m => ({
          role: m.role === 'assistant' ? 'model' : 'user',
          content: m.content,
        }));

      const response = await sendChatMessage({
        message: messageContent,
        history,
        profile_id: profileId,
        language: locale,
      });

      setMessages(prev => prev.map(msg =>
        msg.id === assistantId
          ? {
              ...msg,
              content: response.response,
              schemes: response.should_show_schemes ? response.schemes : undefined,
              isStreaming: false,
            }
          : msg
      ));
    } catch (error) {
      setMessages(prev => prev.map(msg =>
        msg.id === assistantId
          ? {
              ...msg,
              content: 'Sorry, something went wrong. Please try again.',
              isStreaming: false,
              error: String(error),
            }
          : msg
      ));
    } finally {
      setIsLoading(false);
    }
  }, [isLoading, messages, profileId, locale]);

  const clearChat = () => {
    setMessages([]);
    setIsLoading(false);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] w-full max-w-3xl mx-auto bg-slate-50 md:border-x border-slate-200 shadow-sm relative">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 bg-white/90 backdrop-blur-md sticky top-0 z-10">
        <div className="flex items-center gap-3">
          <div className="bg-indigo-100 p-2 rounded-full">
            <MessageSquare className="w-5 h-5 text-indigo-600" />
          </div>
          <div>
            <h2 className="font-extrabold text-slate-900 leading-none">Chat</h2>
            <p className="text-xs text-slate-500 font-bold mt-1 uppercase tracking-wider">AI Advisor</p>
          </div>
        </div>
        {messages.length > 0 && (
          <Button 
            variant="ghost" 
            size="sm" 
            onClick={clearChat} 
            className="text-slate-500 hover:text-red-600 hover:bg-red-50 h-9 font-bold"
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Clear chat
          </Button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-hidden flex flex-col relative px-4 sm:px-6">
        {messages.length === 0 ? (
          <div className="h-full overflow-y-auto pt-8">
            <WelcomeMessage onSuggest={handleSend} />
          </div>
        ) : (
          <MessageList messages={messages} />
        )}
      </div>

      {/* Input */}
      <div className="shrink-0 p-4 sm:px-6 bg-white border-t border-slate-200 mt-auto">
        <div className="max-w-3xl mx-auto">
          <ChatInput onSend={handleSend} disabled={isLoading} />
          <div className="text-center mt-3">
            <p className="text-[11px] font-bold text-slate-400 flex items-center justify-center gap-1.5">
              <span>AI can make mistakes. Verify details on official portals.</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}