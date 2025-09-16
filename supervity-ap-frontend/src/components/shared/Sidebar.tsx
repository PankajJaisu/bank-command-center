"use client"; // This component now uses a hook, so it must be a client component

import Link from "next/link";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAppContext } from "@/lib/AppContext"; // Import the context
import {
  LayoutDashboard,
  DatabaseZap, // New Icon for Data Center
  ClipboardList, // New Icon for Invoice Manager
  SlidersHorizontal, // New Icon for Configuration
  Sparkles, // New Icon for Automation
  CreditCard, // New Icon for Collection Cell
} from "lucide-react";

// New navigation structure (AI Bank Collection Manager integrated into header)
const navItems = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/data-center", icon: DatabaseZap, label: "Data Center" },
  {
    href: "/collection-cell",
    icon: CreditCard,
    label: "Collection Cell",
  },
  {
    href: "/resolution-workbench",
    icon: ClipboardList,
    label: "Resolution Workbench",
  },
  { href: "/ai-insights", icon: Sparkles, label: "AI Insights" },
  { href: "/ai-policies", icon: SlidersHorizontal, label: "AI Policies" },
];

export const Sidebar = () => {
  const pathname = usePathname();
  const { currentUser } = useAppContext(); // Get user from context

  return (
    <aside className="w-64 bg-blue-primary text-white p-4 flex flex-col shrink-0">
      <div className="mb-10 px-4 text-center">
        <Link href="/dashboard" className="block">
          <Image
            src="/logo.svg"
            alt="Supervity Logo"
            width={150}
            height={40}
            priority
            className="mx-auto"
          />
          <p className="text-xs text-gray-300 mt-1 font-semibold">
            Proactive Loan Collections Command Center
          </p>
        </Link>
      </div>
      <nav>
        <ul>
          {navItems.map((item) => {
            // --- ADD CONDITIONAL RENDER FOR DATA CENTER ---
            if (
              item.href === "/data-center" &&
              currentUser?.role.name !== "admin"
            ) {
              return null; // Don't render the Data Center link for non-admins
            }
            // --- END OF ADDITION ---

            return (
              <li key={item.label} className="mb-2">
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center p-3 rounded-lg text-sm font-medium transition-transform duration-200 ease-in-out hover:bg-white/20 hover:translate-x-1",
                    pathname === item.href ||
                      (pathname.startsWith(item.href) && item.href !== "/")
                      ? "bg-white/10 text-white font-semibold"
                      : "text-gray-200 hover:text-white",
                  )}
                >
                  <item.icon className="mr-3 h-5 w-5" />
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
};
