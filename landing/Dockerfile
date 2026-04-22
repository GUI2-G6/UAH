FROM node:20-alpine AS build

WORKDIR /app/landing

COPY landing/package.json landing/package-lock.json* ./
RUN npm ci

COPY landing/ ./
RUN npm run build

FROM nginx:alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY landing/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/landing/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
