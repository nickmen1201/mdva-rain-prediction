# Monitoreo de Variables Ambientales (MDVA)

Proyecto backend para monitorear variables ambientales relacionadas con movilidad urbana en Medellin y el Valle de Aburra.

El servicio expone una API REST para:
- Consultar ubicaciones (municipios, comunas y barrios) desde PostgreSQL.
- Consultar condiciones climaticas actuales por coordenadas usando Open-Meteo.
- Verificar estado del servicio y documentar endpoints con Swagger/OpenAPI.

## Tabla de contenido

1. [Descripcion general](#descripcion-general)
2. [Stack tecnologico](#stack-tecnologico)
3. [Estructura del repositorio](#estructura-del-repositorio)
4. [Prerequisitos](#prerequisitos)
5. [Configuracion de base de datos](#configuracion-de-base-de-datos)
6. [Ejecucion del proyecto](#ejecucion-del-proyecto)
7. [API y endpoints](#api-y-endpoints)
8. [Perfiles y configuracion](#perfiles-y-configuracion)
9. [Pruebas](#pruebas)
10. [jOOQ y codigo generado](#jooq-y-codigo-generado)
11. [Troubleshooting](#troubleshooting)

## Descripcion general

Este repositorio contiene principalmente un backend en Spring Boot ubicado en `Backend/`.

Capacidades actuales:
- API REST con validaciones de entrada.
- Integracion con PostgreSQL mediante jOOQ.
- Endpoint de clima actual por latitud/longitud.
- Endpoint de health check.
- Swagger UI y OpenAPI JSON.

## Stack tecnologico

- Java 21
- Spring Boot 3.4.2
- Gradle 9.2.0 (wrapper)
- PostgreSQL
- jOOQ 3.19.18
- springdoc-openapi 2.7.0
- Lombok
- MapStruct

## Estructura del repositorio

```text
Monitoreo-de-variables-ambientales/
|-- README.md
`-- Backend/
    |-- build.gradle.kts
    |-- gradlew
    |-- gradlew.bat
    |-- DB/
    |   |-- init.sql
    |   |-- TIC1DB.sql
    |   `-- TIC1DB.backup
    |-- src/main/java/ti/mdva/
    |   |-- BackendApplication.java
    |   |-- controller/
    |   |-- service/
    |   |-- dto/
    |   |-- config/
    |   `-- exception/
    `-- src/main/resources/
        |-- application.yml
        |-- application-dev.yml
        `-- application-prod.yml
```

## Prerequisitos

Instala lo siguiente antes de iniciar:

1. JDK 21
2. PostgreSQL (14 o superior recomendado)
3. Gradle no es obligatorio (se usa wrapper `gradlew`)

Verificaciones utiles:

```bash
java -version
```

## Configuracion de base de datos

La app por defecto usa:
- Base de datos: `mdva`
- Host: `localhost`
- Puerto: `5432`
- Usuario por defecto: `postgres`

### 1) Crear la base

```sql
CREATE DATABASE mdva;
```

### 2) Inicializar esquema y datos

Ejecuta el script:
- `Backend/DB/init.sql`

Ese script:
- Crea tablas principales (`municipios`, `comunas`, `barrios`, `usuarios`, `vehiculos`, `viajes`, etc.).
- Inserta datos semilla de municipios/comunas/barrios y tipos de vehiculo/motor.
- Crea indices para consultas frecuentes.

## Ejecucion del proyecto

Desde la raiz del repositorio:

### Windows (PowerShell)

```powershell
cd Backend
.\gradlew.bat bootRun
```

### Linux/Mac

```bash
cd Backend
./gradlew bootRun
```

Servicio disponible en:
- Base URL: `http://localhost:8080`
- Health: `http://localhost:8080/api/health`

## API y endpoints

Prefijo principal: `/api`

### Health

- `GET /api/health`

Respuesta esperada:

```json
{
  "status": "UP",
  "service": "mdva-backend",
  "timestamp": "2026-03-12T22:30:00Z"
}
```

### Ubicaciones

- `GET /api/locations/municipalities`
- `GET /api/locations/municipalities/{id}/communes`
- `GET /api/locations/communes/{id}/neighborhoods`

Ejemplos:

```bash
curl http://localhost:8080/api/locations/municipalities
curl http://localhost:8080/api/locations/municipalities/MED/communes
curl http://localhost:8080/api/locations/communes/MED14/neighborhoods
```

### Clima actual

- `GET /api/weather/current?latitude=6.2442&longitude=-75.5812`
- `POST /api/weather/current`

Ejemplo `POST`:

```bash
curl -X POST http://localhost:8080/api/weather/current \
  -H "Content-Type: application/json" \
  -d '{"latitude":6.2442,"longitude":-75.5812}'
```

Campos esperados para `POST /api/weather/current`:
- `latitude`: requerido, rango `[-90, 90]`
- `longitude`: requerido, rango `[-180, 180]`

## Documentacion interactiva

Con la app ejecutandose:
- Swagger UI: `http://localhost:8080/swagger-ui.html`
- OpenAPI JSON: `http://localhost:8080/api-docs`

## Perfiles y configuracion

Archivos:
- `Backend/src/main/resources/application.yml`
- `Backend/src/main/resources/application-dev.yml`
- `Backend/src/main/resources/application-prod.yml`

### Perfil por defecto

Usa `application.yml` con configuracion local de datasource.

### Ejecutar con perfil `dev`

```powershell
cd Backend
.\gradlew.bat bootRun --args="--spring.profiles.active=dev"
```

### Ejecutar con perfil `prod`

Variables requeridas:
- `DATABASE_URL`
- `DATABASE_USERNAME`
- `DATABASE_PASSWORD`

Ejemplo en PowerShell:

```powershell
$env:DATABASE_URL="jdbc:postgresql://localhost:5432/mdva"
$env:DATABASE_USERNAME="postgres"
$env:DATABASE_PASSWORD="tu_password"
cd Backend
.\gradlew.bat bootRun --args="--spring.profiles.active=prod"
```

## Pruebas

Desde `Backend/`:

### Windows

```powershell
.\gradlew.bat test
```

### Linux/Mac

```bash
./gradlew test
```

## jOOQ y codigo generado

El proyecto usa plugin jOOQ configurado en `Backend/build.gradle.kts`.

Regenerar clases jOOQ:

```powershell
cd Backend
.\gradlew.bat generateJooq
```

Nota importante:
- En esta rama, la salida de jOOQ esta configurada a `src/main/java`.

## Troubleshooting

1. Error de conexion a PostgreSQL
- Verifica que PostgreSQL este arriba en `localhost:5432`.
- Confirma usuario/password en `application.yml` o variables de entorno.

2. Endpoints de ubicaciones retornan vacio
- Asegura que ejecutaste `Backend/DB/init.sql` en la base `mdva`.

3. `POST /api/weather/current` devuelve 400
- Revisa que `latitude` y `longitude` esten dentro de rango.

4. Error por version de Java
- Ejecuta con JDK 21 para coincidir con `build.gradle.kts`.

## Estado actual

El backend esta listo para integrarse con frontend web o app movil como proveedor de:
- Catalogo geografico administrativo.
- Clima actual por coordenadas.
- Endpoints de observabilidad basica.
