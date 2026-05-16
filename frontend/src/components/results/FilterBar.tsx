'use client';

import { useTranslations } from 'next-intl';
import { Badge } from '@/components/ui/badge';
import { EligibilityStatus } from '@/types/api';

export type FilterState = {
  status?: EligibilityStatus | 'all';
  level?: string | 'all';
};

interface FilterBarProps {
  activeFilters: FilterState;
  onChange: (filters: FilterState) => void;
}

export function FilterBar({ activeFilters, onChange }: FilterBarProps) {
  const t = useTranslations('results.filters');

  const statusFilters: Array<{ value: EligibilityStatus | 'all'; label: string }> = [
    { value: 'all', label: t('all') },
    { value: 'eligible', label: t('eligible') },
    { value: 'likely_eligible', label: t('likelyEligible') },
  ];

  const levelFilters = [
    { value: 'all', label: t('all') },
    { value: 'Central', label: t('central') },
    { value: 'State', label: t('state') },
  ];

  return (
    <div className="flex flex-wrap items-center gap-4 text-sm">
      <div className="flex items-center gap-2">
        <span className="text-muted-foreground font-medium">{useTranslations('results')('status')}</span>
        <div className="flex flex-wrap gap-2">
          {statusFilters.map((filter) => (
            <Badge
              key={filter.value}
              variant={activeFilters.status === filter.value || (!activeFilters.status && filter.value === 'all') ? 'default' : 'outline'}
              className="cursor-pointer"
              onClick={() => onChange({ ...activeFilters, status: filter.value })}
            >
              {filter.label}
            </Badge>
          ))}
        </div>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-muted-foreground font-medium">{useTranslations('results')('level')}</span>
        <div className="flex flex-wrap gap-2">
          {levelFilters.map((filter) => (
            <Badge
              key={filter.value}
              variant={activeFilters.level === filter.value || (!activeFilters.level && filter.value === 'all') ? 'default' : 'outline'}
              className="cursor-pointer"
              onClick={() => onChange({ ...activeFilters, level: filter.value })}
            >
              {filter.label}
            </Badge>
          ))}
        </div>
      </div>
    </div>
  );
}
