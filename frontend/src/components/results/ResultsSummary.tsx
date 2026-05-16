'use client';
import { Link } from '@/i18n/navigation';

interface ResultsSummaryProps {
  total: number;
  eligibleCount: number;
  likelyCount: number;
  latencyMs?: number;
}

export function ResultsSummary({ total, eligibleCount, likelyCount, latencyMs }: ResultsSummaryProps) {
  const othersCount = total - eligibleCount - likelyCount;

  return (
    <div className="flex flex-col gap-3 bg-white border border-slate-200 p-5 rounded-xl shadow-sm relative overflow-hidden">
      <div className="flex justify-between items-start">
        <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
          {total} schemes matched your profile
        </h2>
        {latencyMs !== undefined && (
          <span className="text-xs font-bold text-slate-400">
            Searched 334 schemes · {latencyMs}ms
          </span>
        )}
      </div>
      
      <div className="flex justify-between items-center w-full">
        <div className="flex flex-wrap items-center gap-4 text-sm font-bold text-slate-600">
          <div className="flex items-center gap-2 bg-green-50 text-green-700 px-3 py-1 rounded-full ring-1 ring-green-600/20">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            {eligibleCount} Eligible
          </div>
          <div className="flex items-center gap-2 bg-amber-50 text-amber-700 px-3 py-1 rounded-full ring-1 ring-amber-600/20">
            <div className="w-2 h-2 rounded-full bg-amber-400" />
            {likelyCount} Likely Eligible
          </div>
          <div className="flex items-center gap-2 bg-slate-50 text-slate-700 px-3 py-1 rounded-full ring-1 ring-slate-500/20">
            <div className="w-2 h-2 rounded-full bg-slate-400" />
            {othersCount} Others
          </div>
        </div>

        <Link
          href="/profile?fresh=true"
          className="text-sm text-slate-500 hover:text-indigo-600 underline font-semibold transition-colors"
        >
          ← Start Over with a new profile
        </Link>
      </div>
    </div>
  );
}