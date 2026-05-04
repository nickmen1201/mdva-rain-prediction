# MDVA — Enrutamiento Ambiental

Sistema de enrutamiento inteligente para el Valle de Aburrá que **integra variables ambientales** con cálculo de rutas en grafos viales reales.

## Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend React                       │
│                  (Google Maps JS)                       │
└───────────────────────┬─────────────────────────────────┘
                        │
┌───────────────────────▼─────────────────────────────────┐
│              Backend Spring Boot                        │
│           (ViajeUseCase → planificarViaje)              │
│                                                         │
│  Intenta → Enrutamiento Ambiental (puerto 8000)        │
│  Fallback → Google Directions API                       │
└───────────┬───────────────────────────┬─────────────────┘
            │                           │
┌───────────▼───────────┐  ┌────────────▼────────────────┐
│  Enrutamiento         │  │  ML Service (puerto 8081)   │
│  Ambiental            │  │  - Regresión Logística      │
│  (puerto 8000)        ├──┤  - Random Forest            │
│                       │  │  - Monitoreo trayecto       │
│  ┌─────────────────┐  │  └─────────────────────────────┘
│  │ OSMnx/NetworkX  │  │
│  │ (Grafo vial     │  │  ┌─────────────────────────────┐
│  │  Valle Aburrá)  │  │  │  Open-Meteo API (gratis)    │
│  └─────────────────┘  ├──┤  - Temperatura              │
│  ┌─────────────────┐  │  │  - Humedad                  │
│  │ Rain Model      │  │  │  - Cobertura nubosa         │
│  │ (SIATA data)    │  │  │  - Viento                   │
│  └─────────────────┘  │  └─────────────────────────────┘
│  ┌─────────────────┐  │
│  │ SIATA Live      │  │
│  │ (Precipitación) │  │
│  └─────────────────┘  │
└───────────────────────┘
```

## Features

- **3 tipos de ruta**: Más rápida, más corta, más seca
- **Multi-parada**: Soporte para waypoints intermedios
- **Variables ambientales integradas**:
  - Predicción ML (MDVA): Regresión Logística + Random Forest
  - Modelo local SIATA: Intensidad de precipitación
  - Open-Meteo: Temperatura, humedad, viento, cobertura nubosa
- **Factores de peso**:
  - Tráfico (simulado por jerarquía vial)
  - Pendiente (topografía, crítico para bicicletas)
  - Lluvia (penalización combinada MDVA + SIATA)
  - Elevación (nubes chocan con montañas)
- **Encoded polyline**: Compatible con Google Maps frontend
- **Pasos de navegación**: Turn-by-turn como Google Directions
- **Alertas climáticas**: VERDE / AMARILLO / ROJO
- **Sugerencia de ruta alterna**: Cuando lluvia > 70% y distancia > 5km

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Estado del servicio |
| POST | `/api/v1/route` | Ruta simple con múltiples opciones |
| POST | `/api/v1/route/multi` | Ruta multi-parada |
| POST | `/api/v1/route/spring` | **Compatible con Spring Boot** |

## Instalación y Ejecución

### Local (desarrollo)
```bash
cd Data-science/enrutamiento_ambiental
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Docker (con todo el stack MDVA)
```bash
docker compose -f docker-compose.dev.yml up --build
```

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `MDVA_ML_URL` | `http://ml-service:8081` | URL del microservicio ML |
| `GRAPH_CACHE_FILE` | `valle_aburra.graphml` | Ruta al grafo OSM cacheado |
| `RAIN_MODEL_PATH` | `./cache/rain_model.joblib` | Ruta al modelo de lluvia |

## Ejemplo de request (`/api/v1/route/spring`)

```json
POST /api/v1/route/spring
{
    "origen": {"latitude": 6.2566, "longitude": -75.5921},
    "destino": {"latitude": 6.2088, "longitude": -75.5677},
    "paradas": [
        {"latitude": 6.2442, "longitude": -75.5812}
    ],
    "vehicle_type": "car"
}
```

## Estructura del proyecto

```
enrutamiento_ambiental/
├── main.py                    ← Entrypoint FastAPI
├── requirements.txt
├── Dockerfile
├── domain/
│   ├── entities.py            ← Location, Route (con campos MDVA)
│   ├── ports.py               ← Interfaces abstractas
│   ├── exceptions.py
│   └── rain_model.py          ← Modelo de lluvia SIATA
├── application/
│   ├── dtos.py                ← DTOs + SpringRouteResponse
│   └── use_cases.py           ← Lógica de negocio + encoded polyline
├── infrastructure/
│   ├── osmnx_map_repository.py    ← Grafo OSM Valle de Aburrá
│   ├── networkx_routing_service.py ← Algoritmos de ruta con MDVA
│   ├── weather_service.py         ← Bridge MDVA ML + SIATA + Open-Meteo
│   └── siata_live_service.py      ← Datos en tiempo real SIATA
├── presentation/
│   ├── api.py                 ← Endpoints REST
│   └── dependencies.py        ← Inyección de dependencias
└── scripts/
    └── train_rain_model.py    ← Entrenamiento modelo SIATA
```
