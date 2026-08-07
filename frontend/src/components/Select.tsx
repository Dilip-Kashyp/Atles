"use client";

import React from "react";

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: SelectOption[];
  error?: string;
}

export default function Select({ label, options, error, className = "", ...props }: SelectProps) {
  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && <label className="text-xs font-semibold text-slate-300 tracking-wide">{label}</label>}
      <select
        className={`w-full bg-slate-900/60 border ${
          error ? "border-rose-500/50" : "border-slate-800 focus:border-blue-500/60"
        } rounded-xl px-3.5 py-2.5 text-sm text-slate-100 focus:outline-none transition-all duration-200 ${className}`}
        {...props}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value} className="bg-slate-900 text-slate-200">
            {opt.label}
          </option>
        ))}
      </select>
      {error && <span className="text-xs text-rose-400 font-medium">{error}</span>}
    </div>
  );
}
