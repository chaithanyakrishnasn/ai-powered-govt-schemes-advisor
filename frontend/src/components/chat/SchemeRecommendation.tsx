'use client';

import { useTranslations } from 'next-intl';
import { SchemeResultItem, SchemeExplanation } from '@/types/api';
import { StatusBadge } from '@/components/results/StatusBadge';
import { Button } from '@/components/ui/button';
import { ExternalLink, ArrowRight, CheckCircle2 } from 'lucide-react';
import { Link } from '@/i18n/navigation';

interface SchemeRecommendationProps {
  scheme: SchemeResultItem;
  explanation?: SchemeExplanation;
}

export function SchemeRecommendation({ scheme, explanation }: SchemeRecommendationProps) {
  const t = useTranslations('results');

  const borderColors = {
    eligible: 'border-l-4 border-l-green-500',
    likely_eligible: 'border-l-4 border-l-amber-500',
    need_more_info: 'border-l-4 border-l-slate-400',
    not_eligible: 'border-l-4 border-l-red-500 opacity-70',
  };

  const bgColors = {
    eligible: 'bg-green-50/30',
    likely_eligible: 'bg-amber-50/30',
    need_more_info: 'bg-slate-50/30',
    not_eligible: 'bg-red-50/30',
  };

  return (
    <div className={`relative border rounded-lg p-4 flex flex-col gap-3 my-3 shadow-sm
      ${borderColors[scheme.status]} ${bgColors[scheme.status]}`}
    >
      <div className="flex justify-between items-start gap-4">
        <div className="flex flex-col gap-1.5">
          <StatusBadge status={scheme.status} />
          <h4 className="font-semibold text-base leading-tight">{scheme.name}</h4>
        </div>
      </div>

      <div className="text-xs text-muted-foreground flex flex-wrap items-center gap-x-2 gap-y-1 mt-1">
        <span>{scheme.benefit_type === 'cash' ? 'Financial' : scheme.benefit_type || 'Assistance'}</span>
        <span>•</span>
        <span>{scheme.categories?.[0] || 'General'}</span>
        <span>•</span>
        <span className="font-medium">{scheme.level === 'Central' ? 'Central' : scheme.state || 'State'}</span>
      </div>

      {explanation ? (
        <div className="mt-2 space-y-3 animate-in fade-in duration-500">
          <p className="text-sm italic text-muted-foreground border-l-2 border-primary/20 pl-3">
            &quot;{explanation.explanation}&quot;
          </p>
          
          {explanation.key_benefits && explanation.key_benefits.length > 0 && (
            <ul className="space-y-1">
              {explanation.key_benefits.slice(0, 2).map((benefit, i) => (
                <li key={i} className="text-sm flex items-start gap-2 text-foreground">
                  <CheckCircle2 className="w-3.5 h-3.5 text-green-500 mt-0.5 shrink-0" />
                  <span>{benefit}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : (
         <p className="text-sm text-muted-foreground line-clamp-2 mt-2">
            {scheme.benefit_description || 'Loading scheme details...'}
         </p>
      )}

      <div className="mt-2 pt-3 flex flex-wrap items-center justify-end gap-3 border-t border-border/50">
        <Link href={`/results?profile_id=current`}>
           <Button variant="ghost" size="sm" className="h-8 text-xs">
             See Full Match <ArrowRight className="w-3 h-3 ml-1.5" />
           </Button>
        </Link>
        <Button
          variant="default"
          size="sm"
          className="h-8 text-xs"
          disabled={!scheme.application_url}
          onClick={() => {
            if (scheme.application_url) window.open(scheme.application_url, '_blank');
          }}
        >
          {scheme.application_url ? t('apply') : t('applyUnavailable')}
          {scheme.application_url && <ExternalLink className="ml-1.5 w-3 h-3" />}
        </Button>
      </div>
    </div>
  );
}
