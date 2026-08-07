"use client";

import React from "react";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
  startIcon?: React.ReactNode;
}

export default function Input({ label, error, helperText, startIcon, className = "", ...props }: InputProps) {
  return (
    <div className="flex flex-col gap-1.5 w-full">
      {label && <label className="text-xs font-semibold text-slate-300 tracking-wide">{label}</label>}
      <div className="relative flex items-center">
        {startIcon && <div className="absolute left-3 text-slate-400 pointer-events-none">{startIcon}</div>}
        <input
          className={`w-full bg-slate-900/60 border ${
            error ? "border-rose-500/50 focus:border-rose-500" : "border-slate-800 focus:border-blue-500/60"
          } rounded-xl ${startIcon ? "pl-10" : "pl-3.5"} pr-3.5 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none transition-all duration-200 ${className}`}
          {...props}
        />
      </div>
      {error ? (
        <span className="text-xs text-rose-400 font-medium">{error}</span>
      ) : (
        helperText && <span className="text-xs text-slate-500">{helperText}</span>
      )}
    </div>
  );
}
