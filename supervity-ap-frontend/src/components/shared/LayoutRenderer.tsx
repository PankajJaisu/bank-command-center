"use client";
import { usePathname } from "next/navigation";
import { AppLayoutClient } from "./AppLayoutClient";

export function LayoutRenderer({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAuthPage = pathname === "/login" || pathname === "/signup";

  if (isAuthPage) {
    return <>{children}</>;
  }

  return <AppLayoutClient>{children}</AppLayoutClient>;
}
