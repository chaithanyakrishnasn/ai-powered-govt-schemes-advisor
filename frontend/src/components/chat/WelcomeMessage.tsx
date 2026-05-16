'use client';

import { useTranslations } from 'next-intl';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Lightbulb, UserCircle } from 'lucide-react';
import { useProfileStore } from '@/lib/store/profileStore';
import { Link } from '@/i18n/navigation';

interface WelcomeMessageProps {
  onSuggest: (query: string) => void;
}

export function WelcomeMessage({ onSuggest }: WelcomeMessageProps) {
  const t = useTranslations('chat');
  const { profile } = useProfileStore();

  const hasProfile = Object.keys(profile).length > 0;

  const suggestions = [
    t('suggestions.farming'),
    t('suggestions.scholarship'),
    t('suggestions.disability'),
    t('suggestions.pmkisan')
  ];

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 animate-in fade-in zoom-in duration-500">
      <Card className="w-full max-w-2xl text-center bg-card shadow-md">
        <CardHeader>
          <CardTitle className="text-2xl font-bold flex items-center justify-center gap-3">
            <span className="text-3xl">🏛</span> {t('welcome')}
          </CardTitle>
          <CardDescription className="text-base mt-2">
            {t('welcomeSubtitle')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-8">
          
          <div className="bg-muted/50 rounded-lg p-4 border flex items-center justify-center gap-3">
            {hasProfile ? (
              <>
                <UserCircle className="w-5 h-5 text-green-600" />
                <span className="text-sm font-medium">
                  {t('profileLoaded', { state: profile.state || 'India' })}
                </span>
                <span className="text-sm text-muted-foreground ml-2">
                  Ready for personalized results!
                </span>
              </>
            ) : (
              <>
                <UserCircle className="w-5 h-5 text-amber-600" />
                <span className="text-sm font-medium text-amber-800">
                  {t('noProfile')}
                </span>
                <Link href="/profile" className="ml-2">
                  <Button variant="link" size="sm" className="h-auto p-0 text-primary">
                    {t('completeProfile')} →
                  </Button>
                </Link>
              </>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
            {suggestions.map((query, i) => (
              <Button
                key={i}
                variant="outline"
                className="h-auto py-3 px-4 justify-start text-left font-normal bg-background hover:bg-muted whitespace-normal break-words"
                onClick={() => onSuggest(query)}
              >
                <Lightbulb className="w-4 h-4 text-primary shrink-0 mr-3 mt-0.5" />
                <span>{query}</span>
              </Button>
            ))}
          </div>

        </CardContent>
      </Card>
    </div>
  );
}
