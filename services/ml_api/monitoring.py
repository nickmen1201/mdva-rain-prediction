"""Reglas de monitoreo de trayecto (charter RF-17) como funciones puras.

- delta = p_actual − p_inicio: [0.10, 0.25] → MODERADO; > 0.25 → SIGNIFICATIVO; si no, ESTABLE.
- Dato meteorológico con más de 15 min de latencia → sube un nivel.
- p_actual > 0.85 → CRITICO (prevalece).
"""

from __future__ import annotations

from datetime import datetime

NIVELES = ("ESTABLE", "MODERADO", "SIGNIFICATIVO", "CRITICO")
LATENCIA_MAX_MIN = 15
PROB_CRITICA = 0.85


def latency_minutes(weather_ts: datetime, now: datetime) -> int:
    """Minutos desde el dato meteorológico; nunca negativo. Ambos instantes deben tener zona horaria."""
    return max(0, int((now - weather_ts).total_seconds() / 60))


def change_level(prob_start: float, prob_now: float, latency_min: int) -> str:
    delta = prob_now - prob_start
    nivel = "ESTABLE"
    if 0.10 <= delta <= 0.25:
        nivel = "MODERADO"
    elif delta > 0.25:
        nivel = "SIGNIFICATIVO"
    if latency_min > LATENCIA_MAX_MIN:
        nivel = NIVELES[min(NIVELES.index(nivel) + 1, len(NIVELES) - 1)]
    if prob_now > PROB_CRITICA:
        nivel = "CRITICO"
    return nivel
