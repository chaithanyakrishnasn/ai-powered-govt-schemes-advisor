'use client';

import { Input } from '@/components/ui/input';

interface IncomeInputProps {
  value?: number;
  onChange: (value: number | undefined) => void;
  id?: string;
  placeholder?: string;
}

export function IncomeInput({ value, onChange, id, placeholder }: IncomeInputProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    if (val === '') {
      onChange(undefined);
    } else {
      const num = parseInt(val, 10);
      if (!isNaN(num)) onChange(num);
    }
  };

  const formatLakhs = (val: number) => {
    if (val >= 10000000) {
      return `₹${(val / 10000000).toFixed(2)}Cr`;
    }
    if (val >= 100000) {
      return `₹${(val / 100000).toFixed(2)}L`;
    }
    if (val >= 1000) {
      return `₹${(val / 1000).toFixed(2)}K`;
    }
    return `₹${val}`;
  };

  return (
    <div className="space-y-1">
      <div className="relative">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">₹</span>
        <Input
          id={id}
          type="number"
          min={0}
          value={value ?? ''}
          onChange={handleChange}
          placeholder={placeholder}
          className="pl-8"
        />
      </div>
      {value !== undefined && value > 0 && (
        <p className="text-sm text-muted-foreground">
          = {formatLakhs(value)}/year
        </p>
      )}
    </div>
  );
}
