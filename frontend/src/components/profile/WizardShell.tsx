'use client';

import { useState } from 'react';
import { useProfileStore } from '@/lib/store/profileStore';
import { createProfile, updateProfile as updateProfileApi } from '@/lib/api/profiles';
import { useRouter } from '@/i18n/navigation';
import { useToast } from '@/hooks/use-toast';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useTranslations } from 'next-intl';
import { Check, ArrowRight, ArrowLeft } from 'lucide-react';
import type { UserProfile } from '@/types/api';

import { Step1BasicInfo } from './steps/Step1BasicInfo';
import { Step2Economic } from './steps/Step2Economic';
import { Step3Social } from './steps/Step3Social';
import { Step4Health } from './steps/Step4Health';

const STEPS = [Step1BasicInfo, Step2Economic, Step3Social, Step4Health];

export default function WizardShell() {
  const t = useTranslations('profile.wizard');
  const tCommon = useTranslations('common');
  const { currentStep, totalSteps, profile, profileId, nextStep, prevStep, setProfileId } = useProfileStore();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const router = useRouter();
  const { toast } = useToast();

  const CurrentStepComponent = STEPS[currentStep];

  const handleNext = () => {
    nextStep();
  };

  const handleSubmit = async () => {
    try {
      setIsSubmitting(true);
      let newProfileId = profileId;

      const cleanProfile = (p: Partial<UserProfile>) => {
        const allowedKeys = [
          'age', 'gender', 'state', 'district', 'annual_income',
          'occupation', 'employment_status', 'caste_category',
          'religion', 'marital_status', 'is_farmer',
          'land_holding_acres', 'education_level', 'family_size',
          'has_disability', 'disability_percentage'
        ];
        return Object.fromEntries(
          Object.entries(p).filter(([k, v]) => {
            if (!allowedKeys.includes(k)) return false;
            if (v === null || v === undefined) return false;
            if (v === '') return false;
            if (typeof v === 'number' && isNaN(v)) return false;
            return true;
          })
        );
      };
      
      const cleaned = cleanProfile(profile);

      if (profileId) {
        await updateProfileApi(profileId, cleaned as Partial<UserProfile>);
      } else {
        const response = await createProfile(cleaned as UserProfile);
        newProfileId = response.profile_id;
        setProfileId(newProfileId);
      }

      router.push(`/results?profile_id=${newProfileId}`);
    } catch (error) {
      console.error('Failed to save profile:', error);
      toast({
        variant: 'destructive',
        title: 'Error',
        description: tCommon('error'),
      });
      setIsSubmitting(false);
    }
  };

  const stepTitles = [
    { title: 'Basic Info', label: t('steps.basic') },
    { title: 'Economic', label: t('steps.economic') },
    { title: 'Social', label: t('steps.social') },
    { title: 'Health', label: t('steps.health') }
  ];

  return (
    <div className="max-w-3xl mx-auto space-y-10 py-8">
      <div className="space-y-3 text-center">
        <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">{useTranslations('profile')('title')}</h1>
        <p className="text-slate-500 max-w-xl mx-auto text-lg font-medium">{useTranslations('profile')('subtitle')}</p>
      </div>

      {/* Premium Step Indicator */}
      <div className="relative">
        <div className="absolute top-1/2 left-0 w-full h-0.5 bg-slate-100 -translate-y-1/2 z-0" />
        <div 
          className="absolute top-1/2 left-0 h-0.5 bg-indigo-600 -translate-y-1/2 z-0 transition-all duration-500 ease-in-out"
          style={{ width: `${(currentStep / (totalSteps - 1)) * 100}%` }}
        />
        
        <div className="relative z-10 flex justify-between">
          {stepTitles.map((step, index) => {
            const isCompleted = index < currentStep;
            const isActive = index === currentStep;
            
            return (
              <div key={index} className="flex flex-col items-center gap-3">
                <div 
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-bold transition-all duration-300 shadow-sm ring-4 ring-white
                    ${isCompleted ? 'bg-indigo-600 text-white' : 
                      isActive ? 'bg-indigo-600 text-white ring-indigo-50' : 
                      'bg-white text-slate-400 border-2 border-slate-200'}`}
                >
                  {isCompleted ? <Check className="w-5 h-5" /> : index + 1}
                </div>
                <div className="flex flex-col items-center">
                  <span className={`text-sm font-bold ${isActive || isCompleted ? 'text-slate-900' : 'text-slate-400'}`}>
                    {step.title}
                  </span>
                  <span className="text-[11px] font-bold text-slate-400 hidden sm:block">
                    {isCompleted ? '(completed ✓)' : isActive ? '(active)' : '(upcoming)'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <Card className="border-slate-200 shadow-sm overflow-hidden bg-white/50 rounded-xl">
        <div className="border-b border-slate-100 bg-slate-50/50 px-8 py-5">
          <h2 className="text-xl font-extrabold text-slate-900">
            Step {currentStep + 1} of {totalSteps} · {stepTitles[currentStep].title} Details
          </h2>
        </div>
        <CardContent className="p-8">
          <CurrentStepComponent />
        </CardContent>
      </Card>

      <div className="flex justify-between items-center px-2">
        <Button
          variant="ghost"
          onClick={prevStep}
          disabled={currentStep === 0 || isSubmitting}
          className={`text-slate-500 hover:text-slate-900 font-bold px-6 ${currentStep === 0 ? 'invisible' : ''}`}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          {t('nav.back')}
        </Button>

        {currentStep === totalSteps - 1 ? (
          <Button 
            onClick={handleSubmit} 
            disabled={isSubmitting}
            size="lg"
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-8 font-bold rounded-full shadow-sm hover:shadow transition-all h-12"
          >
            {isSubmitting ? (
              <span className="flex items-center space-x-2">
                <span className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></span>
                <span>{t('nav.submitting')}</span>
              </span>
            ) : (
              <span className="flex items-center">
                {t('nav.submit')} <Check className="w-5 h-5 ml-2" />
              </span>
            )}
          </Button>
        ) : (
          <Button 
            onClick={handleNext}
            size="lg"
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-8 font-bold rounded-full shadow-sm hover:shadow transition-all h-12"
          >
            {t('nav.next')} <ArrowRight className="w-5 h-5 ml-2" />
          </Button>
        )}
      </div>
    </div>
  );
}