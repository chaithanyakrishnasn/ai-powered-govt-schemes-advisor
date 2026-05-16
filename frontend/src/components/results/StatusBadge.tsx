'use client';

import { useTranslations } from 'next-intl';
import { Badge } from '@/components/ui/badge';
import { EligibilityStatus } from '@/types/api';
import { CheckCircle2, HelpCircle, XCircle, AlertCircle } from 'lucide-react';

interface StatusBadgeProps {
  status: EligibilityStatus;
  size?: 'sm' | 'md';
}

export function StatusBadge({ status, size = 'sm' }: StatusBadgeProps) {
  const t = useTranslations('results');

  const config = {
    eligible: {
      label: t('eligible'),
      color: 'bg-green-100 text-green-800 hover:bg-green-100 border-green-200',
      icon: CheckCircle2,
    },
    likely_eligible: {
      label: t('likelyEligible'),
      color: 'bg-amber-100 text-amber-800 hover:bg-amber-100 border-amber-200',
      icon: AlertCircle,
    },
    need_more_info: {
      label: t('needMoreInfo'),
      color: 'bg-slate-100 text-slate-800 hover:bg-slate-100 border-slate-200',
      icon: HelpCircle,
    },
    not_eligible: {
      label: t('notEligible'),
      color: 'bg-red-100 text-red-800 hover:bg-red-100 border-red-200',
      icon: XCircle,
    },
  };

  const { label, color, icon: Icon } = config[status];

  return (
    <Badge variant="outline" className={`${color} flex items-center gap-1 ${size === 'md' ? 'text-sm py-1 px-3' : 'text-xs'}`}>
      <Icon className={size === 'md' ? 'w-4 h-4' : 'w-3 h-3'} />
      {label}
    </Badge>
  );
}
