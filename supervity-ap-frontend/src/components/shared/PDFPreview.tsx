"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/Button";
import { X, Download, ExternalLink } from "lucide-react";
import toast from "react-hot-toast";

interface PDFPreviewProps {
  isOpen: boolean;
  onClose: () => void;
  filename: string;
  title?: string;
}

export function PDFPreview({ isOpen, onClose, filename, title }: PDFPreviewProps) {
  const [pdfUrl, setPdfUrl] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string>("");

  useEffect(() => {
    if (isOpen && filename) {
      loadPDF();
    }
    return () => {
      if (pdfUrl) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [isOpen, filename]);

  const loadPDF = async () => {
    setIsLoading(true);
    setError("");
    
    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000/api';
      const requestUrl = `${apiBaseUrl}/documents/file/${encodeURIComponent(filename)}`;
      
      const response = await fetch(requestUrl);

      if (!response.ok) {
        throw new Error(`Failed to load PDF: ${response.status} ${response.statusText}`);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      setPdfUrl(url);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load PDF';
      setError(errorMessage);
      toast.error(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDownload = () => {
    if (pdfUrl) {
      const link = document.createElement('a');
      link.href = pdfUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      toast.success('PDF download started');
    }
  };

  const handleOpenInNewTab = () => {
    if (pdfUrl) {
      window.open(pdfUrl, '_blank');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex justify-center items-center">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl max-h-[80vh] m-4 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white rounded-t-lg">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              {title || "Contract Note Preview"}
            </h2>
            <p className="text-sm text-gray-600">{filename}</p>
          </div>
          
          <div className="flex items-center space-x-2">
            {pdfUrl && !error && (
              <>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleOpenInNewTab}
                  title="Open in new tab"
                >
                  <ExternalLink className="h-4 w-4" />
                </Button>
                
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleDownload}
                >
                  <Download className="h-4 w-4" />
                </Button>
              </>
            )}
            
            <Button variant="secondary" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* PDF Content */}
        <div className="flex-1 overflow-hidden bg-gray-100 rounded-b-lg">
          {isLoading && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Loading PDF...</p>
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="bg-red-50 border border-red-200 rounded-lg p-6 max-w-md mx-auto">
                  <h3 className="text-red-800 font-medium mb-2">Failed to Load PDF</h3>
                  <p className="text-red-600 text-sm">{error}</p>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={loadPDF}
                    className="mt-4"
                  >
                    Try Again
                  </Button>
                </div>
              </div>
            </div>
          )}

          {pdfUrl && !error && !isLoading && (
            <iframe
              src={pdfUrl}
              className="w-full h-full border-0"
              title={`PDF Preview - ${filename}`}
            />
          )}
        </div>
      </div>
    </div>
  );
}
