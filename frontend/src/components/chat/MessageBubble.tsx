'use client';

import { ChatMessage } from '@/types/chat';
import { TypingIndicator } from './TypingIndicator';
import { SchemeRecommendation } from './SchemeRecommendation';
import { Sparkles, AlertCircle } from 'lucide-react';

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  
  const timeString = new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  if (isUser) {
    return (
      <div className="flex w-full justify-end mb-4 animate-in slide-in-from-bottom-2 duration-300">
        <div className="flex flex-col items-end gap-1 max-w-[85%] sm:max-w-[70%]">
          <div className="bg-indigo-600 text-white px-4 py-3 rounded-2xl rounded-tr-sm text-[15px] shadow-sm font-medium leading-relaxed">
            {message.content}
          </div>
          <span className="text-[11px] font-bold text-slate-400 px-1">{timeString}</span>
        </div>
      </div>
    );
  }

  // Assistant message
  const hasSchemes = message.schemes && message.schemes.length > 0;

  return (
    <div className="flex w-full justify-start mb-6 animate-in slide-in-from-bottom-2 duration-300">
      <div className="flex flex-col items-start gap-1 max-w-full sm:max-w-[85%]">
        
        <div className="bg-white border border-slate-200 shadow-sm px-4 py-3 rounded-2xl rounded-tl-sm text-[15px] whitespace-pre-wrap text-slate-800 font-medium leading-relaxed">
          {message.content}
          {message.isStreaming && !hasSchemes && <span className="inline-block ml-2"><TypingIndicator /></span>}
        </div>
        <span className="text-[11px] font-bold text-slate-400 px-1">{timeString}</span>

        {hasSchemes && (
          <div className="flex flex-col gap-2 mt-2 w-full">
            <div className="flex items-center gap-1.5 text-xs font-extrabold text-slate-500 mb-1 ml-1 uppercase tracking-wider">
              <Sparkles className="w-3.5 h-3.5 text-amber-500" />
              Recommendations
            </div>
            
            <div className="grid gap-2">
              {message.schemes!.slice(0, 5).map(scheme => (
                <SchemeRecommendation 
                  key={scheme.slug} 
                  scheme={scheme}
                />
              ))}
            </div>
            
            {message.isStreaming && (
              <div className="px-4 py-3 mt-2 bg-slate-50 border border-slate-100 rounded-xl flex items-center gap-3 text-sm font-bold text-slate-500 shadow-sm">
                <TypingIndicator />
                Generating explanations...
              </div>
            )}
          </div>
        )}

        {message.error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-2xl rounded-tl-sm text-sm font-bold flex items-start gap-2 mt-2 shadow-sm">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            {message.error}
          </div>
        )}
      </div>
    </div>
  );
}