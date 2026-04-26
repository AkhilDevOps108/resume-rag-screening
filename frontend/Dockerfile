# Build stage
FROM node:16-alpine AS builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY public ./public
COPY src ./src

# Build React app
RUN npm run build

# Production stage
FROM node:16-alpine

WORKDIR /app

# Install serve to run React app
RUN npm install -g serve

# Copy built app from builder
COPY --from=builder /app/build ./build
COPY --from=builder /app/public ./public

# Expose port
EXPOSE 3000

# Environment
ENV REACT_APP_API_URL=http://localhost:8000/api
ENV NODE_ENV=production

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:3000 || exit 1

# Start app
CMD ["serve", "-s", "build", "-l", "3000"]
