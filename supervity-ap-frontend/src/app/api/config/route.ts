import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || "http://127.0.0.1:8000/api",
    apiTimeout: process.env.NEXT_PUBLIC_API_TIMEOUT || "30000",
    enableDebug: process.env.NEXT_PUBLIC_ENABLE_DEBUG === "true",
  });
} 