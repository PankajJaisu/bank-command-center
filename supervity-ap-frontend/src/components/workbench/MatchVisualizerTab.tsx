"use client";
import { type MatchTraceStep } from "@/lib/api";
import { MatchTrace } from "../shared/MatchTrace";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/Card";

interface MatchVisualizerTabProps {
  matchTrace: MatchTraceStep[];
}

export const MatchVisualizerTab = ({ matchTrace }: MatchVisualizerTabProps) => {
  // Convert null details to undefined to match MatchTrace component expectations
  const transformedTrace = matchTrace.map((step) => ({
    ...step,
    details: step.details || undefined,
  }));

  return (
    <div className="p-4">
      <Card>
        <CardHeader>
          <CardTitle>3-Way Match Trace</CardTitle>
          <CardDescription>
            This is a step-by-step log from the automated matching engine,
            showing exactly why this invoice was approved or flagged for review.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <MatchTrace trace={transformedTrace} />
        </CardContent>
      </Card>
    </div>
  );
};
