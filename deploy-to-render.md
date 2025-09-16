# 🚀 Deploying Supervity AP Command Center to Render

## 📋 Pre-Deployment Checklist

- [ ] GitHub repository is public or connected to Render
- [ ] Google Gemini API key is ready
- [ ] Render account is created
- [ ] All code is committed and pushed to GitHub

## 🗄️ Step 1: Create PostgreSQL Database

1. **Log into Render Dashboard**
   - Go to [render.com](https://render.com) and sign in

2. **Create New PostgreSQL Database**
   - Click "New +" → "PostgreSQL"
   - **Name**: `supervity-bank-cc-postgres`
   - **Database Name**: `supervity_bank_cc`
   - **User**: `supervity_bank_cc_user`
   - **Region**: Choose closest to your users
   - **Plan**: Start with "Starter" ($7/month)
   - Click "Create Database"

3. **Save Database Connection Details**
   - Once created, note the **Internal Database URL** and **External Database URL**
   - You'll need the Internal URL for the backend service

## 🔧 Step 2: Deploy Backend API

1. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - **Name**: `supervity-backend`
   - **Region**: Same as database
   - **Branch**: `main` (or your default branch)
   - **Root Directory**: Leave empty (uses project root)
   - **Runtime**: Docker
   - **Plan**: Start with "Starter" ($7/month)

2. **Configure Build Settings**
   - **Docker Command**: Leave empty (uses Dockerfile)
   - **Dockerfile Path**: `./Dockerfile`

3. **Set Environment Variables**
   ```bash
   # Required Variables
   DATABASE_URL=<Internal Database URL from Step 1>
   GEMINI_API_KEY=<Your Google Gemini API Key>
   
   # Configuration
   APP_ENV=production
   CORS_ORIGINS=https://supervity-frontend.onrender.com
   PDF_STORAGE_PATH=./sample_data
   GENERATED_PDF_STORAGE_PATH=./generated_documents
   
   # Optional Performance Tuning
   GUNICORN_LOG_LEVEL=info
   GUNICORN_TIMEOUT=120
   WEB_CONCURRENCY=1
   ```

4. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (5-10 minutes)
   - Check logs for any errors
   - Test health endpoint: `https://your-backend-url.onrender.com/api/health`

## 🎨 Step 3: Deploy Frontend

1. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - **Name**: `supervity-frontend`
   - **Region**: Same as backend
   - **Branch**: `main`
   - **Root Directory**: `supervity-ap-frontend`
   - **Runtime**: Docker
   - **Plan**: Start with "Starter" ($7/month)

2. **Configure Build Settings**
   - **Docker Command**: Leave empty
   - **Dockerfile Path**: `./Dockerfile`

3. **Set Environment Variables**
   ```bash
   # Required
   NEXT_PUBLIC_API_BASE_URL=https://supervity-backend.onrender.com/api
   NODE_ENV=production
   
   # Optional
   NEXT_PUBLIC_API_TIMEOUT=30000
   NEXT_PUBLIC_ENABLE_DEBUG=false
   ```

4. **Deploy**
   - Click "Create Web Service"
   - Wait for deployment (5-10 minutes)
   - Test frontend: `https://your-frontend-url.onrender.com`

## 🔄 Step 4: Update CORS Configuration

1. **Update Backend CORS**
   - Go to your backend service settings
   - Update `CORS_ORIGINS` environment variable with your actual frontend URL:
   ```bash
   CORS_ORIGINS=https://your-actual-frontend-url.onrender.com
   ```
   - Redeploy the backend service

## 🧪 Step 5: Test Deployment

1. **Access the Application**
   - Frontend: `https://your-frontend-url.onrender.com`
   - Backend API Docs: `https://your-backend-url.onrender.com/docs`
   - Health Check: `https://your-backend-url.onrender.com/api/health`

2. **Test Key Features**
   - [ ] User registration/login
   - [ ] Document upload
   - [ ] AI processing (requires Gemini API key)
   - [ ] Dashboard data loading
   - [ ] Database connectivity

3. **Default Login Credentials**
   - **Email**: `admin@supervity.ai`
   - **Password**: `SupervityAdmin123!`

## 🔧 Step 6: Production Optimizations

### Database Optimization
- Consider upgrading to "Standard" plan for better performance
- Enable connection pooling if needed
- Set up automated backups

### Backend Optimization
```bash
# Add these environment variables for better performance
WEB_CONCURRENCY=2  # Increase for higher traffic
WORKER_CONNECTIONS=1000
GUNICORN_TIMEOUT=300  # Increase for large file processing
```

### Frontend Optimization
- Enable Render's CDN for static assets
- Consider upgrading plan for better performance

## 🔍 Troubleshooting

### Common Issues

**Backend Won't Start**
- Check environment variables are set correctly
- Verify DATABASE_URL format
- Check build logs for Python dependency issues
- Ensure GEMINI_API_KEY is valid

**Frontend Can't Connect to Backend**
- Verify NEXT_PUBLIC_API_BASE_URL is correct
- Check CORS_ORIGINS on backend includes frontend URL
- Test backend health endpoint directly

**Database Connection Issues**
- Use Internal Database URL for backend service
- Check database is in same region as backend
- Verify database credentials

**File Upload Issues**
- Render has ephemeral storage - files are lost on restart
- Consider using external storage (AWS S3, Cloudinary) for production
- Current setup works for testing but not production persistence

### Viewing Logs
- Go to service dashboard
- Click "Logs" tab
- Filter by error level
- Check both build and runtime logs

## 💰 Cost Estimation

**Monthly Costs (Starter Plans)**:
- PostgreSQL Database: $7/month
- Backend Web Service: $7/month  
- Frontend Web Service: $7/month
- **Total**: ~$21/month

**For Production**:
- Consider "Standard" plans for better performance
- Add Redis for caching if needed
- External storage for file persistence

## 🔄 Continuous Deployment

Render automatically deploys when you push to your connected branch:
1. Push changes to GitHub
2. Render detects changes
3. Automatically rebuilds and deploys
4. Zero-downtime deployment

## 📚 Additional Resources

- [Render Documentation](https://render.com/docs)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Next.js Deployment](https://nextjs.org/docs/deployment)
- [PostgreSQL on Render](https://render.com/docs/databases)

## 🆘 Getting Help

If you encounter issues:
1. Check Render service logs
2. Verify all environment variables
3. Test components individually
4. Check GitHub repository connectivity
5. Contact Render support if needed
