"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import Link from "next/link";
import { BookUser, Sparkles, SlidersHorizontal } from "lucide-react";

export const WelcomeGuide = () => {
  return (
    <Card className="bg-blue-primary/5 border-blue-primary/20">
      <CardHeader>
        <CardTitle className="text-2xl font-bold text-blue-primary">
          Welcome to the Proactive Loan Command Center!
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-gray-600">
          It looks like you&apos;re new here. Your personalized dashboard will
          populate with tasks and metrics as you begin processing invoices.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link href="/invoice-explorer" passHref>
            <Button
              variant="secondary"
              className="w-full h-full text-left flex flex-col items-start p-4 justify-start"
            >
              <BookUser className="w-6 h-6 mb-2 text-purple-accent" />
              <span className="font-semibold">Start Reviewing</span>
              <span className="text-xs font-normal">
                Head to the Invoice Explorer to see all available invoices.
              </span>
            </Button>
          </Link>
          <Link href="/ai-insights" passHref>
            <Button
              variant="secondary"
              className="w-full h-full text-left flex flex-col items-start p-4 justify-start"
            >
              <Sparkles className="w-6 h-6 mb-2 text-orange-warning" />
              <span className="font-semibold">See AI Insights</span>
              <span className="text-xs font-normal">
                Discover patterns and automation opportunities.
              </span>
            </Button>
          </Link>
          <Link href="/ai-policies" passHref>
            <Button
              variant="secondary"
              className="w-full h-full text-left flex flex-col items-start p-4 justify-start"
            >
              <SlidersHorizontal className="w-6 h-6 mb-2 text-green-success" />
              <span className="font-semibold">Configure System</span>
              <span className="text-xs font-normal">
                Admins can set up rules, users, and policies.
              </span>
            </Button>
          </Link>
        </div>
      </CardContent>
    </Card>
  );
};
