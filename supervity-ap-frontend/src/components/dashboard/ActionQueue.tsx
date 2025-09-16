"use client";
import { useState, useEffect } from "react";
import { type InvoiceSummary, getActionQueue } from "@/lib/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import Link from "next/link";
import { ArrowRight, Inbox } from "lucide-react";

interface ActionQueueProps {
  userId?: number;
}

export const ActionQueue = ({ userId }: ActionQueueProps) => {
  const [queue, setQueue] = useState<InvoiceSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    getActionQueue(userId)
      .then(setQueue)
      .finally(() => setIsLoading(false));
  }, [userId]);

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle>Action Queue</CardTitle>
        <CardDescription>
          Top priority invoices requiring review.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <p className="text-sm text-gray-500">Loading actions...</p>
        ) : queue.length === 0 ? (
          <div className="text-center py-4 text-gray-500">
            <Inbox className="mx-auto h-10 w-10 mb-2" />
            <p className="font-semibold">Queue is clear!</p>
            <p className="text-sm">
              No invoices are currently awaiting review.
            </p>
          </div>
        ) : (
          <ul className="space-y-3">
            {queue.map((inv) => (
              <li
                key={inv.id}
                className="flex items-center justify-between p-2 rounded-md bg-gray-50 hover:bg-gray-100"
              >
                <div>
                  <p className="font-semibold text-gray-800">
                    {inv.invoice_id}
                  </p>
                  <p className="text-sm text-gray-500">{inv.vendor_name}</p>
                </div>
                <Link
                  href={`/resolution-workbench?invoiceId=${inv.invoice_id}`}
                >
                  <Button variant="ghost" size="sm">
                    Review <ArrowRight className="ml-2 h-4 w-4" />
                  </Button>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
};
