# How the live site is built (step 11): Render runs this on every push to main.
# Stage 1 builds the React app; stage 2 is the Python server, which also serves
# that build (main.py), so one server gives the page and the API.

# --- Stage 1: the React app -> frontend/dist -------------------------------------------
FROM node:24-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: the server -------------------------------------------------------------------
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=frontend /app/frontend/dist /app/frontend/dist

# At start: bring every account database up to date (migrate.py), then serve.
# One uvicorn process on purpose: login limits, open databases and report jobs
# live in memory. --proxy-headers: behind Render's proxy, see the visitor's real
# address (for the login-attempt limit). Render sets PORT.
CMD python migrate.py --all && uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000} --proxy-headers --forwarded-allow-ips="*"
