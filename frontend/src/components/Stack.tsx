"use client";

import React from "react";

export interface StackProps extends React.HTMLAttributes<HTMLDivElement> {
  direction?: "row" | "col";
  gap?: number | string;
  align?: "start" | "center" | "end" | "stretch";
  justify?: "start" | "center" | "end" | "between" | "around";
  className?: string;
  children?: React.ReactNode;
}

export default function Stack({
  direction = "col",
  gap = 4,
  align = "stretch",
  justify = "start",
  className = "",
  children,
  style,
  ...props
}: StackProps) {
  const dirClass = direction === "row" ? "flex-row" : "flex-col";
  const alignClass = {
    start: "items-start",
    center: "items-center",
    end: "items-end",
    stretch: "items-stretch",
  }[align];

  const justifyClass = {
    start: "justify-start",
    center: "justify-center",
    end: "justify-end",
    between: "justify-between",
    around: "justify-around",
  }[justify];

  return (
    <div
      className={`flex ${dirClass} ${alignClass} ${justifyClass} ${className}`}
      style={{ gap: typeof gap === "number" ? `${gap * 0.25}rem` : gap, ...style }}
      {...props}
    >
      {children}
    </div>
  );
}
