# =============================================================================
# Frontend/Dockerfile — React + Vite (build estático servido con nginx)
# =============================================================================
# Etapa 1: build con Node
FROM node:24-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# VITE_API_URL se inyecta como build arg para que Vite lo bake en el bundle
ARG VITE_API_URL=""
ARG VITE_GOOGLE_MAPS_KEY=""
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_GOOGLE_MAPS_KEY=$VITE_GOOGLE_MAPS_KEY

RUN npm run build

# =============================================================================
# Etapa 2: servir con nginx (Railway maneja HTTPS en el edge, no en el contenedor)
FROM nginx:alpine AS runtime

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf.template

RUN apk add --no-cache gettext

ENV PORT=80

EXPOSE 80

CMD ["/bin/sh", "-c", "envsubst '${PORT}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
