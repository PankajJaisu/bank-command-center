"use client";
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAppContext } from "@/lib/AppContext";
import { Loader2 } from "lucide-react";

const publicPaths = ["/login", "/signup"];

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoadingAuth } = useAppContext();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoadingAuth) {
      if (!isAuthenticated && !publicPaths.includes(pathname)) {
        router.push("/login");
      }
      if (isAuthenticated && publicPaths.includes(pathname)) {
        router.push("/dashboard");
      }
    }
  }, [isAuthenticated, isLoadingAuth, pathname, router]);

  if (isLoadingAuth) {
    return (
      <div className="h-screen w-screen flex items-center justify-center">
        <Loader2 className="w-10 h-10 animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated && !publicPaths.includes(pathname)) {
    // Still loading or redirecting, show a loader
    return (
      <div className="h-screen w-screen flex items-center justify-center">
        <Loader2 className="w-10 h-10 animate-spin" />
      </div>
    );
  }

  return <>{children}</>;
}
