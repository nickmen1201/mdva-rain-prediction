# MANUAL DE USUARIO
## Monitoreo de Variables Ambientales (MVA)
**Versión:** 1.0 · Sprint 5  
**Fecha:** 19/05/2026  
**Audiencia:** Usuarios finales del área metropolitana de Medellín

---

## 1. Descripción del sistema

MVA es una aplicación web de planificación de viajes y monitoreo ambiental para el Valle de Aburrá. Combina predicción de lluvia basada en Machine Learning (entrenado con datos locales del SIATA) con enrutamiento en tiempo real para entregar recomendaciones instructivas de movilidad antes de que salgas a la calle.

**Qué puede hacer la aplicación:**

- Predecir si lloverá en tu recorrido usando modelos de ML locales.
- Calcular el tiempo estimado de viaje ajustado por condiciones climáticas.
- Mostrarte una alerta de nivel Verde / Amarillo / Rojo con instrucciones concretas.
- Guiarte paso a paso en una vista de navegación 3D con indicadores climáticos.
- Mostrar una capa de calor meteorológico sobre el mapa.
- Registrar tu historial de viajes para análisis posterior.

**Qué no hace:**
- No es una app nativa iOS / Android (es una webapp; ábrela desde el navegador).
- No cubre ciudades fuera del Valle de Aburrá.
- No predice calidad del aire ni sismos; se enfoca en lluvia.

**Requisitos para usar la app:**
- Dispositivo con navegador moderno (Chrome 90+, Firefox, Edge, Safari 15+).
- Conexión a internet.
- La app está disponible en: `http://localhost:8090` (entorno local con Docker).

---

## 2. Casos de uso principales

| # | Caso de uso | Descripción |
|---|---|---|
| CU-01 | Registro | Crear una cuenta nueva con nombre, correo y contraseña |
| CU-02 | Inicio de sesión | Acceder a la cuenta existente |
| CU-03 | Planificar un viaje | Ingresar origen, destino y vehículo para obtener predicción y ruta |
| CU-04 | Ver resultado del viaje | Consultar tiempo ajustado, alerta climática y mapa con ruta |
| CU-05 | Navegar en ruta | Activar la vista de navegación paso a paso con cámara 3D |
| CU-06 | Consultar mapa general | Ver la ciudad con capa de calor meteorológico superpuesta |
| CU-07 | Ver historial | Consultar todos los viajes anteriores registrados |
| CU-08 | Finalizar un viaje | Marcar el viaje como completado al llegar al destino |

---

## 3. Flujo 1 — Registro de cuenta

### Paso 1: Abrir la app
Ingresa a `http://localhost:8090` en tu navegador. Verás la pantalla de inicio de sesión.

### Paso 2: Ir a registro
Haz clic en **"¿No tienes cuenta? Regístrate"** (o navega a `/register`).

### Paso 3: Completar el formulario
Completa los campos:
- **Nombre completo:** tu nombre (ej. `María García`)
- **Correo electrónico:** correo válido (ej. `maria@ejemplo.com`)
- **Contraseña:** mínimo 8 caracteres

### Paso 4: Crear cuenta
Haz clic en **"Crear cuenta"**.

**Resultado esperado:** La app crea tu cuenta y te redirige automáticamente al inicio de sesión (o directamente a la pantalla principal si el token se emite en el registro).

**Si algo falla:**
- *"El correo ya está registrado"* → ese correo ya tiene una cuenta; usa otro o inicia sesión.
- *"Contraseña muy corta"* → elige una contraseña de al menos 8 caracteres.

---

## 4. Flujo 2 — Inicio de sesión

### Paso 1: Abrir la pantalla de login
Navega a la raíz de la app (`http://localhost:8090`) o a `/login`.

### Paso 2: Ingresar credenciales
- **Correo:** el mismo que usaste al registrarte.
- **Contraseña:** tu contraseña.

### Paso 3: Iniciar sesión
Haz clic en **"Iniciar sesión"**.

**Resultado esperado:** La app guarda tu sesión (token JWT) y te lleva a la pantalla de planificación de viaje.

**Si algo falla:**
- *"Credenciales incorrectas"* → verifica correo y contraseña. Si olvidaste la contraseña, contacta al administrador.

---

## 5. Flujo 3 — Planificar un viaje (flujo principal)

Este es el flujo central de la app.

