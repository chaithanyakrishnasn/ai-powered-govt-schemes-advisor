'use client';

import { useTranslations } from 'next-intl';
import { SchemeResultItem } from '@/types/api';
import { Button } from '@/components/ui/button';
import { ExternalLink, AlertTriangle, Zap, CheckCircle2, Info, XCircle } from 'lucide-react';

interface SchemeCardProps {
  scheme: SchemeResultItem;
  isSelected?: boolean;
  onSelect: () => void;
  onExplain: () => void;
}

export function SchemeCard({ scheme, isSelected, onSelect, onExplain }: SchemeCardProps) {
  const t = useTranslations('results');

  const statusConfig = {
    eligible: {
      border: 'border-l-green-500',
      bg: 'hover:bg-slate-50/50',
      icon: <CheckCircle2 className="w-3.5 h-3.5" />,
      badgeBg: 'bg-green-50 text-green-700 ring-green-600/20',
      label: 'ELIGIBLE'
    },
    likely_eligible: {
      border: 'border-l-amber-400',
      bg: 'hover:bg-slate-50/50',
      icon: <CheckCircle2 className="w-3.5 h-3.5" />,
      badgeBg: 'bg-amber-50 text-amber-700 ring-amber-600/20',
      label: 'LIKELY ELIGIBLE'
    },
    need_more_info: {
      border: 'border-l-slate-300',
      bg: 'hover:bg-slate-50/50',
      icon: <Info className="w-3.5 h-3.5" />,
      badgeBg: 'bg-slate-100 text-slate-700 ring-slate-500/20',
      label: 'NEEDS INFO'
    },
    not_eligible: {
      border: 'border-l-red-300',
      bg: 'hover:bg-slate-50/50 opacity-80',
      icon: <XCircle className="w-3.5 h-3.5" />,
      badgeBg: 'bg-red-50 text-red-700 ring-red-600/20',
      label: 'NOT ELIGIBLE'
    },
  };

  const config = statusConfig[scheme.status];
  const selectedClass = isSelected ? 'ring-2 ring-indigo-500/20 shadow-md translate-y-[-2px]' : 'shadow-sm';
  const displayScore = Math.round((scheme.combined_score ?? scheme.score) * 100);

  return (
    <div
      onClick={onSelect}
      className={`relative cursor-pointer transition-all duration-200 bg-white border border-slate-200 rounded-xl p-6 flex flex-col gap-4 border-l-4 hover:shadow-md hover:-translate-y-0.5 ${config.border} ${config.bg} ${selectedClass}`}
    >
      <div className="flex justify-between items-start gap-4">
        <div className="flex flex-col gap-1.5">
          <span className={`inline-flex w-fit items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-bold tracking-wider ring-1 ${config.badgeBg}`}>
            {config.icon}
            {config.label}
          </span>
          <h3 className="font-bold text-slate-900 text-lg leading-snug line-clamp-2 mt-1">{scheme.name}</h3>
          <p className="text-sm font-medium text-slate-500">
            {scheme.level === 'Central' ? 'Central Government' : scheme.state || 'State Government'}
          </p>
        </div>
      </div>

      <p className="text-slate-600 font-medium leading-relaxed text-sm line-clamp-2 mt-1">
        {scheme.benefit_description || 'No description available.'}
      </p>

      {scheme.categories && scheme.categories.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {scheme.categories.slice(0, 3).map(cat => (
            <span key={cat} className="text-xs font-bold text-slate-600 bg-slate-100 px-2 py-1 rounded-md">
              {cat}
            </span>
          ))}
          {scheme.categories.length > 3 && (
            <span className="text-xs font-bold text-slate-500 px-2 py-1">+{scheme.categories.length - 3}</span>
          )}
        </div>
      )}

      {scheme.missing_fields && scheme.missing_fields.length > 0 && (
        <div className="flex items-center gap-2 mt-2 text-xs font-medium text-amber-700 bg-amber-50/50 p-2 rounded-lg border border-amber-100">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          <span className="truncate">
            {t('missingFields', { fields: scheme.missing_fields.slice(0, 2).join(', ') })}
          </span>
        </div>
      )}

      <div className="mt-auto pt-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-t border-slate-100">
        <div className="flex items-center gap-3 text-sm font-bold text-slate-500">
          <span className="uppercase tracking-wider text-[11px]">Match score</span>
          <div className="w-24 h-2 bg-slate-100 rounded-full overflow-hidden flex">
            <div 
              className="h-full bg-indigo-500 rounded-full" 
              style={{ width: `${displayScore}%` }}
            />
          </div>
          <span className="text-slate-900">{displayScore}%</span>
        </div>

        <div className="flex gap-3 w-full sm:w-auto">
          <Button
            variant="outline"
            className="flex-1 sm:flex-none border-slate-200 text-slate-700 hover:bg-slate-50 hover:text-slate-900 font-bold"
            onClick={(e) => {
              e.stopPropagation();
              onExplain();
            }}
          >
            <Zap className="w-4 h-4 mr-1.5 text-indigo-500" />
            {t('explain')}
          </Button>
          
          <Button
            className="flex-1 sm:flex-none bg-indigo-600 hover:bg-indigo-700 text-white font-bold shadow-sm"
            disabled={!scheme.application_url}
            onClick={(e) => {
              e.stopPropagation();
              if (scheme.application_url) window.open(scheme.application_url, '_blank');
            }}
          >
            {scheme.application_url ? t('apply') : t('applyUnavailable')}
            {scheme.application_url && <ExternalLink className="ml-1.5 w-4 h-4" />}
          </Button>
        </div>
      </div>
    </div>
  );
}