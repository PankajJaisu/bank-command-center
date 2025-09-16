import type { Metadata } from "next";
import "./globals.css";
import { Toaster } from "react-hot-toast";
import { AppProvider } from "@/lib/AppContext";
import { AuthGuard } from "@/components/shared/AuthGuard";
import { LayoutRenderer } from "@/components/shared/LayoutRenderer";

export const metadata: Metadata = {
  title: "Supervity AI Bank Collection Manager",
  description: "The AI-Powered Accounts Payable Command Center",
  icons: {
    icon: [{ url: "/favicon.png", sizes: "any", type: "image/png" }],
    shortcut: "/favicon.png",
    apple: "/favicon.png",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans">
        <AppProvider>
          <AuthGuard>
            <LayoutRenderer>{children}</LayoutRenderer>
          </AuthGuard>
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: "#363636",
                color: "#fff",
              },
            }}
          />
        </AppProvider>
      </body>
    </html>
  );
}
