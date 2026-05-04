import networkx as nx
import osmnx as ox
from typing import Any, List
from domain.entities import Location, Route
from domain.exceptions import RouteNotFoundError
from domain.ports import RoutingService

from infrastructure.weather_service import WeatherService

class NetworkXRoutingService(RoutingService):
    def __init__(self, weather_service: WeatherService = None):
        self.weather_service = weather_service

    def find_multiple_routes(self, origin: Location, destination: Location, graph: Any, vehicle_type: str = "car") -> List[Route]:
        orig_node = ox.distance.nearest_nodes(graph, origin.longitude, origin.latitude)
        dest_node = ox.distance.nearest_nodes(graph, destination.longitude, destination.latitude)
        
        weather_stats = self.weather_service.get_weather_stats(origin.latitude, origin.longitude) if self.weather_service else {"penalty": 1.0, "probability": 0, "intensity": 0, "mdva": {}}
        
        # Extraer datos MDVA del weather_stats
        mdva = weather_stats.get("mdva", {})
        
        def get_weight(u, v, data, rain_sensitivity=0.0, prefer_short=False):
            length = data.get('length', 1.0)
            
            # 1. Factor de Tráfico (Simulado según jerarquía vial y hora)
            highway = data.get('highway', 'unclassified')
            traffic_factor = 1.0
            if isinstance(highway, list): highway = highway[0]
            
            if prefer_short:
                # Para ruta más corta, solo distancia bruta
                return length
            
            if highway in ['primary', 'motorway', 'trunk']:
                traffic_factor = 1.5 # Vías principales más congestionadas
            
            # 2. Factor de Pendiente (Crucial para bicicletas)
            grade = abs(data.get('grade', 0.0))
            grade_factor = 1.0
            if vehicle_type == "bike" and grade > 0.05:
                grade_factor = 1.0 + (grade * 10) # Penalizar lomas fuertes para bicis
            
            # 3. Factor de Lluvia (combinado: modelo local + MDVA)
            rain_penalty = 1.0 + (weather_stats["penalty"] - 1.0) * rain_sensitivity
            
            # 4. Factor MDVA: si MDVA dice que llueve con alta probabilidad, penalizar más
            mdva_prob = mdva.get("probabilidad_rf", 0.0)
            if mdva_prob > 0.5 and rain_sensitivity > 0:
                # Boost adicional basado en la predicción MDVA
                mdva_boost = 1.0 + (mdva_prob - 0.5) * rain_sensitivity * 0.5
                rain_penalty *= mdva_boost
            
            return length * traffic_factor * grade_factor * rain_penalty

        routes = []
        
        # Ruta 1: Ruta más rápida (optimizada por tráfico + lluvia)
        try:
            routes.append(self._build_route(graph, orig_node, dest_node, 
                                          weight_func=lambda u,v,d: get_weight(u,v,d, rain_sensitivity=1.0), 
                                          route_type="fastest", stats=weather_stats))
        except RouteNotFoundError:
            pass
        
        # Ruta 2: Ruta más corta en distancia
        try:
            short_route = self._build_route(graph, orig_node, dest_node,
                                           weight_func=lambda u,v,d: get_weight(u,v,d, prefer_short=True),
                                           route_type="shortest", stats=weather_stats)
            # Solo agregar si es significativamente diferente
            if not routes or abs(short_route.distance_meters - routes[0].distance_meters) > 100:
                routes.append(short_route)
        except RouteNotFoundError:
            pass
        
        # Ruta 3: Ruta más seca (máxima penalización por lluvia para evitar zonas húmedas)
        # Ahora también se activa si MDVA predice lluvia
        mdva_prob = mdva.get("probabilidad_rf", 0.0)
        if weather_stats["probability"] > 10 or mdva_prob > 0.3:
            try:
                dry_route = self._build_route(graph, orig_node, dest_node,
                                            weight_func=lambda u,v,d: get_weight(u,v,d, rain_sensitivity=3.0),
                                            route_type="dryest", stats=weather_stats)
                if not routes or abs(dry_route.distance_meters - routes[0].distance_meters) > 100:
                    routes.append(dry_route)
            except RouteNotFoundError:
                pass
        
        if not routes:
            raise RouteNotFoundError()
        
        return routes

    def _build_route(self, graph, orig_node, dest_node, weight_func, route_type, stats) -> Route:
        try:
            route_nodes = nx.shortest_path(graph, orig_node, dest_node, weight=weight_func)
            path_locations = []
            total_distance = 0.0
            total_time = 0.0
            
            for i in range(len(route_nodes)):
                node_id = route_nodes[i]
                node_data = graph.nodes[node_id]
                path_locations.append(Location(latitude=node_data['y'], longitude=node_data['x']))
                
                if i < len(route_nodes) - 1:
                    next_node = route_nodes[i+1]
                    edges = graph.get_edge_data(node_id, next_node)
                    edge_data = edges[0]
                    edge_length = float(edge_data.get('length', 0.0))
                    total_distance += edge_length
                    
                    # Tiempo afectado por lluvia
                    speed_ms = 11.11 / stats["penalty"]
                    total_time += edge_length / speed_ms

            from shapely.geometry import LineString
            coords = [(loc.longitude, loc.latitude) for loc in path_locations]
            wkt_geom = LineString(coords).wkt if len(coords) > 1 else ""

            # Calcular elevación promedio de la ruta
            avg_elev = stats.get("elevation", 1500.0)

            # Extraer datos MDVA
            mdva = stats.get("mdva", {})

            return Route(
                distance_meters=round(total_distance, 2),
                travel_time_seconds=round(total_time, 2),
                path=path_locations,
                geometry_wkt=wkt_geom,
                rain_factor=round(stats["penalty"], 2),
                rain_probability=round(stats["probability"], 2),
                rain_intensity_avg=round(stats["intensity"], 2),
                elevation_avg=round(avg_elev, 2),
                route_type=route_type,
                # Campos MDVA integrados
                mdva_llueve=mdva.get("llueve", False),
                mdva_probabilidad_rf=round(mdva.get("probabilidad_rf", 0.0), 4),
                mdva_probabilidad_rl=round(mdva.get("probabilidad_rl", 0.0), 4),
                mdva_temperatura_c=round(mdva.get("temperatura_c", 0.0), 1),
                mdva_humedad_pct=round(mdva.get("humedad_pct", 0.0), 1),
                mdva_cobertura_nubosa_pct=round(mdva.get("cobertura_nubosa_pct", 0.0), 1),
                mdva_velocidad_viento_ms=round(mdva.get("velocidad_viento_ms", 0.0), 2),
            )
        except nx.NetworkXNoPath:
            raise RouteNotFoundError()

    def find_shortest_path(self, origin: Location, destination: Location, graph: Any) -> Route:
        # Mantener compatibilidad por ahora
        return self.find_multiple_routes(origin, destination, graph)[0]
