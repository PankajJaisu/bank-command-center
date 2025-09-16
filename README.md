# Supervity AI Proactive Loan Command Center

Welcome to the **Supervity AI Accounts Payable Command Center**, a comprehensive, intelligent platform designed to automate and streamline the entire invoice processing lifecycle. This application transforms traditional AP workflows into a proactive, multi-user command center with advanced role-based access control, automated policy enforcement, and AI-powered assistance.

## ✨ Core Features

### 🔐 **Advanced User Management & Security**
- **Role-Based Access Control (RBAC):** Secure multi-user environment with distinct **Admin** and **AP Processor** roles
- **Smart User Registration:** @supervity.ai users get instant admin access; others require approval
- **Dynamic Role Management:** Admins can promote users to co-admin status with real-time updates
- **Granular Permission Policies:** Create complex, multi-condition rules to control invoice access per user

### 🤖 **AI-Powered Automation**
- **Intelligent Document Processing:** AI-powered data extraction from Invoices, Purchase Orders, and GRNs using Google Gemini
- **Automated 3-Way Matching:** Robust validation engine checking quantities, prices, and items across documents
- **AI Copilot Assistant:** Conversational AI that can analyze data, execute actions, and provide strategic insights
- **Adaptive Learning Engine:** System learns from user actions to suggest and create automation rules
- **Smart Exception Handling:** Automatically flags and categorizes discrepancies for review

### 📊 **Comprehensive Analytics & Dashboards**
- **Role-Based Dashboards:** Customized views for admins (team overview) and processors (personal queue)
- **Real-Time KPIs:** Track touchless processing rates, exception handling times, and vendor performance
- **AI Insights Page:** Discover automation opportunities and process improvement suggestions
- **Exception Analytics:** Interactive charts showing root causes and trending issues
- **Vendor Performance Tracking:** Automatic ranking by exception rates and payment compliance

### ⚡ **Advanced Workflow Management**
- **Resolution Workbench:** Dedicated interface for resolving flagged invoices with side-by-side document comparison
- **Dynamic Hold System:** Temporarily pause invoices while waiting for documents or approvals
- **Service Level Agreements (SLAs):** Define processing time targets with automated breach alerts
- **Audit Trail:** Complete history of all actions for compliance and transparency
- **Batch Operations:** Process multiple invoices simultaneously for efficiency

### 📄 **Document & Data Management**
- **Flexible Document Ingestion:** Drag-and-drop upload or automated sync from external sources
- **Professional Data Export:** Export filtered data to CSV or multi-sheet XLSX with complete document sets
- **Document Version Control:** Track changes to purchase orders and maintain document history
- **PDF Generation:** Automatically create and regenerate POs with proper formatting

### 🔧 **Configuration & Automation**
- **Automation Rules Manager:** Create IF-THEN rules for automatic invoice processing
- **Vendor Settings:** Configure tolerance levels and contact information per vendor
- **SLA Policy Management:** Define and monitor processing time agreements
- **Field Configuration:** Customize data extraction fields per document type
- **Payment Processing:** Batch payment creation and tracking

For a complete feature breakdown, see [FEATURES.md](./FEATURES.md).

## 🚀 Quick Start Guide

