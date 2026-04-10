# ============================================================
# UAH Frontend — Dockerfile (DEV)
# ============================================================
# Two-stage build:
#   1. Node — install deps and build the Vue 3 app
#   2. Nginx — serve the static build output
# ============================================================

# --- Stage 1: Build ---
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies (layer caching)
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source and build
COPY . .
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
COPY nginx.http.conf /etc/nginx/templates/nginx.http.conf
COPY nginx.https.conf /etc/nginx/templates/nginx.https.conf
COPY docker-entrypoint.d/10-select-nginx-config.sh /docker-entrypoint.d/10-select-nginx-config.sh
RUN chmod +x /docker-entrypoint.d/10-select-nginx-config.sh

# Copy built assets from stage 1
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]

