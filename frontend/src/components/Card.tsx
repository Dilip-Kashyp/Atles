"use client";

import React from "react";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string;
  children?: React.ReactNode;
  hoverable?: boolean;
}

export default function Card({ className = "", children, hoverable = true, style, ...props }: CardProps) {
  return (
    <div
      className={`glass-card p-6 ${hoverable ? "hover:-translate-y-1 transition-all duration-300" : ""} ${className}`}
      style={style}
      {...props}
    >
      {children}
    </div>
  );
}