### Prerequisites
- **Docker & Docker Compose** (recommended) *or* Python 3.10+ and Node.js
- **Google Gemini API Key** - Get yours from [Google AI Studio](https://aistudio.google.com/app/apikey)

### 🐳 Docker Setup (Recommended)

For detailed Docker instructions, see [DOCKER_GUIDE.md](./DOCKER_GUIDE.md).

1. **Quick Start:**
   ```bash
   git clone <your-repository-url>
   cd ap-command-center
   
   # Build and start with Docker (replace with your actual API key)
   docker build -t supervity-backend .
   docker build -t supervity-frontend ./supervity-ap-frontend
   
   # Create network and start containers
   docker network create supervity-network
   docker run -d --name supervity-backend --network supervity-network -p 8000:8000 \
     -e GEMINI_API_KEY="your_api_key_here" supervity-backend
   docker run -d --name supervity-frontend --network supervity-network -p 3000:3000 \
     -e NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api supervity-frontend
   ```

2. **Access the Application:**
   - **Main App:** [http://localhost:3000](http://localhost:3000)
   - **API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)

### 💻 Local Development Setup

1. **Backend Setup:**
   ```bash
   # Create virtual environment
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r packages/requirements.txt
   
   # Start backend
   python run_fresh.py  # First time
   # or python run.py    # Subsequent runs
   ```

2. **Frontend Setup (separate terminal):**
   ```bash
   cd supervity-ap-frontend
   npm install
   npm run dev
   ```

### 🔑 Default Login Credentials

The system creates a default admin account:
- **Email:** `admin@supervity.ai`
- **Password:** `SupervityAdmin123!`

**Note:** Users with `@supervity.ai` email domains automatically receive admin privileges and are instantly approved.

### 📊 Sample Data Setup

1. **Generate Test Data:**
   ```bash
   python scripts/data_generator.py
   ```

2. **Upload Documents:**
   - Navigate to **Data Center** → Click "Sync Sample Data"
   - Upload `pos.json` and `grns.csv` from `sample_data/` directory

3. **Start Processing:**
   - Go to **Resolution Workbench** to review flagged invoices
   - Try the **AI Copilot** with queries like "Show me KPI summary" or "What's wrong with invoice INV-123?"

## 🏗️ Architecture Overview

### Backend (FastAPI + SQLAlchemy)
```
src/app/
├── main.py                     # Application entry point
├── config.py                   # Configuration management  
├── api/endpoints/              # REST API endpoints
│   ├── auth.py                # Authentication & user registration
│   ├── users.py               # User management & role changes
│   ├── dashboard.py           # Dashboard data & analytics
│   ├── copilot.py             # AI assistant interactions
│   ├── documents.py           # Document upload & processing
│   └── ...
├── modules/                    # Core business logic
│   ├── copilot/               # AI agent & tools
│   ├── matching/              # 3-way matching engine
│   ├── ingestion/             # Document processing
│   ├── learning/              # Pattern recognition & insights
│   └── automation/            # Rule execution engine
├── db/                         # Database layer
│   ├── models.py              # SQLAlchemy models
│   └── schemas.py             # Pydantic schemas
└── services/                   # Business services
```

### Frontend (Next.js 15 + React 19)
```
supervity-ap-frontend/src/
├── app/                        # App Router pages
│   ├── dashboard/             # Main dashboard
│   ├── resolution-workbench/  # Invoice processing interface
│   ├── ai-insights/           # Automation opportunities
│   ├── ai-policies/           # Configuration & user management
│   ├── invoice-explorer/      # Search & filter invoices
│   └── document-hub/          # Document upload center
├── components/                 # Reusable UI components
│   ├── dashboard/             # Dashboard widgets
│   ├── workbench/             # Resolution interface
│   ├── settings/              # Configuration forms
│   └── ui/                    # Base UI components
└── lib/                        # Utilities & API client
    ├── api.ts                 # Type-safe API functions
    ├── AppContext.tsx         # React context providers
    └── utils.ts               # Helper functions
```

## 🔧 Key Technologies

### Backend Stack
- **FastAPI** - High-performance async web framework
- **SQLAlchemy** - ORM with PostgreSQL/SQLite support
- **Google Gemini** - AI document processing & conversational agent
- **PyMuPDF** - PDF processing and text extraction
- **Pydantic** - Data validation and serialization
- **bcrypt** - Secure password hashing
- **FastAPI-Mail** - Email notifications

### Frontend Stack  
- **Next.js 15** - React framework with App Router
- **React 19** - Latest React with improved performance
- **TypeScript** - Type safety and better DX
- **Tailwind CSS 4** - Utility-first styling
- **Zod** - Runtime type validation
- **React Hot Toast** - Notification system
- **Recharts** - Data visualization
- **React PDF** - PDF viewing capabilities

## 🔧 Configuration

### Environment Variables
```bash
# Required
GEMINI_API_KEY="your_gemini_api_key"
DATABASE_URL="sqlite:///./ap_data.db"

# Optional  
CORS_ORIGINS="http://localhost:3000"
PDF_STORAGE_PATH="./sample_data"
GENERATED_PDF_STORAGE_PATH="./generated_documents"
```

### System Configuration
- **User Roles:** Admin, AP Processor  
- **Permission Policies:** Vendor-based, amount-based, date-based filtering
- **SLA Policies:** Configurable processing time targets
- **Automation Rules:** IF-THEN conditions for auto-processing
- **Vendor Settings:** Tolerance levels and contact information

## 🛑 Management Commands

```bash
# Stop Docker containers
docker stop supervity-backend supervity-frontend
docker rm supervity-backend supervity-frontend

# View logs
docker logs supervity-backend
docker logs supervity-frontend

# Database operations
python scripts/cleanup_db.py    # Reset database
python export_database.py       # Export data

# Available utility scripts
python scripts/data_generator.py      # Generate sample data
python scripts/init_config_data.py    # Initialize configuration
python scripts/verify_test_data.py    # Verify test data integrity
```

## 📚 API Documentation

The complete API documentation is available at `/docs` when the backend is running. Key endpoints include:

- **Authentication:** `/api/auth/` - Login, signup, token management
- **User Management:** `/api/users/` - User operations, role changes
- **Documents:** `/api/documents/` - Upload, processing, search
- **Dashboard:** `/api/dashboard/` - Analytics and KPIs
- **AI Copilot:** `/api/copilot/` - Conversational AI interactions
- **Configuration:** `/api/config/` - System settings and policies

## 🔍 Troubleshooting

### Common Issues

**PDF Processing Fails:**
- Verify your `GEMINI_API_KEY` is correct
- Check backend logs: `docker logs supervity-backend`

**Frontend Can't Connect:**
- Ensure both containers are running: `docker ps`
- Check network connectivity between containers

**Database Issues:**
- Reset database: `rm -f ap_data.db && python run_fresh.py`
- Check SQLite file permissions

**Memory Issues:**
- Increase Docker memory limits for large document processing
- Monitor system resources during bulk uploads

### Getting Help

1. Check the [FEATURES.md](./FEATURES.md) for detailed feature documentation
2. Review API documentation at `/docs`
3. Examine log files for error details
4. Ensure all prerequisites are properly installed

---

## 📄 License

This project is proprietary software developed by Supervity AI.

## 🚀 What's Next?

- **Enterprise SSO Integration** - SAML/OAuth support
- **Advanced Analytics** - Predictive modeling and forecasting  
- **Mobile Application** - iOS/Android apps for on-the-go processing
- **ERP Integrations** - Direct connections to SAP, Oracle, and other systems
- **Advanced OCR** - Enhanced document recognition capabilities# bank-cc
