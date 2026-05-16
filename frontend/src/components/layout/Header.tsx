'use client';

import { useTranslations } from 'next-intl';
import { Link, usePathname } from '@/i18n/navigation';
import { Landmark, Menu } from 'lucide-react';
import LanguageSwitcher from '@/components/common/LanguageSwitcher';
import { Button } from '@/components/ui/button';
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet';
import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';

export default function Header() {
  const t = useTranslations('nav');
  const pathname = usePathname();
  const [isOpen, setIsOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handler = () => setScrolled(window.scrollY > 10);
    window.addEventListener('scroll', handler);
    return () => window.removeEventListener('scroll', handler);
  }, []);

  const navLinks = [
    { href: '/', label: t('home') },
    { href: '/profile', label: t('findSchemes') },
    { href: '/chat', label: t('chat') },
  ];

  const NavContent = ({ mobile = false }: { mobile?: boolean }) => (
    <nav className={cn(
      "flex",
      mobile ? "flex-col space-y-4 mt-8" : "items-center space-x-8"
    )}>
      {navLinks.map((link) => {
        const isActive = pathname === link.href || (link.href !== '/' && pathname?.startsWith(link.href));
        return (
          <Link
            key={link.href}
            href={link.href}
            onClick={() => setIsOpen(false)}
            className={cn(
              "text-sm font-semibold transition-all relative py-1",
              isActive 
                ? "text-indigo-600" 
                : "text-slate-500 hover:text-slate-900",
              !mobile && "after:absolute after:bottom-0 after:left-0 after:h-[2px] after:w-full after:origin-bottom-right after:scale-x-0 after:bg-indigo-600 after:transition-transform after:duration-300 hover:after:origin-bottom-left hover:after:scale-x-100",
              !mobile && isActive && "after:scale-x-100"
            )}
          >
            {link.label}
          </Link>
        );
      })}
      {mobile && (
        <div className="pt-6 mt-4 border-t border-slate-100">
          <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">{t('language')}</p>
          <LanguageSwitcher />
        </div>
      )}
    </nav>
  );

  return (
    <header className={cn(
      "sticky top-0 z-50 w-full transition-all duration-300 border-b",
      scrolled 
        ? "bg-white/90 backdrop-blur-md shadow-sm border-transparent" 
        : "bg-white border-slate-200"
    )}>
      <div className="container mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8 max-w-7xl">
        {/* Logo */}
        <Link href="/" className="flex items-center space-x-2.5 group">
          <div className="bg-indigo-50 p-1.5 rounded-lg group-hover:bg-indigo-100 transition-colors">
            <Landmark className="h-5 w-5 text-indigo-600" />
          </div>
          <span className="text-xl font-extrabold tracking-tight text-slate-900">Yojana AI</span>
        </Link>

        {/* Desktop Nav */}
        <div className="hidden md:flex items-center space-x-8">
          <NavContent />
          <div className="h-6 w-px bg-slate-200" />
          <LanguageSwitcher />
        </div>

        {/* Mobile Nav */}
        <div className="md:hidden flex items-center">
          <Sheet open={isOpen} onOpenChange={setIsOpen}>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="text-slate-500 hover:text-slate-900 hover:bg-slate-50">
                <Menu className="h-6 w-6" />
                <span className="sr-only">Toggle menu</span>
              </Button>
            </SheetTrigger>
            <SheetContent side="right" className="w-[300px] sm:w-[350px] border-l-0 shadow-2xl">
              <div className="flex items-center space-x-2.5 mt-2 mb-8">
                <div className="bg-indigo-50 p-1.5 rounded-lg">
                  <Landmark className="h-5 w-5 text-indigo-600" />
                </div>
                <span className="text-xl font-extrabold tracking-tight text-slate-900">Yojana AI</span>
              </div>
              <NavContent mobile />
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}