from application.dtos import (
    MetricsResponse,
    MultiStopLeg,
    MultiStopRouteRequest,
    MultiStopRouteResponse,
    RouteOption,
    RouteRequest,
    RouteResponse,
    SpringRouteRequest,
    SpringRouteResponse,
    SpringRouteStep,
)
from application.navigation import build_steps
from domain.entities import Location, Route
from domain.ports import MapRepository
from infrastructure.rain_signal import RainSignal


def _coords(path: list[Location]) -> list[dict]:
    return [{"latitude": p.latitude, "longitude": p.longitude} for p in path]


def _wkt(path: list[Location]) -> str:
    if len(path) < 2:
        return ""
    return "LINESTRING (" + ", ".join(f"{p.longitude} {p.latitude}" for p in path) + ")"


def _rain(signal: RainSignal) -> dict:
    """Campos de lluvia de la respuesta: valores del modelo o nulos (nunca valores por defecto)."""
    return {
        "clima_disponible": signal.available,
        "rain_probability": round(signal.probability, 4) if signal.available else None,
        "alerta_nivel": signal.alert_level if signal.available else None,
        "model_version": signal.model_version,
        "rain_factor": signal.time_factor,
    }


class FindBestRouteUseCase:
    def __init__(self, map_repo: MapRepository, routing_svc):
        self.map_repo = map_repo
        self.routing_svc = routing_svc

    def execute(self, request: RouteRequest) -> RouteResponse:
        origin = Location(request.origin.latitude, request.origin.longitude)
        destination = Location(request.destination.latitude, request.destination.longitude)
        result = self.routing_svc.find_multiple_routes(
            origin, destination, self.map_repo.load_graph(), vehicle_type=request.vehicle_type
        )
        rain = _rain(result.signal)
        options = [
            RouteOption(
                distance_meters=r.distance_meters,
                travel_time_seconds=r.travel_time_seconds,
                path=_coords(r.path),
                geometry_wkt=_wkt(r.path),
                route_type=r.route_type,
                rain_exposure=r.rain_exposure,
                **rain,
            )
            for r in result.routes
        ]
        return RouteResponse(options=options, dryest_available=result.dryest_available)

    def execute_multi_stop(self, request: MultiStopRouteRequest) -> MultiStopRouteResponse:
        """Ruta por todas las paradas en orden; la señal de lluvia es la del origen (una sola consulta)."""
        if len(request.waypoints) < 2:
            raise ValueError("Se necesitan al menos 2 puntos (origen y destino)")
        graph = self.map_repo.load_graph()
        puntos = [Location(w.latitude, w.longitude) for w in request.waypoints]
        signal = self.routing_svc.signal(puntos[0])
        legs = []
        for i, (a, b) in enumerate(zip(puntos[:-1], puntos[1:], strict=True)):
            best = self.routing_svc.find_multiple_routes(a, b, graph, request.vehicle_type, signal=signal).routes[0]
            legs.append(
                MultiStopLeg(
                    from_index=i,
                    to_index=i + 1,
                    distance_meters=best.distance_meters,
                    travel_time_seconds=best.travel_time_seconds,
                    path=_coords(best.path),
                )
            )
        return MultiStopRouteResponse(
            legs=legs,
            total_distance_meters=round(sum(leg.distance_meters for leg in legs), 2),
            total_travel_time_seconds=round(sum(leg.travel_time_seconds for leg in legs), 2),
            waypoints=request.waypoints,
            **_rain(signal),
        )

    def execute_spring(self, request: SpringRouteRequest) -> SpringRouteResponse:
        """Formato del Backend: duración **base** (sin factor RF-10, spec 008), pasos por vía y alternativas."""
        graph = self.map_repo.load_graph()
        puntos = [request.origen, *(request.paradas or []), request.destino]
        puntos = [Location(p.latitude, p.longitude) for p in puntos]
        signal = self.routing_svc.signal(puntos[0])
        rain = _rain(signal)

        if len(puntos) > 2:
            rutas = [
                self.routing_svc.find_multiple_routes(a, b, graph, request.vehicle_type, signal=signal).routes[0]
                for a, b in zip(puntos[:-1], puntos[1:], strict=True)
            ]
            unida = Route(
                distance_meters=sum(r.distance_meters for r in rutas),
                travel_time_seconds=sum(r.travel_time_seconds for r in rutas),
                path=[p for i, r in enumerate(rutas) for p in (r.path if i == 0 else r.path[1:])],
                segments=[s for r in rutas for s in r.segments],
                route_type="fastest",
                rain_factor=signal.time_factor,
            )
            return self._spring(unida, rain, dryest_available=False, alternativas=None)

        result = self.routing_svc.find_multiple_routes(puntos[0], puntos[1], graph, request.vehicle_type, signal=signal)
        principal = next((r for r in result.routes if r.route_type == request.route_type), result.routes[0])
        alternativas = [self._spring(r, rain, result.dryest_available) for r in result.routes if r is not principal]
        return self._spring(principal, rain, result.dryest_available, alternativas or None)

    def metrics(self, request: SpringRouteRequest) -> MetricsResponse:
        signal = self.routing_svc.signal(Location(request.origen.latitude, request.origen.longitude))
        return MetricsResponse(time_utc=signal.time_utc, **_rain(signal))

    def _spring(self, route: Route, rain: dict, dryest_available: bool, alternativas=None) -> SpringRouteResponse:
        factor = route.rain_factor or 1.0
        pasos = [
            SpringRouteStep(
                instruccion=s.instruction,
                distanciaMetros=int(round(s.distance_m)),
                duracionSegundos=int(round(s.duration_s / factor)),
                startLat=s.start[0],
                startLng=s.start[1],
                endLat=s.end[0],
                endLng=s.end[1],
            )
            for s in build_steps(route.segments)
        ]
        return SpringRouteResponse(
            distanciaMetros=int(round(route.distance_meters)),
            duracionSegundos=int(round(route.travel_time_seconds / factor)),
            overviewPolyline=self._encode_polyline(route.path),
            pasos=pasos,
            route_type=route.route_type,
            rain_exposure=route.rain_exposure,
            dryest_available=dryest_available,
            alternativas=alternativas,
            **rain,
        )

    def _encode_polyline(self, path: list) -> str:
        """Codifica un path en formato Encoded Polyline (precisión 1e-5), el que decodifica el Frontend."""
        encoded = []
        prev_lat = 0
        prev_lng = 0

        for point in path:
            if isinstance(point, dict):
                lat = point["latitude"]
                lng = point["longitude"]
            else:
                lat = point.latitude
                lng = point.longitude

            lat_e5 = round(lat * 1e5)
            lng_e5 = round(lng * 1e5)

            d_lat = lat_e5 - prev_lat
            d_lng = lng_e5 - prev_lng

            prev_lat = lat_e5
            prev_lng = lng_e5

            for v in [d_lat, d_lng]:
                v = ~(v << 1) if v < 0 else (v << 1)
                while v >= 0x20:
                    encoded.append(chr((0x20 | (v & 0x1F)) + 63))
                    v >>= 5
                encoded.append(chr(v + 63))

        return "".join(encoded)
