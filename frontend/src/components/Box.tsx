"use client";

import React from "react";

export interface BoxProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}

export default function Box({ className = "", style, children, ...props }: BoxProps) {
  return (
    <div className={className} style={style} {...props}>
      {children}
    </div>
  );
}
