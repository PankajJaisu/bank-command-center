// PDF.js configuration - centralized to avoid conflicts
import { pdfjs } from "react-pdf";

// Configure PDF.js worker once globally
if (typeof window !== "undefined" && !pdfjs.GlobalWorkerOptions.workerSrc) {
  // Use CDN version to avoid module resolution issues
  pdfjs.GlobalWorkerOptions.workerSrc = "https://unpkg.com/pdfjs-dist@5.3.31/build/pdf.worker.min.js";
  console.log("PDF.js worker configured:", pdfjs.GlobalWorkerOptions.workerSrc);
}

export { pdfjs };
