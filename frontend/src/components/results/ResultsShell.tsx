'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { useTranslations } from 'next-intl';
import { streamMatch, runMatch } from '@/lib/api/match';
import { SchemeResultItem, SchemeExplanation, MatchResponse } from '@/types/api';
import { SearchBar } from './SearchBar';
import { FilterBar, FilterState } from './FilterBar';
import { ResultsSummary } from './ResultsSummary';
import { SchemeCard } from './SchemeCard';
import { SchemeCardSkeleton } from './SchemeCardSkeleton';
import { ExplanationPanel } from './ExplanationPanel';
import { EmptyState } from './EmptyState';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { useToast } from '@/hooks/use-toast';
import { VisuallyHidden } from '@radix-ui/react-visually-hidden';

export default function ResultsShell({ profileId }: { profileId: string }) {
  const t = useTranslations('results');
  const { toast } = useToast();

  const [query, setQuery] = useState('');
  const [isSearching, setIsSearching] = useState(true);
  const [results, setResults] = useState<SchemeResultItem[]>([]);
  const [explanations, setExplanations] = useState<Record<string, SchemeExplanation>>({});
  const [stats, setStats] = useState<MatchResponse['pipeline_stats'] | null>(null);
  const [filters, setFilters] = useState<FilterState>({ status: 'all', level: 'all' });
  const [showIneligible, setShowIneligible] = useState(false);

  const [selectedScheme, setSelectedScheme] = useState<SchemeResultItem | null>(null);
  const [isExplaining, setIsExplaining] = useState(false);
  const [isMobileSheetOpen, setIsMobileSheetOpen] = useState(false);

  const eventSourceRef = useRef<EventSource | null>(null);

  // Initial load & search execution
  const executeSearch = useCallback(async (searchQuery: string) => {
    setIsSearching(true);
    try {
      const response = await runMatch({ profile_id: profileId, query: searchQuery, explain: false });
      setResults(response.results);
      setStats(response.pipeline_stats);
      // Optional: prepopulate explanations if returned (they shouldn't be for explain=false)
      if (response.explanations) {
        const explMap: Record<string, SchemeExplanation> = {};
        response.explanations.forEach(ex => explMap[ex.slug] = ex);
        setExplanations(prev => ({ ...prev, ...explMap }));
      }
    } catch (err) {
      console.error('Search failed:', err);
      toast({ variant: 'destructive', title: 'Error', description: 'Failed to fetch schemes.' });
    } finally {
      setIsSearching(false);
    }
  }, [profileId, toast]);

  // Execute on mount / when query changes
  useEffect(() => {
    executeSearch(query);
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [query, executeSearch]);

  const handleExplain = (scheme: SchemeResultItem) => {
    setSelectedScheme(scheme);
    setIsMobileSheetOpen(true);

    // If already explained, do nothing
    if (explanations[scheme.slug]) return;

    // Use SSE to fetch explanation
    setIsExplaining(true);
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    const source = streamMatch({ profile_id: profileId, query: scheme.name, explain: true });
    eventSourceRef.current = source;

    source.addEventListener('stage3_explanation', (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.explanation && data.explanation.slug === scheme.slug) {
          setExplanations(prev => ({ ...prev, [scheme.slug]: data.explanation }));
          setIsExplaining(false);
        }
      } catch (err) {
        console.error('Failed to parse explanation', err);
      }
    });

    source.addEventListener('error', (e) => {
      console.error('SSE Error', e);
      source.close();
      setIsExplaining(false);
    });

    source.addEventListener('done', () => {
      source.close();
      setIsExplaining(false);
    });
  };

  // Filtering logic
  const filteredResults = results.filter(r => {
    if (filters.status !== 'all' && r.status !== filters.status) return false;
    if (filters.level !== 'all' && r.level !== filters.level) return false;
    if (!showIneligible && r.status === 'not_eligible') return false;
    return true;
  });

  const ineligibleCount = results.filter(r => r.status === 'not_eligible').length;
  const eligibleCount = results.filter(r => r.status === 'eligible').length;
  const likelyCount = results.filter(r => r.status === 'likely_eligible').length;

  return (
    <div className="flex flex-col h-[calc(100vh-80px)] gap-6">
      <div className="flex flex-col gap-4 shrink-0">
        <ResultsSummary 
          total={results.length} 
          eligibleCount={eligibleCount} 
          likelyCount={likelyCount} 
          latencyMs={stats?.total_latency_ms} 
        />
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <SearchBar initialQuery={query} onSearch={setQuery} isLoading={isSearching} />
          <FilterBar activeFilters={filters} onChange={setFilters} />
        </div>
      </div>

      <div className="flex-1 flex gap-6 overflow-hidden pb-4">
        {/* Left Column: Scheme List */}
        <div className="w-full lg:w-3/5 overflow-y-auto pr-2 custom-scrollbar flex flex-col gap-4">
          {isSearching ? (
            <SchemeCardSkeleton />
          ) : results.length === 0 ? (
            <EmptyState />
          ) : filteredResults.length === 0 ? (
            <div className="p-8 text-center text-muted-foreground border rounded-lg">
              No schemes match the current filters.
            </div>
          ) : (
            <>
              {filteredResults.map(scheme => (
                <SchemeCard 
                  key={scheme.slug} 
                  scheme={scheme} 
                  isSelected={selectedScheme?.slug === scheme.slug}
                  onSelect={() => setSelectedScheme(scheme)}
                  onExplain={() => handleExplain(scheme)}
                />
              ))}
              
              {!showIneligible && ineligibleCount > 0 && filters.status === 'all' && (
                <Button 
                  variant="ghost" 
                  className="w-full mt-2" 
                  onClick={() => setShowIneligible(true)}
                >
                  {t('showIneligible', { count: ineligibleCount })}
                </Button>
              )}
              {showIneligible && ineligibleCount > 0 && filters.status === 'all' && (
                <Button 
                  variant="ghost" 
                  className="w-full mt-2" 
                  onClick={() => setShowIneligible(false)}
                >
                  {t('hideIneligible')}
                </Button>
              )}
            </>
          )}
        </div>

        {/* Right Column: Desktop Explanation Panel */}
        <div className="hidden lg:block lg:w-2/5 border rounded-lg bg-card overflow-hidden sticky top-0 h-full">
          <ExplanationPanel 
            scheme={selectedScheme}
            explanation={selectedScheme ? explanations[selectedScheme.slug] || null : null}
            isLoading={isExplaining}
            onApply={(url) => window.open(url, '_blank')}
            onViewDetails={(slug) => window.open(`/schemes/${slug}`, '_blank')}
          />
        </div>
      </div>

      {/* Mobile Sheet for Explanation Panel */}
      <Sheet open={isMobileSheetOpen} onOpenChange={setIsMobileSheetOpen}>
        <SheetContent side="bottom" className="h-[85vh] p-0 sm:max-w-none rounded-t-xl overflow-hidden">
          <VisuallyHidden asChild>
            <SheetTitle>Scheme Details</SheetTitle>
          </VisuallyHidden>
          <VisuallyHidden asChild>
            <SheetDescription>
              An explanation and details for the selected scheme.
            </SheetDescription>
          </VisuallyHidden>
          <ExplanationPanel 
            scheme={selectedScheme}
            explanation={selectedScheme ? explanations[selectedScheme.slug] || null : null}
            isLoading={isExplaining}
            onApply={(url) => window.open(url, '_blank')}
            onViewDetails={(slug) => window.open(`/schemes/${slug}`, '_blank')}
          />
        </SheetContent>
      </Sheet>
    </div>
  );
}
