'use client';

import { useTranslations } from 'next-intl';
import { SchemeResultItem, SchemeExplanation } from '@/types/api';
import { Button } from '@/components/ui/button';
import { Loader2, ExternalLink, Info, CheckCircle, ChevronDown } from 'lucide-react';
import { useState } from 'react';

interface ExplanationPanelProps {
  scheme: SchemeResultItem | null;
  explanation: SchemeExplanation | null;
  isLoading: boolean;
  onApply: (url: string) => void;
  onViewDetails: (slug: string) => void;
}

export function ExplanationPanel({ scheme, explanation, isLoading, onApply, onViewDetails }: ExplanationPanelProps) {
  const t = useTranslations('results');
  const [openSections, setOpenSections] = useState({
    benefits: false,
    nextSteps: false,
    missingInfo: false
  });

  const toggleSection = (section: keyof typeof openSections) => {
    setOpenSections(prev => ({ ...prev, [section]: !prev[section] }));
  };

  if (!scheme) {
    return (
      <div className="h-full flex flex-col items-center justify-center p-8 text-center text-slate-400 bg-slate-50">
        <Info className="w-12 h-12 mb-4 opacity-20" />
        <p className="font-bold text-slate-500">{t('selectSchemePrompt')}</p>
      </div>
    );
  }

  const borderColors: Record<string, string> = {
    eligible: 'border-green-500',
    likely_eligible: 'border-amber-400',
    need_more_info: 'border-slate-300',
    not_eligible: 'border-red-300',
  };

  return (
    <div className={`flex flex-col h-full bg-white animate-in slide-in-from-right duration-300 border-l-4 ${borderColors[scheme.status]}`}>
      <div className="p-6 border-b border-slate-100 bg-slate-50/50">
        <h2 className="text-xl font-extrabold text-slate-900 leading-snug mb-2">{scheme.name}</h2>
        <p className="text-sm font-bold text-slate-500 mb-3">{scheme.state || 'Central Government'}</p>
        <div className="flex items-center gap-3">
          {explanation && (
            <span className="text-xs font-bold text-indigo-600 bg-indigo-50 px-3 py-1 rounded-full ring-1 ring-indigo-600/20 uppercase tracking-wider">
              {Math.round(explanation.confidence * 100)}% Confidence Match
            </span>
          )}
        </div>
      </div>

      <div className="p-6 flex-1 space-y-6 overflow-y-auto custom-scrollbar">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-500 gap-4">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
            <p className="font-bold">Analyzing your eligibility...</p>
          </div>
        ) : explanation ? (
          <div className="space-y-6 animate-in fade-in duration-300">
            {/* Why this matches */}
            <div className="space-y-3">
              <h3 className="text-sm font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                Why this matches you <div className="h-px bg-slate-200 flex-1 ml-2" />
              </h3>
              <p className="text-[15px] leading-relaxed text-slate-700 font-medium bg-slate-50 p-4 rounded-xl border border-slate-100">
                {explanation.explanation}
              </p>
            </div>

            {/* Key Benefits (Accordion) */}
            {explanation.key_benefits && explanation.key_benefits.length > 0 && (
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <button 
                  onClick={() => toggleSection('benefits')}
                  className="w-full flex items-center justify-between p-4 bg-slate-50 hover:bg-slate-100/50 transition-colors"
                >
                  <h3 className="font-bold text-slate-900">Key Benefits</h3>
                  <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${openSections.benefits ? 'rotate-180' : ''}`} />
                </button>
                {openSections.benefits && (
                  <div className="p-4 bg-white border-t border-slate-100">
                    <ul className="space-y-3">
                      {explanation.key_benefits.map((benefit, i) => (
                        <li key={i} className="text-sm flex items-start gap-3 text-slate-700">
                          <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                          <span className="leading-relaxed font-medium">{benefit}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}

            {/* Next Steps (Accordion) */}
            {explanation.action_steps && explanation.action_steps.length > 0 && (
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <button 
                  onClick={() => toggleSection('nextSteps')}
                  className="w-full flex items-center justify-between p-4 bg-slate-50 hover:bg-slate-100/50 transition-colors"
                >
                  <h3 className="font-bold text-slate-900">Next Steps</h3>
                  <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${openSections.nextSteps ? 'rotate-180' : ''}`} />
                </button>
                {openSections.nextSteps && (
                  <div className="p-4 bg-white border-t border-slate-100">
                    <ol className="list-decimal pl-5 space-y-3">
                      {explanation.action_steps.map((step, i) => (
                        <li key={i} className="text-sm text-slate-700 leading-relaxed font-medium">{step}</li>
                      ))}
                    </ol>
                  </div>
                )}
              </div>
            )}

            {/* Missing Info (Accordion) */}
            {explanation.missing_info && explanation.missing_info.length > 0 && (
              <div className="border border-slate-200 rounded-xl overflow-hidden">
                <button 
                  onClick={() => toggleSection('missingInfo')}
                  className="w-full flex items-center justify-between p-4 bg-slate-50 hover:bg-slate-100/50 transition-colors"
                >
                  <h3 className="font-bold text-slate-900">What to Gather</h3>
                  <ChevronDown className={`w-4 h-4 text-slate-400 transition-transform ${openSections.missingInfo ? 'rotate-180' : ''}`} />
                </button>
                {openSections.missingInfo && (
                  <div className="p-4 bg-white border-t border-slate-100">
                    <ul className="list-disc pl-5 space-y-2">
                      {explanation.missing_info.map((info, i) => (
                        <li key={i} className="text-sm text-slate-700 leading-relaxed font-medium">{info}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-slate-500 gap-3">
            <p className="font-bold text-center">Select &quot;Explain&quot; on the left to see why you qualify.</p>
          </div>
        )}
      </div>

      <div className="p-6 border-t border-slate-100 bg-white flex flex-col sm:flex-row gap-3 mt-auto shadow-[0_-10px_20px_-15px_rgba(0,0,0,0.05)]">
        <Button
          variant="outline"
          className="w-full sm:w-1/3 border-slate-200 text-slate-700 hover:bg-slate-50 hover:text-slate-900 font-bold h-11"
          onClick={() => onViewDetails(scheme.slug)}
        >
          {t('viewDetails')}
        </Button>
        <Button
          className="w-full sm:w-2/3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold h-11 shadow-sm"
          disabled={!scheme.application_url}
          onClick={() => scheme.application_url && onApply(scheme.application_url)}
        >
          {scheme.application_url ? t('apply') : t('applyUnavailable')}
          {scheme.application_url && <ExternalLink className="w-4 h-4 ml-2" />}
        </Button>
      </div>
    </div>
  );
}