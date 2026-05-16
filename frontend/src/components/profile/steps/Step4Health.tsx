'use client';

import { useEffect } from 'react';
import { useProfileStore } from '@/lib/store/profileStore';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useTranslations, useLocale } from 'next-intl';

export function Step4Health() {
  const t = useTranslations('profile.wizard.fields');
  const tSummary = useTranslations('profile.wizard.summary');
  const locale = useLocale();
  const { profile, updateProfile } = useProfileStore();

  useEffect(() => {
    if (!profile.preferred_language) {
      updateProfile({ preferred_language: locale });
    }
  }, [locale, profile.preferred_language, updateProfile]);

  const handleDisabilityChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    if (val === '') {
      updateProfile({ disability_percentage: undefined });
    } else {
      const num = parseInt(val, 10);
      if (!isNaN(num)) updateProfile({ disability_percentage: num });
    }
  };

  const isDisabilityInvalid = profile.disability_percentage !== undefined && (profile.disability_percentage < 0 || profile.disability_percentage > 100);

  const formatIncome = (val?: number) => {
    if (val === undefined) return tSummary('notProvided');
    if (val >= 100000) return `₹${(val / 100000).toFixed(2)}L/year`;
    if (val >= 1000) return `₹${(val / 1000).toFixed(2)}K/year`;
    return `₹${val}/year`;
  };

  return (
    <div className="space-y-8">
      <div className="space-y-6">
        <div className="flex items-center space-x-2">
          <Switch
            id="has_disability"
            name="has_disability"
            checked={profile.has_disability ?? false}
            onCheckedChange={(val) => {
              updateProfile({ has_disability: val });
              if (!val) {
                updateProfile({ disability_percentage: undefined });
              }
            }}
          />
          <Label htmlFor="has_disability">{t('hasDisability')}</Label>
        </div>

        {profile.has_disability && (
          <div className="space-y-2 animate-in fade-in slide-in-from-top-2 duration-200">
            <Label htmlFor="disability_percentage">{t('disabilityPercentage')}</Label>
            <Input
              id="disability_percentage"
              type="number"
              min={0}
              max={100}
              value={profile.disability_percentage ?? ''}
              onChange={handleDisabilityChange}
              placeholder="e.g. 40"
            />
            <p className="text-sm text-muted-foreground">As per disability certificate</p>
            {isDisabilityInvalid && <p className="text-red-500 text-sm">Percentage must be between 0 and 100</p>}
          </div>
        )}

        <div className="space-y-2">
          <Label htmlFor="preferred_language">{t('preferredLanguage')}</Label>
          <Select value={profile.preferred_language} onValueChange={(val) => updateProfile({ preferred_language: val })}>
            <SelectTrigger id="preferred_language">
              <SelectValue placeholder="Select language" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="en">English</SelectItem>
              <SelectItem value="hi">हिन्दी</SelectItem>
              <SelectItem value="kn">ಕನ್ನಡ</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">{tSummary('title')}</CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <div><span className="font-semibold text-muted-foreground">{t('age')}:</span> {profile.age ?? tSummary('notProvided')}</div>
            <div><span className="font-semibold text-muted-foreground">{t('gender')}:</span> {profile.gender ?? tSummary('notProvided')}</div>
            <div><span className="font-semibold text-muted-foreground">{t('state')}:</span> {profile.state ?? tSummary('notProvided')}</div>
            <div><span className="font-semibold text-muted-foreground">{t('district')}:</span> {profile.district ?? tSummary('notProvided')}</div>
            <div><span className="font-semibold text-muted-foreground">{t('annualIncome')}:</span> {formatIncome(profile.annual_income)}</div>
            <div><span className="font-semibold text-muted-foreground">{t('occupation')}:</span> {profile.occupation ?? tSummary('notProvided')}</div>
            <div><span className="font-semibold text-muted-foreground">{t('isFarmer')}:</span> {profile.is_farmer ? `Yes (${profile.land_holding_acres ?? 0} acres)` : 'No'}</div>
            <div><span className="font-semibold text-muted-foreground">{t('casteCategory')}:</span> {profile.caste_category ?? tSummary('notProvided')}</div>
            <div><span className="font-semibold text-muted-foreground">{t('educationLevel')}:</span> {profile.education_level ?? tSummary('notProvided')}</div>
            <div><span className="font-semibold text-muted-foreground">{t('hasDisability')}:</span> {profile.has_disability ? `Yes (${profile.disability_percentage ?? 0}%)` : 'No'}</div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
