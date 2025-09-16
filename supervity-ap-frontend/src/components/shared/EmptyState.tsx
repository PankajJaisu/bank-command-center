"use client";

import { type LucideIcon } from "lucide-react";

interface EmptyStateProps {
  Icon: LucideIcon;
  title: string;
  description: string;
  className?: string;
}

export const EmptyState = ({
  Icon,
  title,
  description,
  className,
}: EmptyStateProps) => {
  return (
    <div className={`text-center py-10 px-4 ${className}`}>
      <div className="flex flex-col items-center text-gray-500">
        <Icon className="w-16 h-16 mb-4" />
        <h3 className="text-lg font-semibold text-gray-700">{title}</h3>
        <p className="max-w-md mx-auto">{description}</p>
      </div>
    </div>
  );
};
