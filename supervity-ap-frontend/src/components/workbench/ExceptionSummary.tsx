"use client";
import { type MatchTraceStep } from "@/lib/api";
import { AlertCircle, FileWarning, BadgeDollarSign, Scale } from "lucide-react";
import { ActionableHold } from "./ActionableHold";

interface ExceptionSummaryProps {
  trace: MatchTraceStep[];
  invoiceDbId: number;
  onActionComplete: () => void;
}

const getIconForStep = (step: string) => {
  if (step.toLowerCase().includes("quantity"))
    return <Scale className="h-5 w-5 text-orange-warning" />;
  if (step.toLowerCase().includes("price"))
    return <BadgeDollarSign className="h-5 w-5 text-orange-warning" />;
  if (
    step.toLowerCase().includes("document") ||
    step.toLowerCase().includes("item match") ||
    step.toLowerCase().includes("timing") ||
    step.toLowerCase().includes("grn") ||
    step.toLowerCase().includes("duplicate")
  )
    return <FileWarning className="h-5 w-5 text-orange-warning" />;
  return <AlertCircle className="h-5 w-5 text-orange-warning" />;
};

const generateFriendlyMessage = (failure: MatchTraceStep): string => {
  // We can keep this simple, as the detailed messages will now be in the line-item table
  return failure.message;
};

export const ExceptionSummary = ({
  trace,
  invoiceDbId,
  onActionComplete,
}: ExceptionSummaryProps) => {
  if (!trace) return null;

  // --- START: MODIFIED LOGIC TO FILTER FAILURES ---
  // Only show failures that are NOT related to line-item price or quantity matches.
  const headerLevelFailures = trace.filter((step) => {
    const lowerStep = step.step.toLowerCase();
    return (
      step.status === "FAIL" &&
      !lowerStep.includes("price match") &&
      !lowerStep.includes("quantity match")
    );
  });

  // Filter out the generic "Final Result" failure to avoid redundancy
  const specificFailures = headerLevelFailures.filter(
    (f) => f.step !== "Final Result",
  );
  // --- END: MODIFIED LOGIC ---

  if (specificFailures.length === 0) {
    return null; // Don't render the card if there are no header-level issues.
  }

  return (
    <div className="space-y-3">
      <h3 className="text-lg font-semibold text-black">Resolution Required</h3>
      {specificFailures.map((failure, index) => {
        // --- START: NEW LOGIC TO RENDER ACTIONABLE COMPONENT ---
        if (failure.step === "GRN Validation") {
          return (
            <ActionableHold
              key={index}
              invoiceDbId={invoiceDbId}
              onActionComplete={onActionComplete}
              message={failure.message}
            />
          );
        }
        // --- END: NEW LOGIC ---

        // Fallback for all other errors
        return (
          <div
            key={index}
            className="p-4 rounded-lg bg-orange-warning/10 border-l-4 border-orange-warning"
          >
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 mt-1">
                {getIconForStep(failure.step)}
              </div>
              <div>
                <h4 className="font-semibold text-orange-700">
                  {failure.step}
                </h4>
                <p className="text-sm text-gray-700 mt-1">
                  {generateFriendlyMessage(failure)}
                </p>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
