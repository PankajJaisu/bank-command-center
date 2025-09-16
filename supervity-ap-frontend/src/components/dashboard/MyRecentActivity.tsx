"use client";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/Card";
import { formatDistanceToNow } from "date-fns";
import Link from "next/link";

interface Activity {
  invoice_id: string;
  summary: string | null;
  timestamp: string;
}

export const MyRecentActivity = ({
  activities,
}: {
  activities: Activity[];
}) => {
  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>My Recent Activity</CardTitle>
        <CardDescription>A log of your most recent actions.</CardDescription>
      </CardHeader>
      <CardContent>
        <ul className="space-y-4">
          {activities.length > 0 ? (
            activities.map((activity, index) => (
              <li key={index} className="flex items-start gap-3">
                <div className="flex-shrink-0 w-2 h-2 mt-1.5 bg-blue-primary rounded-full" />
                <div>
                  <p className="text-sm text-gray-600">
                    {activity.summary || "Updated status"} on invoice{" "}
                    <Link
                      href={`/resolution-workbench?invoiceId=${activity.invoice_id}`}
                      className="font-semibold text-blue-primary hover:underline"
                    >
                      {activity.invoice_id}
                    </Link>
                  </p>
                  <p className="text-xs text-gray-400">
                    {formatDistanceToNow(new Date(activity.timestamp), {
                      addSuffix: true,
                    })}
                  </p>
                </div>
              </li>
            ))
          ) : (
            <p className="text-sm text-center text-gray-500 py-4">
              No recent activity to show.
            </p>
          )}
        </ul>
      </CardContent>
    </Card>
  );
};