### Paso 1: Acceder a la pantalla de planificación
Después de iniciar sesión, llegarás a la pantalla **"Planificar Viaje"** (`/`).

### Paso 2: Ingresar el origen

En el campo **"Origen"**:
- Empieza a escribir el nombre del lugar (ej. `Parque Berrío`, `Universidad de Antioquia`, `Aeropuerto Olaya Herrera`).
- Selecciona la sugerencia de Google Places que corresponda a tu ubicación de partida.

> También puedes ingresar coordenadas directas en formato `lat,lng` (ej. `6.2442,-75.5812`).

### Paso 3: Ingresar el destino

En el campo **"Destino"**:
- Escribe el nombre del lugar de llegada (ej. `Centro Comercial Santa Fe`, `Estadio Atanasio Girardot`).
- Selecciona la sugerencia correcta.

### Paso 4: Seleccionar el vehículo (opcional)

En el campo **"Vehículo"**, selecciona el vehículo que usarás:
- Motocicleta, bicicleta, automóvil, transporte público, etc.
- Si viajas a pie o no quieres especificar, deja el campo vacío.

> **Importante:** Si seleccionas moto, el sistema aplicará restricciones de circulación en túneles al calcular tu ruta.

### Paso 5: Planificar

Haz clic en **"Planificar viaje"**.

La app procesará:
1. Tu ruta óptima (Google Directions API).
2. Las condiciones climáticas actuales en tu origen (Google Weather API).
3. La predicción de lluvia de los modelos ML locales.

Esto puede tomar entre 3 y 8 segundos.

### Paso 6: Leer el resultado

Serás redirigido a la pantalla de **Resultado del Viaje** (`/resultado/:id`).

---

## 6. Flujo 4 — Leer el resultado y las alertas

### Sección: Estadísticas del viaje

| Dato | Descripción |
|---|---|
| **Tiempo estimado** | Duración calculada con ajuste por condiciones climáticas |
| **Tiempo base** | Duración sin ajuste climático (solo tráfico, según Google Directions) |
| **Factor de ajuste** | ×1.00 / ×1.20 / ×1.35 dependiendo del nivel de alerta |
| **Distancia** | Distancia total de la ruta en km |

### Sección: Alerta climática

La alerta puede ser de tres niveles:

| Color | Nivel | Condición | Qué significa |
|---|---|---|---|
| 🟢 **Verde** | Sin riesgo | Probabilidad de lluvia < 40% | Condiciones normales. Puedes salir sin precauciones adicionales. |
| 🟡 **Amarillo** | Precaución | Probabilidad de lluvia 40%–70% | Posible lluvia durante el trayecto. Se recomienda llevar impermeable o considerar salir antes. |
| 🔴 **Rojo** | Alto riesgo | Probabilidad de lluvia > 70% | Lluvia probable. El sistema suma tiempo adicional al recorrido y puede sugerirte una ruta alterna si tu trayecto supera 5 km. |

**Datos climáticos mostrados:**
- Temperatura actual (°C)
- Humedad relativa (%)
- Cobertura nubosa (%)
- Velocidad del viento (m/s)
- Probabilidad de lluvia según Random Forest y Regresión Logística

### Sección: Mapa con ruta

El mapa muestra la ruta trazada sobre el Valle de Aburrá. Puedes hacer zoom, mover el mapa y ver la ruta destacada en color.

### Botón: Iniciar navegación

Haz clic en **"Iniciar navegación"** para pasar a la vista de navegación paso a paso.

---

## 7. Flujo 5 — Navegación en ruta (vista 3D)

La vista de navegación (`/en-ruta/:id`) es la pantalla de conducción.

### Características de la vista

**Cámara 3D:** El mapa se inclina en perspectiva 3D y sigue tu posición (o la simulación del viaje).

**Panel de instrucciones:** En la parte superior aparece la instrucción de navegación actual:
- Dirección (ej. "Gira a la derecha en Calle 50")
- Distancia hasta la próxima maniobra

**Botón de centrado:** Si el mapa se desplazó, haz clic en el botón de centrado (ícono de brújula o ubicación) para volver a la posición actual.

**Capa de calor meteorológico (Heatmap):**
- Activa el toggle **"Capa de calor"** para ver superpuesto en el mapa un mapa de calor con la intensidad de lluvia por zona del Valle de Aburrá.
- Los colores van de azul (baja probabilidad) a rojo (alta probabilidad).

### Finalizar el viaje

