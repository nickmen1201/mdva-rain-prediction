# =============================================================================
# Frontend/Dockerfile — React + Vite (build estático servido con nginx)
# =============================================================================
# Etapa 1: build con Node
FROM node:24-alpine AS builder

WORKDIR /app

# Instalar dependencias primero (cache de capas)
COPY package.json package-lock.json ./
RUN npm ci

# Copiar código fuente y variables de entorno
COPY . .

# Build de producción
RUN npm run build

# =============================================================================
# Etapa 2: servir con nginx
FROM nginx:alpine AS runtime

RUN apk add --no-cache openssl \
    && mkdir -p /etc/nginx/certs \
    && openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
      -keyout /etc/nginx/certs/mdva-dev.key \
      -out /etc/nginx/certs/mdva-dev.crt \
      -subj "/CN=mdva-dev"

# Copiar el build generado
COPY --from=builder /app/dist /usr/share/nginx/html

# Configuración de nginx para SPA (React Router)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
