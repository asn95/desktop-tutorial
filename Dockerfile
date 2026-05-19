FROM python:3.12-slim

# Install Node.js for frontend build
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Build frontend
COPY frontend/package.json frontend/package-lock.json frontend/
RUN cd frontend && npm install

COPY frontend/ frontend/
RUN cd frontend && npm run build

# Copy the rest
COPY backend/ backend/
COPY mini-app/ mini-app/
COPY .env.example .env.example

# Create uploads directory
RUN mkdir -p backend/uploads

EXPOSE 8000

CMD sh -c "python -m uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"
