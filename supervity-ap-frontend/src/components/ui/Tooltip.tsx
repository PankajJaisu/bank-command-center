"use client";

import React from "react";
import { cn } from "@/lib/utils";

interface TooltipProps {
  children: React.ReactNode;
  text: React.ReactNode; // Allow React nodes for richer content
  className?: string;
}

export const Tooltip = ({ children, text, className }: TooltipProps) => {
  return (
    <div className="relative flex items-center group">
      {children}
      <div
        className={cn(
          "absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-max max-w-xs p-2 text-xs text-white text-center",
          "bg-gray-800 rounded-md shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200 z-10 pointer-events-none",
          className,
        )}
      >
        {text}
      </div>
    </div>
  );
};
