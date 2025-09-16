"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import { getDocumentFile } from "@/lib/api";
import { Loader2, AlertCircle, FileQuestion } from "lucide-react";
// Add imports for CSS, which is best practice for react-pdf
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";
import "@/lib/pdf-config"; // Initialize PDF.js worker configuration

// Dynamically import react-pdf components
const Document = dynamic(
  () => import("react-pdf").then((mod) => mod.Document),
  { ssr: false },
);
const Page = dynamic(() => import("react-pdf").then((mod) => mod.Page), {
  ssr: false,
});

// Define a simpler prop type
interface DocumentViewerProps {
  filePath: string | null;
}

export const DocumentViewer = ({ filePath }: DocumentViewerProps) => {
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  // --- START OF FIX: Add state for page count ---
  const [numPages, setNumPages] = useState<number | null>(null);

  // Function to be called when the document is loaded successfully
  function onDocumentLoadSuccess({ numPages }: { numPages: number }): void {
    setNumPages(numPages);
  }
  // --- END OF FIX ---

  // Ensure component only renders on client side
  useEffect(() => {
    setIsMounted(true);
  }, []);

  useEffect(() => {
    // FIX 2: Correctly handle URL cleanup to prevent memory leaks
    let objectUrl: string | null = null;

    // --- START OF FIX: Reset page count on new file ---
    setNumPages(null);
    // --- END OF FIX ---

    const loadDocument = async () => {
      if (!filePath) {
        setFileUrl(null);
        setError(null);
        return;
      }

      setIsLoading(true);
      setError(null);
      try {
        // getDocumentFile already returns a blob URL
        objectUrl = await getDocumentFile(filePath);
        setFileUrl(objectUrl);
      } catch {
        setError("Could not load document.");
        setFileUrl(null);
      } finally {
        setIsLoading(false);
      }
    };

    if (isMounted) {
      loadDocument();
    }

    // Cleanup function
    return () => {
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [filePath, isMounted]); // FIX 3: Remove fileUrl from dependency array to prevent infinite loop

  if (!isMounted) return null; // Prevent rendering on server

  return (
    <div className="bg-gray-200 p-4 flex justify-center h-full">
      {isLoading && (
        <div className="h-full flex items-center justify-center text-gray-800">
          <Loader2 className="w-8 h-8 animate-spin" />
        </div>
      )}
      {error && (
        <div className="h-full flex flex-col items-center justify-center text-pink-destructive">
          <AlertCircle className="w-8 h-8 mb-2" />
          <p className="font-medium">{error}</p>
        </div>
      )}
      {fileUrl && !isLoading && (
        <Document
          file={fileUrl}
          onLoadSuccess={onDocumentLoadSuccess} // <-- FIX: Add the success callback
          loading={
            <div className="flex items-center justify-center">
              <Loader2 className="w-6 h-6 animate-spin" />
            </div>
          }
          error={<p>Failed to load PDF.</p>}
        >
          {/* --- START OF FIX: Loop to render all pages --- */}
          {Array.from(new Array(numPages || 0), (el, index) => (
            <div key={`page_wrapper_${index + 1}`} className="mb-4 shadow-lg">
              <Page
                key={`page_${index + 1}`}
                pageNumber={index + 1}
                renderTextLayer={false}
                renderAnnotationLayer={false}
                loading="" // Disable individual page loader for smoother feel
              />
            </div>
          ))}
          {/* --- END OF FIX --- */}
        </Document>
      )}
      {!filePath && !isLoading && !error && (
        <div className="h-full flex flex-col items-center justify-center text-gray-500">
          <FileQuestion className="w-12 h-12 mb-2" />
          <p className="font-medium">Document not available</p>
        </div>
      )}
    </div>
  );
};
