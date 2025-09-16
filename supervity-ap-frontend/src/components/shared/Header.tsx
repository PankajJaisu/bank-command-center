"use client"; // This component also needs the pathname hook

import { usePathname } from "next/navigation";
import { Bot, LogOut } from "lucide-react";
import { useAppContext } from "@/lib/AppContext";
import { Button } from "../ui/Button";

// This helper gets the title from the path for the header
const getPageTitle = (path: string) => {
  // Match the path to the labels in Sidebar.tsx
  const navMap: Record<string, string> = {
    "/dashboard": "Dashboard",
    "/data-center": "Data Center",
    "/invoice-explorer": "Invoice Explorer",
    "/resolution-workbench": "Resolution Workbench",
    "/ai-insights": "AI Insights",
    "/ai-policies": "AI Policies",
    "/document-hub": "Document Hub",
    "/style-guide": "Style Guide",
  };

  // Find a matching key that the path starts with
  const matchingKey = Object.keys(navMap).find((key) => path.startsWith(key));
  if (matchingKey) {
    return navMap[matchingKey];
  }

  // Fallback for unmapped pages
  const title = path.replace("/", "").replace("-", " ");
  return title.charAt(0).toUpperCase() + title.slice(1);
};

export const Header = () => {
  const pathname = usePathname();
  const { openChat, logout, currentUser } = useAppContext();
  const title = getPageTitle(pathname);

  const handleCopilotClick = () => {
    openChat();
  };

  return (
    <header className="bg-white border-b border-gray-light p-4 flex justify-between items-center shrink-0">
      <h1 className="text-xl font-semibold text-gray-dark">{title}</h1>
      <div className="flex items-center gap-4">
        {/* Display user email if available */}
        {currentUser && (
          <div className="hidden md:flex items-center gap-2">
            <span className="text-sm text-gray-600">Welcome,</span>
            <span className="text-sm font-medium text-gray-700">
              {currentUser.email}
            </span>
            <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
              {currentUser.role.name === "admin" ? "Admin" : "Processor"}
            </span>
          </div>
        )}
        <Button variant="primary" onClick={handleCopilotClick}>
          <Bot className="mr-2 h-5 w-5" />
          <span className="hidden sm:inline">Ask AI</span>
        </Button>
        {/* Add Logout Button */}
        {currentUser && (
          <Button
            variant="ghost"
            size="sm"
            onClick={logout}
            className="text-gray-600 hover:bg-red-50 hover:text-red-600"
            title="Logout"
          >
            <LogOut className="h-5 w-5" />
          </Button>
        )}
      </div>
    </header>
  );
};
