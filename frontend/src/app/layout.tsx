import { Noto_Sans, Noto_Sans_Devanagari, Noto_Sans_Kannada } from 'next/font/google';
import './globals.css';

const notoSans = Noto_Sans({ 
  subsets: ['latin'], 
  variable: '--font-noto-sans',
  weight: ['400', '500', '600', '700'],
  display: 'swap',
});

const notoDevanagari = Noto_Sans_Devanagari({
  subsets: ['devanagari'],
  variable: '--font-noto-devanagari',
  weight: ['400', '500', '600', '700'],
  display: 'swap',
});

const notoKannada = Noto_Sans_Kannada({
  subsets: ['kannada'],
  variable: '--font-noto-kannada',
  weight: ['400', '500', '600', '700'],
  display: 'swap',
});

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${notoSans.variable} ${notoDevanagari.variable} ${notoKannada.variable}`}>
      <body className="font-sans antialiased min-h-full flex flex-col">
        {children}
      </body>
    </html>
  );
}
