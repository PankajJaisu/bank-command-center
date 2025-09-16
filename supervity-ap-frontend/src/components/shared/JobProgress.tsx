"use client";

import { useState, useEffect } from "react";
import { type Job, getJobStatus } from "@/lib/api";
import { Badge } from "../ui/Badge";
import {
  Loader2,
  CheckCircle,
  AlertTriangle,
  FileText,
  Magnet,
  ShieldCheck,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface JobProgressProps {
  initialJob: Job;
  onComplete: (job: Job) => void;
}

const Step = ({
  icon: Icon,
  title,
  status,
}: {
  icon: React.ElementType;
  title: string;
  status: "active" | "completed" | "pending";
}) => (
  <div className="flex flex-col items-center gap-2">
    <div
      className={cn(
        "w-12 h-12 rounded-full flex items-center justify-center border-2",
        status === "completed" &&
          "bg-green-success border-green-success text-white",
        status === "active" &&
          "bg-blue-primary border-blue-primary text-white animate-pulse",
        status === "pending" && "bg-gray-100 border-gray-300 text-gray-400",
      )}
    >
      <Icon className="w-6 h-6" />
    </div>
    <p
      className={cn(
        "text-xs font-semibold",
        status === "active" && "text-blue-primary",
        status === "completed" && "text-green-success",
        status === "pending" && "text-gray-400",
      )}
    >
      {title}
    </p>
  </div>
);

export const JobProgress = ({ initialJob, onComplete }: JobProgressProps) => {
  const [job, setJob] = useState<Job>(initialJob);

  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (job.status === "processing" || job.status === "matching") {
      interval = setInterval(async () => {
        try {
          const updatedJob = await getJobStatus(job.id);
          setJob(updatedJob);
          if (
            updatedJob.status === "completed" ||
            updatedJob.status === "failed"
          ) {
            clearInterval(interval);
            onComplete(updatedJob);
          }
        } catch (error) {
          console.error("Failed to poll job status:", error);
          clearInterval(interval);
        }
      }, 2000);
    } else if (job.status === "completed" || job.status === "failed") {
      onComplete(job);
    }
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job.id, job.status, onComplete]);

  const getOverallStatusInfo = () => {
    switch (job.status) {
      case "completed":
        return {
          icon: <CheckCircle className="w-5 h-5 text-green-success" />,
          text: "Completed",
          variant: "success" as const,
        };
      case "failed":
        return {
          icon: <AlertTriangle className="w-5 h-5 text-pink-destructive" />,
          text: "Failed",
          variant: "destructive" as const,
        };
      default:
        return {
          icon: <Loader2 className="w-5 h-5 animate-spin" />,
          text: "In Progress...",
          variant: "default" as const,
        };
    }
  };

  const { icon, text, variant } = getOverallStatusInfo();
  const progress =
    job.total_files > 0 ? (job.processed_files / job.total_files) * 100 : 0;
  const isFinished = job.status === "completed" || job.status === "failed";

  return (
    <div className="p-4 border rounded-lg bg-gray-50 flex flex-col h-full">
      <div className="flex justify-between items-center mb-6">
        <h4 className="font-semibold">Job #{job.id}</h4>
        <Badge variant={variant} className="flex items-center gap-2">
          {icon}
          <span>{text}</span>
        </Badge>
      </div>

      <div className="flex justify-around items-center my-auto">
        <Step
          icon={FileText}
          title="Ingestion"
          status={job.status === "processing" ? "active" : "completed"}
        />
        <div
          className={cn(
            "flex-grow h-1 mx-4 rounded-full",
            job.status !== "processing" ? "bg-green-success" : "bg-gray-200",
          )}
        />
        <Step
          icon={Magnet}
          title="Matching"
          status={
            job.status === "matching"
              ? "active"
              : job.status === "processing"
                ? "pending"
                : "completed"
          }
        />
        <div
          className={cn(
            "flex-grow h-1 mx-4 rounded-full",
            isFinished ? "bg-green-success" : "bg-gray-200",
          )}
        />
        <Step
          icon={ShieldCheck}
          title="Finalized"
          status={isFinished ? "completed" : "pending"}
        />
      </div>

      <div className="mt-auto">
        <div className="w-full bg-gray-200 rounded-full h-2.5">
          <div
            className="bg-blue-primary h-2.5 rounded-full transition-all duration-500"
            style={{ width: `${progress}%` }}
          ></div>
        </div>
        <p className="text-sm text-right mt-1 text-gray-800 font-medium">
          {job.processed_files} / {job.total_files} files processed
        </p>
      </div>
    </div>
  );
};
