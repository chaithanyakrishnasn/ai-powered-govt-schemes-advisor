'use client';

import { useProfileStore } from '@/lib/store/profileStore';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { StateSelect } from '../fields/StateSelect';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useTranslations } from 'next-intl';
import { Gender } from '@/types/api';

export function Step1BasicInfo() {
  const t = useTranslations('profile.wizard.fields');
  const tCommon = useTranslations('common');
  const { profile, updateProfile } = useProfileStore();

  const handleAgeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    if (val === '') {
      updateProfile({ age: undefined });
    } else {
      const num = parseInt(val, 10);
      if (!isNaN(num)) updateProfile({ age: num });
    }
  };

  const isAgeInvalid = profile.age !== undefined && (profile.age < 1 || profile.age > 120);

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="age">{t('age')}</Label>
        <Input
          id="age"
          name="age"
          type="number"
          min={1}
          max={120}
          value={profile.age ?? ''}
          onChange={handleAgeChange}
          placeholder="e.g. 35"
        />
        {isAgeInvalid && <p className="text-red-500 text-sm">Age must be between 1 and 120</p>}
        <div className="text-xs text-muted-foreground"><a href="#" onClick={(e) => { e.preventDefault(); updateProfile({ age: undefined }); }} className="hover:underline">{tCommon('skip')}</a></div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="gender">{t('gender')}</Label>
        <Select value={profile.gender} onValueChange={(val) => updateProfile({ gender: val as Gender })}>
          <SelectTrigger id="gender">
            <SelectValue placeholder="Select gender" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="male">Male</SelectItem>
            <SelectItem value="female">Female</SelectItem>
            <SelectItem value="other">Other</SelectItem>
            <SelectItem value="prefer_not_to_say">Prefer not to say</SelectItem>
          </SelectContent>
        </Select>
        <div className="text-xs text-muted-foreground"><a href="#" onClick={(e) => { e.preventDefault(); updateProfile({ gender: undefined }); }} className="hover:underline">{tCommon('skip')}</a></div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="state">{t('state')}</Label>
        <StateSelect
          value={profile.state}
          onChange={(val) => updateProfile({ state: val })}
        />
        <div className="text-xs text-muted-foreground"><a href="#" onClick={(e) => { e.preventDefault(); updateProfile({ state: undefined }); }} className="hover:underline">{tCommon('skip')}</a></div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="district">{t('district')}</Label>
        <Input
          id="district"
          value={profile.district ?? ''}
          onChange={(e) => {
            const val = e.target.value;
            updateProfile({ district: val === '' ? undefined : val });
          }}
          placeholder="e.g. Mysuru"
        />
        <div className="text-xs text-muted-foreground"><a href="#" onClick={(e) => { e.preventDefault(); updateProfile({ district: undefined }); }} className="hover:underline">{tCommon('skip')}</a></div>
      </div>
    </div>
  );
}
