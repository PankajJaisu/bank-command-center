"use client";

import { useState } from "react";
import { type Job, syncSampleData } from "@/lib/api";
import { FileUpload } from "@/components/shared/FileUpload";
import { JobProgress } from "@/components/shared/JobProgress";
import { UploadStatusList } from "@/components/shared/UploadStatusList";
import { syncEvents } from "@/lib/sync-events";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import toast from "react-hot-toast";
import { Database, Upload, Loader2 } from "lucide-react";

type ProcessingState = {
  job: Job | null;
  isLoading: boolean;
  source: "sync" | "manual";
};

export default function DataCenterPage() {
  const [activeJob, setActiveJob] = useState<ProcessingState | null>(null);

  const handleSyncClick = async () => {
    setActiveJob({ job: null, isLoading: true, source: "sync" });
    toast.loading("Starting comprehensive data sync...", { id: "sync-toast" });
    try {
      const job = await syncSampleData();
      toast.success(`Sync job #${job.id} started!`, { id: "sync-toast" });
      setActiveJob({ job, isLoading: true, source: "sync" });
      
      // Notify other pages that sync has started
      syncEvents.notifySyncStarted(job.id);
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "An unknown error occurred.";
      toast.error(`Sync failed: ${message}`, { id: "sync-toast" });
      setActiveJob(null);
    }
  };

  const handleManualUploadSuccess = (job: Job) => {
    setActiveJob({ job, isLoading: true, source: "manual" });
  };

  const handleJobComplete = (completedJob: Job) => {
    toast.success(`Job #${completedJob.id} completed!`);
    if (activeJob) {
      setActiveJob({ ...activeJob, job: completedJob, isLoading: false });
    }
  };

  const clearResults = () => {
    setActiveJob(null);
  };

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Database className="w-8 h-8 text-purple-accent" />
              <div>
                <CardTitle>Comprehensive Data Sync</CardTitle>
                <CardDescription>
                  Process all sample data including contract notes, customer Excel files, and loan documents.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="text-center py-8">
              <p className="mb-4 text-gray-medium">
                • Process contract notes (PDFs) with OCR to extract EMI amounts, due dates, and contract terms<br/>
                • Import customer data from Excel files to populate Collection Cell and Resolution Workbench<br/>
                • Process loan documents and other sample data files for comprehensive data integration
              </p>
              <Button
                size="lg"
                onClick={handleSyncClick}
                disabled={!!activeJob}
              >
                {activeJob?.isLoading && activeJob.source === "sync" && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Sync All Sample Data
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-3">
              <Upload className="w-8 h-8 text-cyan-accent" />
              <div>
                <CardTitle>Manual Document Upload</CardTitle>
                <CardDescription>
                  Upload specific documents (legal notices, customer correspondence) and associate with Customer No. or Loan ID.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <FileUpload onUploadSuccess={handleManualUploadSuccess} />
          </CardContent>
        </Card>
      </div>

      {activeJob && (
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <CardTitle>Processing Job #{activeJob.job?.id}</CardTitle>
              {activeJob.job && !activeJob.isLoading && (
                <Button variant="secondary" onClick={clearResults}>
                  Start New Job
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {activeJob.job &&
              (activeJob.isLoading ? (
                <JobProgress
                  key={activeJob.job.id}
                  initialJob={activeJob.job}
                  onComplete={handleJobComplete}
                />
              ) : (
                <UploadStatusList results={activeJob.job.summary || []} />
              ))}
          </CardContent>
        </Card>
      )}


    </div>
  );
}
