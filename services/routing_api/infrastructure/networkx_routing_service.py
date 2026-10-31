"""Rutas sobre el grafo vial con tiempos por arista y una sola señal de lluvia (specs 009 y 010).

Costos:
- `fastest`: tiempo de viaje de la arista × factor RF-10 de la alerta (uniforme: no cambia el camino).
- `shortest`: longitud de la arista.
- `dryest` (spec 010): tiempo × factor × (1 + 3 · p_lluvia en el punto medio de la arista), con p de
  una grilla espacial del modelo. Solo si la grilla está disponible y su máximo es ≥ 0.10.

Bicicleta: velocidad = mín(velocidad de la vía, 15 km/h). Sin factores inventados (tráfico, pendiente).
"""

import logging
from dataclasses import dataclass
from typing import Any

import networkx as nx
from application.navigation import Segment, via_label
from domain.entities import Location, Route
from domain.exceptions import RouteNotFoundError
from infrastructure.nearest import NearestNodeIndex
from infrastructure.rain_signal import RainSignal

log = logging.getLogger(__name__)

BIKE_MAX_KPH = 15.0
DRYEST_SENSITIVITY = 3.0
DRYEST_MIN_PROBABILITY = 0.10


@dataclass
class RouteOptions:
    """Rutas calculadas más la información de lluvia usada para calcularlas."""

    routes: list[Route]
    signal: RainSignal
    dryest_available: bool


class NetworkXRoutingService:
    def __init__(self, rain_signal=None, rain_grid=None):
        self.rain_signal = rain_signal
        self.rain_grid = rain_grid
        self._index: tuple[int, NearestNodeIndex] | None = None

    # ── utilidades ─────────────────────────────────────────────────────────────

    def nearest(self, graph, lat: float, lon: float):
        if self._index is None or self._index[0] != id(graph):
            self._index = (id(graph), NearestNodeIndex(graph))
        return self._index[1].nearest(lat, lon)

    @staticmethod
    def edge_seconds(data: dict, vehicle_type: str) -> float:
        if vehicle_type == "bike":
            kph = min(float(data.get("speed_kph", BIKE_MAX_KPH)), BIKE_MAX_KPH)
            return float(data["length"]) / (kph / 3.6)
        return float(data["travel_time"])

    def signal(self, origin: Location) -> RainSignal:
        return (
            self.rain_signal.signal(origin.latitude, origin.longitude) if self.rain_signal else RainSignal.unavailable()
        )

    # ── rutas ──────────────────────────────────────────────────────────────────

    def find_multiple_routes(
        self, origin: Location, destination: Location, graph: Any, vehicle_type: str = "car", signal=None
    ) -> RouteOptions:
        signal = signal or self.signal(origin)
        factor = signal.time_factor
        o = self.nearest(graph, origin.latitude, origin.longitude)
        d = self.nearest(graph, destination.latitude, destination.longitude)

        grid = None
        if self.rain_grid is not None and signal.available:
            grid = self.rain_grid.grid(
                [(origin.latitude, origin.longitude), (destination.latitude, destination.longitude)]
            )

        def tiempo(u, v, data):
            return self.edge_seconds(data, vehicle_type) * factor

        def longitud(u, v, data):
            return float(data["length"])

        routes = [self._build(graph, o, d, tiempo, "fastest", vehicle_type, factor, grid)]
        short = self._build(graph, o, d, longitud, "shortest", vehicle_type, factor, grid)
        if short.path != routes[0].path:
            routes.append(short)

        dryest_available = grid is not None and grid.max_probability >= DRYEST_MIN_PROBABILITY
        if dryest_available:

            def seco(u, v, data):
                p = grid.at(*_midpoint(graph, u, v))
                return self.edge_seconds(data, vehicle_type) * factor * (1 + DRYEST_SENSITIVITY * p)

            dry = self._build(graph, o, d, seco, "dryest", vehicle_type, factor, grid)
            if dry.path != routes[0].path:
                routes.append(dry)
        return RouteOptions(routes, signal, dryest_available)

    def _build(self, graph, o, d, weight, route_type, vehicle_type, factor, grid) -> Route:
        try:
            nodes = nx.shortest_path(
                graph, o, d, weight=lambda u, v, edges: min(weight(u, v, e) for e in edges.values())
            )
        except nx.NetworkXNoPath:
            raise RouteNotFoundError() from None

        segments, exposicion = [], 0.0
        for u, v in zip(nodes[:-1], nodes[1:], strict=True):
            data = min(graph.get_edge_data(u, v).values(), key=lambda e: weight(u, v, e))
            seg_t = self.edge_seconds(data, vehicle_type) * factor
            segments.append(
                Segment(
                    start=(graph.nodes[u]["y"], graph.nodes[u]["x"]),
                    end=(graph.nodes[v]["y"], graph.nodes[v]["x"]),
                    length_m=float(data["length"]),
                    time_s=seg_t,
                    name=via_label(data.get("name"), data.get("highway")),
                    highway=data.get("highway") if isinstance(data.get("highway"), str) else None,
                )
            )
            if grid is not None:
                exposicion += grid.at(*_midpoint(graph, u, v)) * seg_t

        total_t = sum(s.time_s for s in segments)
        return Route(
            distance_meters=round(sum(s.length_m for s in segments), 2),
            travel_time_seconds=round(total_t, 2),
            path=[Location(latitude=graph.nodes[n]["y"], longitude=graph.nodes[n]["x"]) for n in nodes],
            segments=segments,
            route_type=route_type,
            rain_factor=factor,
            rain_exposure=round(exposicion / total_t, 4) if grid is not None and total_t > 0 else None,
        )


def _midpoint(graph, u, v) -> tuple[float, float]:
    a, b = graph.nodes[u], graph.nodes[v]
    return (a["y"] + b["y"]) / 2, (a["x"] + b["x"]) / 2
