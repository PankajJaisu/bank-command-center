"use client";

import { useState } from "react";
import { type Job } from "@/lib/api";
import { FileUpload } from "@/components/shared/FileUpload";
import { JobProgress } from "@/components/shared/JobProgress";
import { JobsHistoryTable } from "@/components/shared/JobsHistoryTable";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";

export default function DocumentHubPage() {
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);

  const handleUploadSuccess = (job: Job) => {
    setActiveJob(job);
  };

  const handleJobComplete = () => {
    // Increment the key to force the history table to refetch
    setHistoryRefreshKey((prev) => prev + 1);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
      {/* Left Column for Upload & Progress */}
      <div className="md:col-span-1 flex flex-col gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Upload Documents</CardTitle>
            <CardDescription>
              Upload Invoices, POs, and GRNs for processing.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FileUpload onUploadSuccess={handleUploadSuccess} />
          </CardContent>
        </Card>

        {activeJob && (
          <JobProgress initialJob={activeJob} onComplete={handleJobComplete} />
        )}
      </div>

      {/* Right Column for History */}
      <div className="md:col-span-2">
        <Card>
          <CardHeader>
            <CardTitle>History of Uploads</CardTitle>
          </CardHeader>
          <CardContent>
            <JobsHistoryTable refreshKey={historyRefreshKey} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
