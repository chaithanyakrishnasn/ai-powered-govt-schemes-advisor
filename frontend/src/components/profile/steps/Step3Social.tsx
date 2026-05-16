'use client';

import { useProfileStore } from '@/lib/store/profileStore';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useTranslations } from 'next-intl';
import { CasteCategory, MaritalStatus, EducationLevel } from '@/types/api';

export function Step3Social() {
  const t = useTranslations('profile.wizard.fields');
  const tCommon = useTranslations('common');
  const { profile, updateProfile } = useProfileStore();

  const handleFamilySizeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    if (val === '') {
      updateProfile({ family_size: undefined });
    } else {
      const num = parseInt(val, 10);
      if (!isNaN(num)) updateProfile({ family_size: num });
    }
  };

  const isFamilySizeInvalid = profile.family_size !== undefined && (profile.family_size < 1 || profile.family_size > 20);

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="caste_category">{t('casteCategory')}</Label>
        <Select value={profile.caste_category} onValueChange={(val) => updateProfile({ caste_category: val as CasteCategory })}>
          <SelectTrigger id="caste_category">
            <SelectValue placeholder="Select caste category" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="GEN">General (GEN)</SelectItem>
            <SelectItem value="OBC">OBC</SelectItem>
            <SelectItem value="SC">SC</SelectItem>
            <SelectItem value="ST">ST</SelectItem>
            <SelectItem value="EWS">EWS</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-sm text-muted-foreground">Used to match reservation-based schemes</p>
        <div className="text-xs text-muted-foreground"><a href="#" onClick={(e) => { e.preventDefault(); updateProfile({ caste_category: undefined }); }} className="hover:underline">{tCommon('skip')}</a></div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="religion">{t('religion')}</Label>
        <Select value={profile.religion} onValueChange={(val) => updateProfile({ religion: val })}>
          <SelectTrigger id="religion">
            <SelectValue placeholder="Select religion" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="Hindu">Hindu</SelectItem>
            <SelectItem value="Muslim">Muslim</SelectItem>
            <SelectItem value="Christian">Christian</SelectItem>
            <SelectItem value="Sikh">Sikh</SelectItem>
            <SelectItem value="Buddhist">Buddhist</SelectItem>
            <SelectItem value="Jain">Jain</SelectItem>
            <SelectItem value="Parsi">Parsi</SelectItem>
            <SelectItem value="Other">Other</SelectItem>
            <SelectItem value="Prefer not to say">Prefer not to say</SelectItem>
          </SelectContent>
        </Select>
        <div className="text-xs text-muted-foreground"><a href="#" onClick={(e) => { e.preventDefault(); updateProfile({ religion: undefined }); }} className="hover:underline">{tCommon('skip')}</a></div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="marital_status">{t('maritalStatus')}</Label>
        <Select value={profile.marital_status} onValueChange={(val) => updateProfile({ marital_status: val as MaritalStatus })}>
          <SelectTrigger id="marital_status">
            <SelectValue placeholder="Select marital status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="single">Single</SelectItem>
            <SelectItem value="married">Married</SelectItem>
            <SelectItem value="widowed">Widowed</SelectItem>
            <SelectItem value="divorced">Divorced</SelectItem>
          </SelectContent>
        </Select>
        <div className="text-xs text-muted-foreground"><a href="#" onClick={(e) => { e.preventDefault(); updateProfile({ marital_status: undefined }); }} className="hover:underline">{tCommon('skip')}</a></div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="education_level">{t('educationLevel')}</Label>
        <Select value={profile.education_level} onValueChange={(val) => updateProfile({ education_level: val as EducationLevel })}>
          <SelectTrigger id="education_level">
            <SelectValue placeholder="Select education level" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="none">None</SelectItem>
            <SelectItem value="primary">Primary</SelectItem>
            <SelectItem value="secondary">Secondary</SelectItem>
            <SelectItem value="higher_secondary">Higher Secondary</SelectItem>
            <SelectItem value="diploma">Diploma</SelectItem>
            <SelectItem value="graduate">Graduate</SelectItem>
            <SelectItem value="postgraduate">Postgraduate</SelectItem>
            <SelectItem value="masters_degree">Masters Degree</SelectItem>
            <SelectItem value="phd">PhD</SelectItem>
          </SelectContent>
        </Select>
        <div className="text-xs text-muted-foreground"><a href="#" onClick={(e) => { e.preventDefault(); updateProfile({ education_level: undefined }); }} className="hover:underline">{tCommon('skip')}</a></div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="family_size">{t('familySize')}</Label>
        <Input
          id="family_size"
          name="family_size"
          type="number"
          min={1}
          max={20}
          value={profile.family_size ?? ''}
          onChange={handleFamilySizeChange}
          placeholder="e.g. 4"
        />
        {isFamilySizeInvalid && <p className="text-red-500 text-sm">Family size must be between 1 and 20</p>}
        <div className="text-xs text-muted-foreground"><a href="#" onClick={(e) => { e.preventDefault(); updateProfile({ family_size: undefined }); }} className="hover:underline">{tCommon('skip')}</a></div>
      </div>
    </div>
  );
}
