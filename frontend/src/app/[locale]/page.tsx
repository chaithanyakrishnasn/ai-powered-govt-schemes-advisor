import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Users, FileText, Languages, ArrowRight } from 'lucide-react';

export default function LandingPage() {
  const t = useTranslations('home');

  return (
    <div className="flex flex-col w-full bg-white">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-24 pb-32 lg:pt-36 lg:pb-40 hero-bg">
        <div className="container relative mx-auto px-4 sm:px-6 lg:px-8 text-center z-10 max-w-7xl">
          <h1 className="text-5xl font-extrabold tracking-tight text-slate-900 sm:text-6xl md:text-7xl max-w-4xl mx-auto leading-[1.1]">
            Find Government Schemes You{' '}
            <span className="bg-gradient-to-r from-indigo-600 to-indigo-400 bg-clip-text text-transparent">
              Actually
            </span>
            {' '}Qualify For
          </h1>
          <p className="mt-6 text-lg leading-8 text-slate-600 max-w-2xl mx-auto font-medium">
            Answer 4 quick questions. Get personalized scheme recommendations in seconds.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Button asChild size="lg" className="rounded-full px-8 h-14 text-base font-bold bg-indigo-600 hover:bg-indigo-700 shadow-sm transition-all hover:-translate-y-0.5 w-full sm:w-auto">
              <Link href="/profile?fresh=true" className="flex items-center justify-center gap-2">
                Get Started — Free <ArrowRight className="h-5 w-5 ml-1" />
              </Link>
            </Button>
            <p className="text-sm font-medium text-slate-500 sm:hidden">
              No registration required · Works in Hindi & Kannada
            </p>
          </div>
          <p className="mt-6 text-sm font-medium text-slate-500 hidden sm:block">
            No registration required · Works in Hindi & Kannada
          </p>
          
          <div className="mt-14 flex flex-wrap items-center justify-center gap-x-8 gap-y-4 text-sm font-bold text-slate-600">
            <div className="flex items-center gap-2 bg-white/80 backdrop-blur-sm px-4 py-2.5 rounded-full border border-slate-200/50 shadow-sm">
              <span className="text-indigo-600 text-base">334+</span> Schemes
            </div>
            <div className="flex items-center gap-2 bg-white/80 backdrop-blur-sm px-4 py-2.5 rounded-full border border-slate-200/50 shadow-sm">
              <span className="text-indigo-600 text-base">₹1L+</span> Avg Benefit
            </div>
            <div className="flex items-center gap-2 bg-white/80 backdrop-blur-sm px-4 py-2.5 rounded-full border border-slate-200/50 shadow-sm">
              <span className="text-indigo-600 text-base">3</span> Languages
            </div>
          </div>
        </div>
      </section>

      {/* Social Proof Bar */}
      <section className="border-y border-slate-100 bg-slate-50/50 py-10">
        <div className="container mx-auto px-4 text-center">
          <p className="text-xs font-bold text-slate-400 mb-8 uppercase tracking-widest">Trusted data sources</p>
          <div className="flex flex-wrap justify-center items-center gap-8 md:gap-16 opacity-60 grayscale">
            <span className="font-extrabold text-slate-700 text-xl tracking-tight">myScheme.gov.in</span>
            <span className="font-extrabold text-slate-700 text-xl tracking-tight">Ministry of Agriculture</span>
            <span className="font-extrabold text-slate-700 text-xl tracking-tight">Government of Karnataka</span>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 bg-white">
        <div className="container mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-1 gap-8 md:grid-cols-3 max-w-6xl mx-auto">
            <Card className="border border-slate-100 shadow-sm hover:shadow-md transition-shadow bg-white overflow-hidden group">
              <CardHeader className="pb-4">
                <div className="h-14 w-14 rounded-2xl bg-indigo-50 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform">
                  <Users className="h-7 w-7 text-indigo-600" />
                </div>
                <CardTitle className="text-xl font-bold text-slate-900">{t('features.personalized.title')}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-600 font-medium leading-relaxed">
                  {t('features.personalized.description')}
                </p>
                <div className="mt-8 pt-5 border-t border-slate-50">
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Smart AI matching engine</p>
                </div>
              </CardContent>
            </Card>

            <Card className="border border-slate-100 shadow-sm hover:shadow-md transition-shadow bg-white overflow-hidden group">
              <CardHeader className="pb-4">
                <div className="h-14 w-14 rounded-2xl bg-indigo-50 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform">
                  <FileText className="h-7 w-7 text-indigo-600" />
                </div>
                <CardTitle className="text-xl font-bold text-slate-900">{t('features.explained.title')}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-600 font-medium leading-relaxed">
                  {t('features.explained.description')}
                </p>
                <div className="mt-8 pt-5 border-t border-slate-50">
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Clear step-by-step guidance</p>
                </div>
              </CardContent>
            </Card>

            <Card className="border border-slate-100 shadow-sm hover:shadow-md transition-shadow bg-white overflow-hidden group">
              <CardHeader className="pb-4">
                <div className="h-14 w-14 rounded-2xl bg-indigo-50 flex items-center justify-center mb-5 group-hover:scale-110 transition-transform">
                  <Languages className="h-7 w-7 text-indigo-600" />
                </div>
                <CardTitle className="text-xl font-bold text-slate-900">{t('features.multilingual.title')}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-600 font-medium leading-relaxed">
                  {t('features.multilingual.description')}
                </p>
                <div className="mt-8 pt-5 border-t border-slate-50">
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">Native English, Hindi, Kannada</p>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>
    </div>
  );
}