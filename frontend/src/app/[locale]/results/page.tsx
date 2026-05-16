'use client';

import { useSearchParams } from 'next/navigation';
import { useRouter } from '@/i18n/navigation';
import { useEffect } from 'react';
import ResultsShell from '@/components/results/ResultsShell';

export default function ResultsPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const profileId = searchParams.get('profile_id');

  useEffect(() => {
    if (!profileId) {
      router.push('/profile');
    }
  }, [profileId, router]);

  if (!profileId) {
    return null; // redirecting
  }

  return (
    <div className="container mx-auto py-8 px-4 max-w-6xl">
      <ResultsShell profileId={profileId} />
    </div>
  );
}
