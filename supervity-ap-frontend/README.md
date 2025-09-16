# Supervity Proactive Loan Command Center - Frontend

This is the frontend application for the **Supervity AI Accounts Payable Command Center**, built with Next.js 15 and React 19.

## 🚀 Tech Stack

- **Next.js 15** - React framework with App Router
- **React 19** - Latest React with improved performance  
- **TypeScript** - Type safety and better developer experience
- **Tailwind CSS 4** - Utility-first styling framework
- **Zod** - Runtime type validation
- **React Hot Toast** - Elegant notification system
- **Recharts** - Powerful data visualization
- **React PDF** - PDF viewing capabilities

## 📱 Application Features

### 🏠 **Dashboard**
- Role-based dashboard views (Admin vs AP Processor)
- Real-time KPIs and performance metrics
- Interactive charts and analytics
- Team performance leaderboards

### 🔧 **Resolution Workbench**
- Side-by-side invoice and document comparison
- Exception handling and approval workflows
- Audit trail and comment system
- Batch operations for efficiency

### 🤖 **AI Copilot**
- Conversational AI assistant
- Natural language query processing
- Automated action execution
- Smart insights and recommendations

### ⚙️ **Configuration & Management**
- User role management with dynamic updates
- Automation rule builder
- SLA policy configuration
- Vendor settings management

### 📊 **Analytics & Insights**
- AI-powered process improvement suggestions
- Exception analysis and trending
- Vendor performance tracking
- Export capabilities (CSV/XLSX)

## 🛠️ Development Setup

### Prerequisites
- Node.js 18+ and npm
- Backend API running on port 8000

### Installation

1. **Install Dependencies:**
   ```bash
   npm install
   ```

2. **Environment Configuration:**
   ```bash
   # Create environment file (optional for local dev)
   cp env.example .env.local
   
   # Set API base URL if different from default
   NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
   ```

3. **Start Development Server:**
   ```bash
   npm run dev
   ```

4. **Access Application:**
   - Frontend: [http://localhost:3000](http://localhost:3000)
   - Ensure backend is running on [http://localhost:8000](http://localhost:8000)

## 📁 Project Structure

```
src/
├── app/                        # Next.js App Router
│   ├── dashboard/             # Main dashboard page
│   ├── resolution-workbench/  # Invoice processing interface
│   ├── ai-insights/           # AI-powered insights
│   ├── ai-policies/           # Configuration & settings
│   ├── invoice-explorer/      # Invoice search & management
│   ├── document-hub/          # Document upload center
│   ├── login/                 # Authentication pages
│   └── signup/                # User registration
├── components/                 # Reusable components
│   ├── dashboard/             # Dashboard-specific widgets
│   ├── workbench/             # Resolution workbench components
│   ├── settings/              # Configuration forms
│   ├── shared/                # Common components
│   └── ui/                    # Base UI components
└── lib/                        # Utilities
    ├── api.ts                 # Type-safe API client
    ├── AppContext.tsx         # React context
    └── utils.ts               # Helper functions
```

## 🔧 Available Scripts

```bash
# Development
npm run dev          # Start development server with Turbopack
npm run build        # Build for production
npm run start        # Start production server
npm run lint         # Run ESLint

# Utilities
npm run postinstall  # Copy PDF worker (runs automatically after install)
```

## 🎨 Design System

The application uses a consistent design system with:

- **Color Palette:** Subtle, professional colors optimized for financial workflows
- **Typography:** Clear, readable fonts with proper hierarchy
- **Spacing:** Consistent spacing scale using Tailwind
- **Components:** Reusable, accessible UI components
- **Responsive Design:** Mobile-first approach with breakpoint optimization

## 🔌 API Integration

The frontend communicates with the FastAPI backend through a type-safe API client (`src/lib/api.ts`) that provides:

- **Authentication:** JWT token management
- **Type Safety:** Zod schema validation for all responses
- **Error Handling:** Consistent error handling and user feedback
- **Real-time Updates:** WebSocket support for live data
- **Caching:** Optimized data fetching and caching strategies

## 📱 User Experience Features

### 🔐 **Authentication & Security**
- Secure login/signup flows
- Role-based UI rendering
- Session management
- Auto-logout on token expiry

### 🎯 **Performance Optimizations**
- **Code Splitting:** Automatic route-based splitting
- **Image Optimization:** Next.js Image component
- **Lazy Loading:** Components loaded on demand
- **Caching:** Strategic caching for better performance

### ♿ **Accessibility**
- **Keyboard Navigation:** Full keyboard support
- **Screen Reader:** ARIA labels and semantic HTML
- **Color Contrast:** WCAG compliant color schemes
- **Focus Management:** Proper focus handling

## 🚀 Production Deployment

### Build for Production
```bash
npm run build
npm run start
```

### Docker Deployment
The frontend is containerized and deploys alongside the backend. See the main [README.md](../README.md) for full deployment instructions.

### Environment Variables
```bash
NEXT_PUBLIC_API_BASE_URL=http://your-backend-api-url/api
```

## 🔍 Troubleshooting

### Common Issues

**Build Errors:**
- Ensure all dependencies are installed: `npm install`
- Clear Next.js cache: `rm -rf .next`

**API Connection Issues:**
- Verify backend is running on correct port
- Check CORS settings in backend
- Confirm API base URL is correct

**PDF Viewing Issues:**
- PDF worker is automatically copied during install
- Check browser console for worker loading errors

### Development Tips

1. **Hot Reloading:** Uses Turbopack for faster development builds
2. **Type Safety:** Always validate API responses with Zod schemas  
3. **Component Testing:** Use React DevTools for component inspection
4. **Network Debugging:** Browser DevTools Network tab for API debugging

---

For the complete application documentation, see the main [README.md](../README.md) in the project root.
