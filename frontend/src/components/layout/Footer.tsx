import { useTranslations } from 'next-intl';

export default function Footer() {
  const t = useTranslations('footer');

  return (
    <footer className="w-full border-t bg-slate-50 py-8 text-center text-slate-500">
      <div className="container mx-auto px-4">
        <p className="text-sm font-medium mb-2">
          Yojana AI — {t('tagline')}
        </p>
        <p className="text-xs">
          {t('disclaimer')}
        </p>
      </div>
    </footer>
  );
}
