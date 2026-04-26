# Build backend
FROM python:3.9-slim as backend-builder

WORKDIR /app/backend

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend .

# Build frontend
FROM node:16-alpine as frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci --only=production

COPY frontend .

# Build React app
RUN npm run build

# Final production image
FROM python:3.9-slim

WORKDIR /app

# Copy backend
COPY --from=backend-builder /app/backend ./backend
RUN cd backend && pip install --no-cache-dir -r requirements.txt

# Copy frontend build
COPY --from=frontend-builder /app/frontend/build ./frontend/build

# Copy public folder for static files
COPY --from=frontend-builder /app/frontend/public ./frontend/public

# Expose ports
EXPOSE 8000 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/api/health')"

# Run backend
CMD ["python", "backend/app.py"]
