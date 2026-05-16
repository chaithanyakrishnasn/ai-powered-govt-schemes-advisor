'use client';

import { Input } from '@/components/ui/input';
import { Search } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { useState, useEffect } from 'react';
import { useDebounce } from 'use-debounce';

interface SearchBarProps {
  initialQuery?: string;
  onSearch: (query: string) => void;
  isLoading?: boolean;
}

export function SearchBar({ initialQuery = '', onSearch, isLoading }: SearchBarProps) {
  const t = useTranslations('results');
  const [value, setValue] = useState(initialQuery);
  const [debouncedValue] = useDebounce(value, 500);

  useEffect(() => {
    // Only trigger search if value actually changed from initial state (prevent mount re-fetch)
    if (debouncedValue !== initialQuery) {
      onSearch(debouncedValue);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedValue, onSearch]);

  return (
    <div className="relative w-full max-w-md">
      <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
        {isLoading ? (
          <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full" />
        ) : (
          <Search className="h-4 w-4 text-muted-foreground" />
        )}
      </div>
      <Input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        className="pl-10 w-full bg-background"
        placeholder={t('searchPlaceholder')}
      />
    </div>
  );
}
