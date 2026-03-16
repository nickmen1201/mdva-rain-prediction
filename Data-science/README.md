# MDVA — Servicio FastAPI de Predicción de Lluvia

## Estructura esperada

```
mdva-api/
├── main.py
├── requirements.txt
└── models/
    ├── regresi_n_log_stica.pkl
    └── random_forest.pkl
```

## Instalación y ejecución

```bash
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8081 --reload
```                 
---

## Endpoints

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Estado del servicio |
| POST | `/predecir/regresion_logistica` | Predicción con Regresión Logística |
| POST | `/predecir/random_forest` | Predicción con Random Forest |

---

## Ejemplo de request

```json
POST /predecir/random_forest
{
  "temperatura_c": 18.5,
  "humedad_relativa_pct": 82.0,
  "cobertura_nubosa_pct": 75.0,
  "velocidad_viento_ms": 2.3,
  "hora": 14,
  "mes": 4
}
```

## Ejemplo de response

```json
{
  "modelo": "random_forest",
  "llueve": true,
  "probabilidad_lluvia": 0.7231,
  "etiqueta": "llueve"
}
```

---

## Consumo desde Spring Boot

### Dependencia (pom.xml)
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-web</artifactId>
</dependency>
```

### DTO
```java
// Request
public record PrediccionRequest(
    double temperatura_c,
    double humedad_relativa_pct,
    double cobertura_nubosa_pct,
    double velocidad_viento_ms,
    int hora,
    int mes
) {}

// Response
public record PrediccionResponse(
    String modelo,
    boolean llueve,
    double probabilidad_lluvia,
    String etiqueta
) {}
```

### Service
```java
@Service
public class PrediccionService {

    private final RestTemplate restTemplate;

    @Value("${mdva.api.url:http://localhost:8081}")
    private String mdvaApiUrl;

    public PrediccionService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    public PrediccionResponse predecir(PrediccionRequest req) {
        String url = mdvaApiUrl + "/predecir/random_forest";
        return restTemplate.postForObject(url, req, PrediccionResponse.class);
    }

    // Para llamar ambos modelos:
    public PrediccionResponse[] predecirAmbos(PrediccionRequest req) {
        String url = mdvaApiUrl + "/predecir/ambos";
        return restTemplate.postForObject(url, req, PrediccionResponse[].class);
    }
}
```

### Config (application.properties)
```properties
mdva.api.url=http://localhost:8081
```
