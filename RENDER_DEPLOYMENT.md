# Render Deployment Guide

This guide will help you deploy the Collection Command Center to Render.

## Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **GitHub Repository**: Your code should be in a GitHub repository
3. **Gemini API Key**: Get from [Google AI Studio](https://aistudio.google.com/)

## Database Configuration

✅ **Database URL Updated**: The project is already configured with your Render PostgreSQL database:
```
postgresql://supervity_bank_cc_user:NsDeBXq4iyl1mqfY57GJB8y0QQ4aFsWm@dpg-d34eftruibrs73af3ntg-a/supervity_bank_cc
```

## Deployment Steps

### 1. Push Code to GitHub
```bash
git add .
git commit -m "Configure for Render deployment"
git push origin main
```

### 2. Create Web Service on Render

1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `collection-command-center`
   - **Environment**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn -c gunicorn/prod.py app.main:app`

### 3. Set Environment Variables

In the Render dashboard, add these environment variables:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | `postgresql://supervity_bank_cc_user:NsDeBXq4iyl1mqfY57GJB8y0QQ4aFsWm@dpg-d34eftruibrs73af3ntg-a/supervity_bank_cc` |
| `GEMINI_API_KEY` | `your_gemini_api_key_here` |
| `APP_ENV` | `production` |
| `CORS_ORIGINS` | `*` |
| `PYTHONPATH` | `/opt/render/project/src` |

### 4. Deploy

1. Click **"Create Web Service"**
2. Render will automatically build and deploy your application
3. Monitor the build logs for any issues

## Alternative: Using render.yaml

You can also use the included `render.yaml` file for Infrastructure as Code deployment:

1. In your Render dashboard, go to **"Blueprint"**
2. Click **"New Blueprint Instance"**
3. Connect your repository
4. Render will read the `render.yaml` file automatically

**Note**: You'll still need to set the `GEMINI_API_KEY` environment variable manually in the Render dashboard.

## Post-Deployment

### 1. Verify Database Connection
Your application will automatically:
- Run database migrations (`alembic upgrade head`)
- Initialize configuration data
- Create necessary directories

### 2. Access Your Application
- Your app will be available at: `https://collection-command-center.onrender.com`
- API documentation: `https://collection-command-center.onrender.com/docs`

### 3. Test Key Features
1. **Health Check**: Visit `/api/health`
2. **Authentication**: Try logging in
3. **File Upload**: Test document processing
4. **AI Features**: Ensure Gemini API is working

## Troubleshooting

### Common Issues

1. **Build Fails**: Check that all dependencies in `packages/requirements.txt` are correct
2. **Database Connection**: Verify the DATABASE_URL is correct
3. **Gemini API**: Ensure GEMINI_API_KEY is set and valid
4. **File Permissions**: The build script should be executable (already configured)

### Logs
- View logs in the Render dashboard under your service
- Look for startup errors or database connection issues

### Environment Variables
If you need to update environment variables:
1. Go to your service in Render dashboard
2. Click **"Environment"** tab
3. Add/modify variables
4. Click **"Save Changes"** (this will trigger a redeploy)

## Frontend Deployment (Optional)

If you want to deploy the frontend separately:

1. Create another web service for the frontend
2. Point to the `supervity-ap-frontend` directory
3. Set `NEXT_PUBLIC_API_BASE_URL` to your backend URL
4. Use Node.js environment

## Support

If you encounter issues:
1. Check the Render build/runtime logs
2. Verify all environment variables are set correctly
3. Ensure your database is accessible from Render's IP ranges
4. Test the application locally first with the same environment variables
