'use client';

import { useProfileStore } from '@/lib/store/profileStore';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { IncomeInput } from '../fields/IncomeInput';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useTranslations } from 'next-intl';
import { EmploymentStatus } from '@/types/api';

const OCCUPATION_SUGGESTIONS = [
  "Farmer", "Student", "Self-employed", "Government Employee", 
  "Private Employee", "Daily Wage Worker", "Homemaker", "Retired", "Unemployed"
];

export function Step2Economic() {
  const t = useTranslations('profile.wizard.fields');
  const tCommon = useTranslations('common');
  const { profile, updateProfile } = useProfileStore();

  const handleLandChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    if (val === '') {
      updateProfile({ land_holding_acres: undefined });
    } else {
      const num = parseFloat(val);
      if (!isNaN(num)) updateProfile({ land_holding_acres: num });
    }
  };

  const isIncomeInvalid = profile.annual_income !== undefined && profile.annual_income < 0;
  const isLandInvalid = profile.land_holding_acres !== undefined && profile.land_holding_acres < 0;

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="annual_income">{t('annualIncome')}</Label>
        <IncomeInput
          id="annual_income"
          value={profile.annual_income}
          onChange={(val) => updateProfile({ annual_income: val })}
          placeholder="e.g. 360000"
        />
        {isIncomeInvalid && <p className="text-red-500 text-sm">Income must be positive</p>}
        <div className="text-xs text-muted-foreground"><a href="#" onClick={(e) => { e.preventDefault(); updateProfile({ annual_income: undefined }); }} className="hover:underline">{tCommon('skip')}</a></div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="occupation">{t('occupation')}</Label>
        <Input
          id="occupation"
          list="occupation-list"
          value={profile.occupation ?? ''}
          onChange={(e) => {
            const val = e.target.value;
            updateProfile({ occupation: val === '' ? undefined : val });
          }}
          placeholder="e.g. Student"
        />
        <datalist id="occupation-list">
          {OCCUPATION_SUGGESTIONS.map(occ => (
            <option key={occ} value={occ} />
          ))}
        </datalist>
        <div className="text-xs text-muted-foreground"><a href="#" onClick={(e) => { e.preventDefault(); updateProfile({ occupation: undefined }); }} className="hover:underline">{tCommon('skip')}</a></div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="employment_status">{t('employmentStatus')}</Label>
        <Select value={profile.employment_status} onValueChange={(val) => updateProfile({ employment_status: val as EmploymentStatus })}>
          <SelectTrigger id="employment_status">
            <SelectValue placeholder="Select status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="employed">Employed</SelectItem>
            <SelectItem value="unemployed">Unemployed</SelectItem>
            <SelectItem value="self_employed">Self-employed</SelectItem>
            <SelectItem value="student">Student</SelectItem>
            <SelectItem value="retired">Retired</SelectItem>
          </SelectContent>
        </Select>
        <div className="text-xs text-muted-foreground"><a href="#" onClick={(e) => { e.preventDefault(); updateProfile({ employment_status: undefined }); }} className="hover:underline">{tCommon('skip')}</a></div>
      </div>

      <div className="flex items-center space-x-2">
        <Switch
          id="is_farmer"
          checked={profile.is_farmer ?? false}
          onCheckedChange={(val) => {
            updateProfile({ is_farmer: val });
            if (!val) {
              updateProfile({ land_holding_acres: undefined });
            }
          }}
        />
        <Label htmlFor="is_farmer">{t('isFarmer')}</Label>
      </div>

      {profile.is_farmer && (
        <div className="space-y-2 animate-in fade-in slide-in-from-top-2 duration-200">
          <Label htmlFor="land_holding_acres">{t('landHolding')}</Label>
          <Input
            id="land_holding_acres"
            name="land_holding_acres"
            type="number"
            min={0}
            step="0.1"
            value={profile.land_holding_acres ?? ''}
            onChange={handleLandChange}
            placeholder="e.g. 2.5"
          />
          {isLandInvalid && <p className="text-red-500 text-sm">Land holding must be positive</p>}
        </div>
      )}
    </div>
  );
}
