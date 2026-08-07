"use client";

import React from "react";

export interface TypographyProps extends React.HTMLAttributes<HTMLElement> {
  variant?: "h1" | "h2" | "h3" | "h4" | "body1" | "body2" | "caption" | "subtitle";
  className?: string;
  children?: React.ReactNode;
}

export default function Typography({
  variant = "body1",
  className = "",
  children,
  ...props
}: TypographyProps) {
  switch (variant) {
    case "h1":
      return (
        <h1 className={`text-3xl font-bold tracking-tight text-slate-100 ${className}`} {...props}>
          {children}
        </h1>
      );
    case "h2":
      return (
        <h2 className={`text-2xl font-semibold tracking-tight text-slate-100 ${className}`} {...props}>
          {children}
        </h2>
      );
    case "h3":
      return (
        <h3 className={`text-xl font-semibold text-slate-200 ${className}`} {...props}>
          {children}
        </h3>
      );
    case "h4":
      return (
        <h4 className={`text-lg font-medium text-slate-200 ${className}`} {...props}>
          {children}
        </h4>
      );
    case "subtitle":
      return (
        <p className={`text-sm text-slate-400 font-medium ${className}`} {...props}>
          {children}
        </p>
      );
    case "body2":
      return (
        <p className={`text-xs text-slate-400 leading-relaxed ${className}`} {...props}>
          {children}
        </p>
      );
    case "caption":
      return (
        <span className={`text-[11px] text-slate-500 uppercase tracking-wider font-semibold ${className}`} {...props}>
          {children}
        </span>
      );
    default:
      return (
        <p className={`text-sm text-slate-300 leading-relaxed ${className}`} {...props}>
          {children}
        </p>
      );
  }
}
