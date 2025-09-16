#!/usr/bin/env python3
"""
Test script to diagnose Gemini API connection issues
"""

import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_gemini_connection():
    """Test Gemini API connection and basic functionality"""
    
    print("🔧 Proactive Loan Command Center - Gemini API Connection Test")
    print("=" * 60)
    
    # Test 1: Check environment configuration
    print("\n1️⃣ Testing Environment Configuration...")
    
    try:
        from app.config import settings
        print(f"✅ Settings loaded successfully")
        
        if settings.gemini_api_key:
            key_preview = f"{settings.gemini_api_key[:10]}...{settings.gemini_api_key[-4:]}"
            print(f"✅ API Key found: {key_preview}")
        else:
            print("❌ API Key not found in settings")
            return False
            
        print(f"✅ Model name: {settings.gemini_model_name}")
        
    except Exception as e:
        print(f"❌ Error loading settings: {e}")
        return False
    
    # Test 2: Test Gemini client initialization
    print("\n2️⃣ Testing Gemini Client Initialization...")
    
    try:
        from google import genai
        from google.genai import types
        
        client = genai.Client(api_key=settings.gemini_api_key)
        print("✅ Gemini client created successfully")
        
    except Exception as e:
        print(f"❌ Error creating Gemini client: {e}")
        return False
    
    # Test 3: Test basic API call
    print("\n3️⃣ Testing Basic API Call...")
    
    try:
        # Simple text-only test
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text="Please respond with exactly this JSON: {\"test\": \"success\", \"status\": \"working\"}"
                    )
                ],
            )
        ]
        
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
        )
        
        print("📡 Making test API call...")
        response_text = ""
        for chunk in client.models.generate_content_stream(
            model=settings.gemini_model_name,
            contents=contents,
            config=config,
        ):
            if chunk.text:
                response_text += chunk.text
        
        print(f"✅ API call successful")
        print(f"📄 Response: {response_text}")
        
        # Try to parse JSON
        import json
        try:
            data = json.loads(response_text)
            print("✅ JSON parsing successful")
            print(f"📊 Parsed data: {data}")
        except json.JSONDecodeError as e:
            print(f"⚠️ JSON parsing failed: {e}")
            print(f"Raw response: {response_text}")
        
    except Exception as e:
        print(f"❌ API call failed: {e}")
        print(f"Error type: {type(e).__name__}")
        return False
    
    # Test 4: Test PDF processing capability
    print("\n4️⃣ Testing PDF Processing Capability...")
    
    try:
        # Create a simple test PDF content (minimal)
        test_pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Test Document) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000207 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n301\n%%EOF"
        
        contents_pdf = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(
                        text="Analyze this PDF and return: {\"document_type\": \"test\", \"content\": \"found\"}"
                    ),
                    types.Part.from_bytes(
                        data=test_pdf_content, mime_type="application/pdf"
                    ),
                ],
            )
        ]
        
        print("📡 Making PDF test API call...")
        response_text = ""
        for chunk in client.models.generate_content_stream(
            model=settings.gemini_model_name,
            contents=contents_pdf,
            config=config,
        ):
            if chunk.text:
                response_text += chunk.text
        
        print(f"✅ PDF API call successful")
        print(f"📄 Response: {response_text}")
        
    except Exception as e:
        print(f"⚠️ PDF processing test failed: {e}")
        print("This might be normal - PDF processing requires more complex setup")
    
    print("\n🎉 Connection test completed!")
    print("\n💡 If you're still having issues:")
    print("1. Check that your PDF files are not corrupted")
    print("2. Try with smaller PDF files (< 10MB)")
    print("3. Check the application logs for more detailed error messages")
    print("4. Ensure your Gemini API key has sufficient quota")
    
    return True

if __name__ == "__main__":
    try:
        success = test_gemini_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {e}")
        sys.exit(1)
