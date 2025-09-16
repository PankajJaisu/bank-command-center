# Stage 1: Install dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
COPY copy-pdf-worker.js ./
RUN npm install

# Run the PDF worker copy script after dependencies are installed
RUN node copy-pdf-worker.js

# Stage 2: Build the application
FROM node:20-alpine AS builder
WORKDIR /app

# Accept build arguments that will be used as environment variables
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
ARG NEXT_PUBLIC_API_TIMEOUT=30000
ARG NEXT_PUBLIC_ENABLE_DEBUG=false

# Set environment variables for build time
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_TIMEOUT=$NEXT_PUBLIC_API_TIMEOUT
ENV NEXT_PUBLIC_ENABLE_DEBUG=$NEXT_PUBLIC_ENABLE_DEBUG

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Copy the generated PDF worker files from the deps stage to ensure they're included
# This overwrites any existing files in the source public directory with the correct versions
COPY --from=deps /app/public/pdf.worker.mjs ./public/pdf.worker.mjs

# Build the application with environment variables embedded
RUN npm run build

# Stage 3: Production image
FROM node:20-alpine AS runner
WORKDIR /app

# Install curl for health checks
RUN apk add --no-cache curl

# Set production environment
ENV NODE_ENV=production

# Create a non-root user to run the application
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy built app from builder (using standalone output)
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Switch to non-root user
USER nextjs

EXPOSE 3000

# Health check for the Next.js application
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=40s \
  CMD curl -f http://localhost:3000/ || exit 1

# Use the standalone server directly
CMD ["node", "server.js"] 