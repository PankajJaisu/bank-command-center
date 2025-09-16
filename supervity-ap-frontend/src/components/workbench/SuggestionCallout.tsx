"use client";

import { type Suggestion } from "@/lib/api";
import { Lightbulb } from "lucide-react";
import { Button } from "../ui/Button";

interface SuggestionCalloutProps {
  suggestion: Suggestion;
  onApply: (action: string) => void;
}

export const SuggestionCallout = ({
  suggestion,
  onApply,
}: SuggestionCalloutProps) => {
  return (
    <div className="p-4 rounded-lg bg-purple-accent/10 border-l-4 border-purple-accent">
      <div className="flex items-start gap-3">
        <Lightbulb className="h-5 w-5 text-purple-accent mt-1 flex-shrink-0" />
        <div>
          <h4 className="font-semibold text-purple-accent">AI Suggestion</h4>
          <p className="text-sm text-gray-dark mt-1 mb-3">
            {suggestion.message}
          </p>
          <Button size="sm" onClick={() => onApply(suggestion.action)}>
            Apply Suggestion & Approve
          </Button>
        </div>
      </div>
    </div>
  );
};
