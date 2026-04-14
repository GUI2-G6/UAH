# ============================================================
# UAH Frontend — Dockerfile (DEV)
# ============================================================
# Two-stage build:
#   1. Node — install deps and build the Vue 3 app
#   2. Nginx — serve the static build output
# ============================================================

# --- Stage 1: Build ---
FROM node:20-alpine AS build

WORKDIR /app/frontend

# Install dependencies (layer caching)
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

# Copy the frontend app and the shared theme assets it imports.
COPY frontend/ ./
COPY shared/ ../shared/
ARG VITE_AUTH_NAMESPACE
ARG VITE_LOCAL_MODE=backend
ENV VITE_AUTH_NAMESPACE=${VITE_AUTH_NAMESPACE}
ENV VITE_LOCAL_MODE=${VITE_LOCAL_MODE}
RUN npm run build

# --- Stage 2: Serve ---
FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy nginx templates and startup selector script
COPY frontend/nginx.http.conf /etc/nginx/templates/nginx.http.conf
COPY frontend/nginx.https.conf /etc/nginx/templates/nginx.https.conf
COPY frontend/docker-entrypoint.d/10-select-nginx-config.sh /docker-entrypoint.d/10-select-nginx-config.sh
RUN chmod +x /docker-entrypoint.d/10-select-nginx-config.sh

# Copy built assets from stage 1
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]

