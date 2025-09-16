import { CheckCircle2, XCircle, AlertTriangle, Info } from "lucide-react";
import { cn } from "@/lib/utils";

interface TraceStep {
  step: string;
  status: "PASS" | "FAIL" | "INFO";
  message: string;
  details?: Record<string, unknown>;
}

const StatusIcon = ({ status }: { status: TraceStep["status"] }) => {
  switch (status) {
    case "PASS":
      return <CheckCircle2 className="h-5 w-5 text-green-success" />;
    case "FAIL":
      return <XCircle className="h-5 w-5 text-pink-destructive" />;
    case "INFO":
      return <Info className="h-5 w-5 text-blue-light" />;
    default:
      return <AlertTriangle className="h-5 w-5 text-orange-warning" />;
  }
};

export const MatchTrace = ({ trace }: { trace: TraceStep[] }) => {
  if (!trace || trace.length === 0) {
    return (
      <p className="text-gray-800 font-medium">No match trace available.</p>
    );
  }

  return (
    <div className="space-y-4">
      <h4 className="font-semibold text-gray-900">Match Trace</h4>
      <ul className="space-y-1">
        {trace.map((step, index) => (
          <li
            key={index}
            className={cn(
              "flex items-start gap-3 p-2 rounded-md",
              step.status === "FAIL" &&
                "bg-pink-destructive/10 border-l-4 border-pink-destructive",
            )}
          >
            <div className="flex-shrink-0 mt-1">
              <StatusIcon status={step.status} />
            </div>
            <div>
              <p
                className={`font-medium ${step.status === "FAIL" ? "text-pink-destructive" : "text-gray-800"}`}
              >
                {step.step}
              </p>
              <p className="text-sm text-gray-500">{step.message}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};
