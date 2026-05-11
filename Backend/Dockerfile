# =============================================================================
# Backend/Dockerfile — Spring Boot (Java 21)
# Build multietapa: compila con Gradle y genera imagen mínima de runtime
# =============================================================================
# Context: raíz del repositorio (un nivel arriba de /Backend)
# Build:   docker compose -f docker-compose.dev.yml build backend
# =============================================================================

# ── Etapa 1: Build ──────────────────────────────────────────────────────────
FROM eclipse-temurin:21-jdk-alpine AS builder

WORKDIR /workspace

# Copiar Gradle wrapper y archivos de configuración primero (cache de capas)
COPY Backend/gradlew             gradlew
COPY Backend/gradle/             gradle/
COPY Backend/settings.gradle.kts settings.gradle.kts
COPY Backend/build.gradle.kts    build.gradle.kts

# Dar permisos y limpiar line endings Windows (CRLF → LF) para que Alpine pueda ejecutar el script
RUN sed -i 's/\r$//' gradlew && chmod +x gradlew

# Descargar dependencias (cacheado si build.gradle.kts no cambia)
RUN ./gradlew dependencies --no-daemon -q || true

# Copiar el código fuente
COPY Backend/src/ src/

# Compilar y empaquetar (sin tests, sin regenerar JOOQ — el código generado
# ya está en src/main/generated-jooq y se incluye en la compilación)
RUN ./gradlew bootJar --no-daemon -x test -x generateJooq

# ── Etapa 2: Runtime ─────────────────────────────────────────────────────────
FROM eclipse-temurin:21-jre-alpine AS runtime

WORKDIR /app

# wget para el healthcheck (alpine no lo trae)
RUN apk add --no-cache wget

# Copiar el JAR generado
COPY --from=builder /workspace/build/libs/*.jar app.jar

# Exponer el puerto del backend
EXPOSE 8080

# Variables de entorno con defaults (sobreescritas por docker-compose)
ENV SPRING_PROFILES_ACTIVE=dev

# Healthcheck para orquestadores (Docker Swarm, k8s probe-like, mini-server LB)
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/api/health || exit 1

ENTRYPOINT ["java", "-jar", "app.jar"]