Al llegar a tu destino, haz clic en **"Finalizar viaje"**. El sistema registrará la hora de llegada y marcará el viaje como completado.

---

## 8. Flujo 6 — Consultar el mapa general

En el menú de navegación, accede a **"Mapa"** (`/mapa`).

Esta vista muestra el mapa panorámico del Valle de Aburrá con la capa de calor meteorológico activable. Útil para ver en qué zonas de la ciudad está lloviendo o hay mayor riesgo de lluvia en el momento actual, sin necesidad de planificar un viaje.

---

## 9. Flujo 7 — Historial de viajes

Accede a **"Historial"** desde el menú.

Verás una lista con todos tus viajes registrados. Cada tarjeta muestra:
- Origen y destino
- Fecha y hora de inicio
- Tiempo estimado
- Nivel de alerta que tuvo el viaje
- Estado (en curso / finalizado)

---

## 10. Escenarios cotidianos

### Escenario A — Motociclista saliendo del trabajo en la tarde

**Situación:** Son las 5:00 PM en el barrio El Poblado y necesito llegar a Bello. Es temporada de lluvias.

1. Abro MVA, inicio sesión.
2. En "Planificar Viaje" pongo origen `El Poblado` y destino `Bello`.
3. Selecciono mi moto en el campo de vehículo.
4. La app devuelve alerta **ROJO** con tiempo ajustado de 55 min (base: 40 min, factor ×1.35) y sugerencia de ruta alterna por la Autopista Norte en lugar del Túnel de Occidente (restricción de moto en túneles aplicada).
5. Leo la recomendación: *"Alta probabilidad de lluvia. Usa impermeable, reduce velocidad y mantén mayor distancia de frenado."*
6. Decido esperar 30 minutos y revisar de nuevo.

### Escenario B — Peatón planificando una salida al centro

**Situación:** Voy a hacer una diligencia en el centro de Medellín a las 10:00 AM.

1. Planifico el viaje sin seleccionar vehículo (a pie / transporte público).
2. La app devuelve alerta **VERDE** con probabilidad de lluvia del 20%.
3. Salgo sin paraguas.

### Escenario C — Usuario de transporte público evaluando si salir ahora o esperar

**Situación:** Está nublado y no sé si salir al bus o esperar.

1. Planifico el viaje desde mi casa hasta el trabajo.
2. La app devuelve alerta **AMARILLO** con probabilidad del 55%.
3. La recomendación dice: *"Posible lluvia leve. Si usas transporte público, lleva paraguas pequeño."*
4. Decido salir ahora con paraguas.

---

## 11. Interpretación de los datos climáticos

| Dato | Valor de referencia | Interpretación |
|---|---|---|
| Temperatura | < 15°C | Frío para el Valle de Aburrá; puede haber lluvia |
| Humedad relativa | > 80% | Alta probabilidad de lluvia próxima |
| Cobertura nubosa | > 70% | Cielo muy nublado |
| Velocidad del viento | > 5 m/s | Viento moderado, lluvia puede ser con viento |
| Probabilidad RF | > 70% | El modelo de ML predice lluvia con alta confianza |

---

## 12. Preguntas frecuentes

**¿La app me da la ubicación en tiempo real?**  
La vista de navegación muestra la ruta planificada. La geolocalización en tiempo real es una mejora planificada para versiones futuras.

**¿Por qué el tiempo estimado es mayor al que me da Google Maps?**  
La app ajusta el tiempo de Google Directions aplicando un factor multiplicador (hasta ×1.35) cuando la predicción de lluvia es alta, para darte una estimación más realista del tiempo que tardarás bajo lluvia.

**¿Por qué mi moto no puede pasar por el túnel?**  
El sistema aplica la restricción de circulación de motocicletas en túneles vigente en el área metropolitana de Medellín.

**¿Qué hago si la app dice que no puede calcular la ruta?**  
Verifica que el origen y el destino estén dentro del Valle de Aburrá. Si el problema persiste, puede ser un problema de conectividad con las APIs externas; intenta de nuevo en unos minutos.

**¿Mis datos están seguros?**  
La app usa autenticación JWT. Tu contraseña nunca se almacena en texto plano (se guarda con hash bcrypt). No se comparten datos con terceros más allá de las APIs de Google necesarias para el funcionamiento.

---

*MDVA — Manual de Usuario · Sprint 5 · Mayo 2026*
