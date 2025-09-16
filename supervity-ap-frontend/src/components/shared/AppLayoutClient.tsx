"use client";

import { ReactNode } from "react";
import { Sidebar } from "@/components/shared/Sidebar";
import { Header } from "@/components/shared/Header";
import { AIChatOverlay } from "@/components/shared/AIChatOverlay";
import { useAppContext } from "@/lib/AppContext";

interface AppLayoutClientProps {
  children: ReactNode;
}

export const AppLayoutClient = ({ children }: AppLayoutClientProps) => {
  const { isChatOpen, closeChat } = useAppContext();

  return (
    <div className="flex h-screen bg-gray-bg">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 p-6 overflow-y-auto relative">{children}</main>
      </div>
      <AIChatOverlay isOpen={isChatOpen} onClose={closeChat} />
    </div>
  );
};
