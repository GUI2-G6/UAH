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
RUN npm run build

# --- Stage 2: Serve ---
FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our custom config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from stage 1
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

