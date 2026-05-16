'use client';

import { useTranslations } from 'next-intl';
import { SearchX } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Link } from '@/i18n/navigation';

export function EmptyState() {
  const t = useTranslations('results');

  return (
    <div className="flex flex-col items-center justify-center p-12 text-center border rounded-lg bg-muted/20">
      <SearchX className="w-12 h-12 text-muted-foreground mb-4 opacity-50" />
      <h3 className="text-xl font-medium mb-2">{t('noResults')}</h3>
      <p className="text-muted-foreground mb-6 max-w-sm">
        {t('noResultsHint')}
      </p>
      <Link href="/profile">
        <Button variant="outline">{t('editProfile')}</Button>
      </Link>
    </div>
  );
}
