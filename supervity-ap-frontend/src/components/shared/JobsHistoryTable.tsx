"use client";

import { useState, useEffect } from "react";
import { format } from "date-fns";
import { type Job, getAllJobs } from "@/lib/api";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/Table";
import { Badge } from "../ui/Badge";

export const JobsHistoryTable = ({ refreshKey }: { refreshKey: number }) => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchJobs = async () => {
      setIsLoading(true);
      try {
        const fetchedJobs = await getAllJobs();
        setJobs(fetchedJobs);
      } catch (error) {
        console.error("Failed to fetch jobs history", error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchJobs();
  }, [refreshKey]); // This will refetch when refreshKey changes

  if (isLoading) {
    return <p className="text-gray-800 font-medium">Loading history...</p>;
  }

  if (jobs.length === 0) {
    return (
      <div className="text-center text-gray-800 py-8">
        <p>No upload history found.</p>
        <p className="text-sm mt-1">
          Upload your first documents in the Document Hub to see processing
          history.
        </p>
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Job ID</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Files</TableHead>
          <TableHead>Created At</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {jobs.map((job) => (
          <TableRow key={job.id}>
            <TableCell className="font-medium">#{job.id}</TableCell>
            <TableCell>
              <Badge
                variant={
                  job.status === "completed"
                    ? "success"
                    : job.status === "failed"
                      ? "destructive"
                      : "default"
                }
              >
                {job.status}
              </Badge>
            </TableCell>
            <TableCell>
              {job.processed_files} / {job.total_files}
            </TableCell>
            <TableCell>
              {format(new Date(job.created_at), "MMM d, yyyy h:mm a")}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};
