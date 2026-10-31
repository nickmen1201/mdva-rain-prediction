"""Pasos de navegación agrupados por vía (spec 009, research R6).

Reemplaza los pasos cada `len(path)//10` nodos con "Continuar hacia el norte" y 40 km/h fijos:
cada paso es un tramo continuo de la misma vía, con su nombre si OSM lo tiene, y su duración es la
suma de los tiempos de sus aristas (los pasos suman la duración total de la ruta).
"""

import math
from dataclasses import dataclass

GIRO_MIN_GRADOS = 30.0


@dataclass(frozen=True)
class Segment:
    """Una arista recorrida: extremos (lat, lon), longitud (m), tiempo (s) y vía."""

    start: tuple[float, float]
    end: tuple[float, float]
    length_m: float
    time_s: float
    name: str | None
    highway: str | None


@dataclass(frozen=True)
class Step:
    instruction: str
    distance_m: float
    duration_s: float
    start: tuple[float, float]
    end: tuple[float, float]


def via_label(name, highway) -> str | None:
    """Nombre legible de la vía; OSM puede traer listas cuando una arista une vías."""
    if isinstance(name, list):
        name = name[0] if name else None
    if name:
        return str(name)
    if isinstance(highway, list):
        highway = highway[0] if highway else None
    return None if highway is None else f"vía {highway}"


def bearing(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlon = math.radians(b[1] - a[1])
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def turn(prev_bearing: float, next_bearing: float) -> str:
    delta = (next_bearing - prev_bearing + 540) % 360 - 180  # (-180, 180]; positivo = derecha
    if delta > GIRO_MIN_GRADOS:
        return "Gira a la derecha"
    if delta < -GIRO_MIN_GRADOS:
        return "Gira a la izquierda"
    return "Continúa"


def _distancia(m: float) -> str:
    return f"{m / 1000:.1f} km" if m >= 1000 else f"{round(m / 10) * 10:.0f} m"


def build_steps(segments: list[Segment]) -> list[Step]:
    grupos: list[list[Segment]] = []
    for seg in segments:
        if grupos and grupos[-1][-1].name == seg.name:
            grupos[-1].append(seg)
        else:
            grupos.append([seg])

    steps = []
    for i, grupo in enumerate(grupos):
        dist = sum(s.length_m for s in grupo)
        dur = sum(s.time_s for s in grupo)
        via = grupo[0].name or "la vía"
        if i == 0:
            accion = "Sal"
        else:
            prev = grupos[i - 1][-1]
            accion = turn(bearing(prev.start, prev.end), bearing(grupo[0].start, grupo[0].end))
        steps.append(
            Step(
                instruction=f"{accion} por {via} durante {_distancia(dist)}",
                distance_m=dist,
                duration_s=dur,
                start=grupo[0].start,
                end=grupo[-1].end,
            )
        )
    return steps
