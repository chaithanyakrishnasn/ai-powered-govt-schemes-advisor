'use client';

import { useLocale } from 'next-intl';
import { usePathname, useRouter } from '@/i18n/navigation';
import { cn } from '@/lib/utils';

export default function LanguageSwitcher() {
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();

  const handleLanguageChange = (newLocale: string) => {
    router.replace(pathname, { locale: newLocale as 'en' | 'hi' | 'kn' });
  };

  const languages = [
    { code: 'en', label: 'EN' },
    { code: 'hi', label: 'हिं' },
    { code: 'kn', label: 'ಕನ್ನ' },
  ];

  return (
    <div className="inline-flex items-center rounded-full border border-slate-200 bg-slate-50 p-1">
      {languages.map((lang) => {
        const isActive = locale === lang.code;
        return (
          <button
            key={lang.code}
            onClick={() => handleLanguageChange(lang.code)}
            className={cn(
              "px-3 py-1 text-xs font-bold rounded-full transition-all duration-200 tracking-wide",
              isActive 
                ? "bg-white text-indigo-600 shadow-sm ring-1 ring-slate-900/5" 
                : "text-slate-500 hover:text-slate-900 hover:bg-slate-200/50"
            )}
          >
            {lang.label}
          </button>
        );
      })}
    </div>
  );
}