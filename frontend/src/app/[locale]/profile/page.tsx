'use client';
import { useEffect } from 'react';
import { useSearchParams } from 'next/navigation';
import { useProfileStore } from '@/lib/store/profileStore';
import WizardShell from '@/components/profile/WizardShell';

export default function ProfilePage() {
  const searchParams = useSearchParams();
  const reset = useProfileStore(state => state.reset);
  const fresh = searchParams.get('fresh');

  useEffect(() => {
    if (fresh === 'true') {
      reset();
    }
  }, [fresh, reset]);

  return (
    <div className="container mx-auto max-w-2xl py-8 px-4">
      <WizardShell />
    </div>
  );
}
