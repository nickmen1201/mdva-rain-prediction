from domain.entities import Location
from domain.ports import MapRepository, RoutingService
from application.dtos import (
    RouteRequest, RouteResponse, 
    MultiStopRouteRequest, MultiStopRouteResponse, MultiStopLeg,
    SpringRouteRequest, SpringRouteResponse, SpringRouteStep,
    Coordinate
)

class FindBestRouteUseCase:
    def __init__(self, map_repo: MapRepository, routing_svc: RoutingService):
        self.map_repo = map_repo
        self.routing_svc = routing_svc

    def execute(self, request: RouteRequest) -> RouteResponse:
        origin = Location(latitude=request.origin.latitude, longitude=request.origin.longitude)
        destination = Location(latitude=request.destination.latitude, longitude=request.destination.longitude)
        
        graph = self.map_repo.load_graph()
        routes = self.routing_svc.find_multiple_routes(origin, destination, graph, vehicle_type=request.vehicle_type)
        
        options = []
        for route in routes:
            options.append({
                "distance_meters": route.distance_meters,
                "travel_time_seconds": route.travel_time_seconds,
                "path": [{"latitude": loc.latitude, "longitude": loc.longitude} for loc in route.path],
                "geometry_wkt": route.geometry_wkt,
                "rain_factor": route.rain_factor,
                "rain_probability": route.rain_probability,
                "rain_intensity_avg": route.rain_intensity_avg,
                "elevation_avg": route.elevation_avg,
                "route_type": route.route_type,
                "mdva_llueve": route.mdva_llueve,
                "mdva_probabilidad_rf": route.mdva_probabilidad_rf,
                "mdva_probabilidad_rl": route.mdva_probabilidad_rl,
                "mdva_temperatura_c": route.mdva_temperatura_c,
                "mdva_humedad_pct": route.mdva_humedad_pct,
                "mdva_cobertura_nubosa_pct": route.mdva_cobertura_nubosa_pct,
                "mdva_velocidad_viento_ms": route.mdva_velocidad_viento_ms,
                "alerta_nivel": route.mdva_alerta_nivel if hasattr(route, 'mdva_alerta_nivel') else "VERDE",
                "alerta_mensaje": route.mdva_alerta_mensaje if hasattr(route, 'mdva_alerta_mensaje') else "",
                "sugerir_ruta_alterna": route.mdva_sugerir_alterna if hasattr(route, 'mdva_sugerir_alterna') else False,
            })
            
        return RouteResponse(options=options)

    def execute_multi_stop(self, request: MultiStopRouteRequest) -> MultiStopRouteResponse:
        """Calcula la ruta completa pasando por múltiples paradas en orden."""
        if len(request.waypoints) < 2:
            raise ValueError("Se necesitan al menos 2 puntos (origen y destino)")
        
        graph = self.map_repo.load_graph()
        legs = []
        total_distance = 0.0
        total_time = 0.0
        total_rain_factor = 0.0
        total_rain_prob = 0.0
        total_rain_intensity = 0.0
        any_rain = False
        max_prob_rf = 0.0
        max_prob_rl = 0.0
        
        for i in range(len(request.waypoints) - 1):
            wp_from = request.waypoints[i]
            wp_to = request.waypoints[i + 1]
            
            origin = Location(latitude=wp_from.latitude, longitude=wp_from.longitude)
            destination = Location(latitude=wp_to.latitude, longitude=wp_to.longitude)
            
            routes = self.routing_svc.find_multiple_routes(origin, destination, graph, vehicle_type=request.vehicle_type)
            best = routes[0]  # Tomamos la mejor ruta para cada tramo
            
            leg = MultiStopLeg(
                from_index=i,
                to_index=i + 1,
                distance_meters=best.distance_meters,
                travel_time_seconds=best.travel_time_seconds,
                path=[{"latitude": loc.latitude, "longitude": loc.longitude} for loc in best.path],
                rain_factor=best.rain_factor,
                rain_probability=best.rain_probability,
                rain_intensity_avg=best.rain_intensity_avg,
                elevation_avg=best.elevation_avg,
                mdva_llueve=best.mdva_llueve,
                mdva_probabilidad_rf=best.mdva_probabilidad_rf,
                mdva_probabilidad_rl=best.mdva_probabilidad_rl,
                alerta_nivel=best.mdva_alerta_nivel if hasattr(best, 'mdva_alerta_nivel') else "VERDE",
            )
            legs.append(leg)
            total_distance += best.distance_meters
            total_time += best.travel_time_seconds
            total_rain_factor += best.rain_factor
            total_rain_prob += best.rain_probability
            total_rain_intensity += best.rain_intensity_avg
            any_rain = any_rain or best.mdva_llueve
            max_prob_rf = max(max_prob_rf, best.mdva_probabilidad_rf)
            max_prob_rl = max(max_prob_rl, best.mdva_probabilidad_rl)
        
        num_legs = len(legs)

        # Determinar alerta global
        alerta_nivel = "VERDE"
        alerta_mensaje = "Condiciones climáticas favorables para el viaje."
        sugerir_alterna = False
        if max_prob_rf >= 0.70:
            alerta_nivel = "ROJO"
            alerta_mensaje = f"Alta probabilidad de lluvia ({max_prob_rf*100:.0f}%). Conduce con precaución."
            sugerir_alterna = total_distance > 5000
        elif max_prob_rf >= 0.40:
            alerta_nivel = "AMARILLO"
            alerta_mensaje = f"Probabilidad de lluvia moderada ({max_prob_rf*100:.0f}%). Lleva paraguas."

        return MultiStopRouteResponse(
            legs=legs,
            total_distance_meters=round(total_distance, 2),
            total_travel_time_seconds=round(total_time, 2),
            total_rain_factor=round(total_rain_factor / num_legs, 2) if num_legs else 1.0,
            total_rain_probability=round(total_rain_prob / num_legs, 2) if num_legs else 0.0,
            total_rain_intensity_avg=round(total_rain_intensity / num_legs, 2) if num_legs else 0.0,
            waypoints=request.waypoints,
            mdva_llueve=any_rain,
            mdva_probabilidad_rf=round(max_prob_rf, 4),
            mdva_probabilidad_rl=round(max_prob_rl, 4),
            alerta_nivel=alerta_nivel,
            alerta_mensaje=alerta_mensaje,
            sugerir_ruta_alterna=sugerir_alterna,
        )

    def execute_spring(self, request: SpringRouteRequest) -> SpringRouteResponse:
        """
        Ejecuta el cálculo de ruta en formato compatible con el Backend Spring Boot.
        Este es el endpoint principal que reemplaza a Google Directions API.
        """
        origin = Location(latitude=request.origen.latitude, longitude=request.origen.longitude)
        destination = Location(latitude=request.destino.latitude, longitude=request.destino.longitude)
        
        graph = self.map_repo.load_graph()
        
        # Si hay paradas, calcular multi-stop
        if request.paradas and len(request.paradas) > 0:
            all_points = [request.origen] + request.paradas + [request.destino]
            multi_req = MultiStopRouteRequest(
                waypoints=all_points,
                vehicle_type=request.vehicle_type
            )
            multi_result = self.execute_multi_stop(multi_req)
            
            # Combinar todos los paths y steps en un solo resultado
            all_path = []
            all_steps = []
            total_dist = 0
            total_dur = 0
            
            for leg in multi_result.legs:
                path_points = leg.path
                if len(path_points) >= 2:
                    # Crear un step para cada tramo
                    first = path_points[0]
                    last = path_points[-1]
                    all_steps.append(SpringRouteStep(
                        instruccion=f"Continuar hacia parada {leg.to_index}",
                        distanciaMetros=int(leg.distance_meters),
                        duracionSegundos=int(leg.travel_time_seconds),
                        startLat=first["latitude"] if isinstance(first, dict) else first.latitude,
                        startLng=first["longitude"] if isinstance(first, dict) else first.longitude,
                        endLat=last["latitude"] if isinstance(last, dict) else last.latitude,
                        endLng=last["longitude"] if isinstance(last, dict) else last.longitude,
                    ))
                all_path.extend(path_points)
                total_dist += leg.distance_meters
                total_dur += leg.travel_time_seconds
            
            # Generar encoded polyline
            encoded = self._encode_polyline(all_path)
            
            return SpringRouteResponse(
                distanciaMetros=int(total_dist),
                duracionSegundos=int(total_dur),
                overviewPolyline=encoded,
                pasos=all_steps,
                rain_factor=multi_result.total_rain_factor,
                rain_probability=multi_result.total_rain_probability,
                rain_intensity_avg=multi_result.total_rain_intensity_avg,
                elevation_avg=1500.0,
                route_type="fastest",
                mdva_llueve=multi_result.mdva_llueve,
                mdva_probabilidad_rf=multi_result.mdva_probabilidad_rf,
                mdva_probabilidad_rl=multi_result.mdva_probabilidad_rl,
                alerta_nivel=multi_result.alerta_nivel,
                alerta_mensaje=multi_result.alerta_mensaje,
                sugerir_ruta_alterna=multi_result.sugerir_ruta_alterna,
            )
        
        # Ruta simple (sin paradas)
        routes = self.routing_svc.find_multiple_routes(origin, destination, graph, vehicle_type=request.vehicle_type)
        best = routes[0]
        
        # Generar steps de navegación a partir del path
        steps = self._generate_nav_steps(best)
        
        # Generar encoded polyline
        encoded = self._encode_polyline(
            [{"latitude": loc.latitude, "longitude": loc.longitude} for loc in best.path]
        )
        
        # Determinar alerta nivel
        prob_rf = best.mdva_probabilidad_rf
        alerta_nivel = "VERDE"
        alerta_mensaje = "Condiciones climáticas favorables para el viaje."
        sugerir_alterna = False
        factor = 1.0
        
        if prob_rf >= 0.70:
            alerta_nivel = "ROJO"
            factor = 1.35
            alerta_mensaje = f"Alta probabilidad de lluvia ({prob_rf*100:.0f}%). Tiempo ajustado +35%. Conduce con precaución."
            if best.distance_meters > 5000:
                sugerir_alterna = True
        elif prob_rf >= 0.40:
            alerta_nivel = "AMARILLO"
            factor = 1.20
            alerta_mensaje = f"Probabilidad de lluvia moderada ({prob_rf*100:.0f}%). Tiempo estimado ajustado +20%."
        
        # Ajustar tiempo por lluvia (mismo cálculo que TripPlannerOrchestrator)
        adjusted_duration = int(best.travel_time_seconds * factor)
        
        # Construir alternativas
        alternativas = []
        for alt_route in routes[1:]:
            alt_encoded = self._encode_polyline(
                [{"latitude": loc.latitude, "longitude": loc.longitude} for loc in alt_route.path]
            )
            alt_steps = self._generate_nav_steps(alt_route)
            alternativas.append(SpringRouteResponse(
                distanciaMetros=int(alt_route.distance_meters),
                duracionSegundos=int(alt_route.travel_time_seconds * factor),
                overviewPolyline=alt_encoded,
                pasos=alt_steps,
                rain_factor=alt_route.rain_factor,
                rain_probability=alt_route.rain_probability,
                rain_intensity_avg=alt_route.rain_intensity_avg,
                elevation_avg=alt_route.elevation_avg,
                route_type=alt_route.route_type,
                mdva_llueve=alt_route.mdva_llueve,
                mdva_probabilidad_rf=alt_route.mdva_probabilidad_rf,
                mdva_probabilidad_rl=alt_route.mdva_probabilidad_rl,
                alerta_nivel=alerta_nivel,
                alerta_mensaje=alerta_mensaje,
                sugerir_ruta_alterna=sugerir_alterna,
            ))
        
        return SpringRouteResponse(
            distanciaMetros=int(best.distance_meters),
            duracionSegundos=adjusted_duration,
            overviewPolyline=encoded,
            pasos=steps,
            rain_factor=best.rain_factor,
            rain_probability=best.rain_probability,
            rain_intensity_avg=best.rain_intensity_avg,
            elevation_avg=best.elevation_avg,
            route_type=best.route_type,
            mdva_llueve=best.mdva_llueve,
            mdva_probabilidad_rf=best.mdva_probabilidad_rf,
            mdva_probabilidad_rl=best.mdva_probabilidad_rl,
            mdva_temperatura_c=best.mdva_temperatura_c,
            mdva_humedad_pct=best.mdva_humedad_pct,
            mdva_cobertura_nubosa_pct=best.mdva_cobertura_nubosa_pct,
            mdva_velocidad_viento_ms=best.mdva_velocidad_viento_ms,
            alerta_nivel=alerta_nivel,
            alerta_mensaje=alerta_mensaje,
            sugerir_ruta_alterna=sugerir_alterna,
            alternativas=alternativas if alternativas else None,
        )
    
    def _generate_nav_steps(self, route) -> list:
        """Genera pasos de navegación a partir de un Route, simulando las instrucciones de Google Directions."""
        steps = []
        path = route.path
        if len(path) < 2:
            return steps
        
        # Generar steps cada N nodos (simplificado)
        step_size = max(1, len(path) // 10)  # ~10 pasos por ruta
        
        for i in range(0, len(path) - 1, step_size):
            start = path[i]
            end_idx = min(i + step_size, len(path) - 1)
            end = path[end_idx]
            
            # Calcular distancia y duración del step
            step_dist = 0.0
            for j in range(i, end_idx):
                step_dist += self._haversine(path[j].latitude, path[j].longitude, 
                                             path[j+1].latitude, path[j+1].longitude)
            
            speed_ms = 11.11  # ~40 km/h promedio urbano
            step_dur = step_dist / speed_ms if speed_ms > 0 else 0
            
            # Generar instrucción basada en dirección
            bearing = self._bearing(start.latitude, start.longitude, end.latitude, end.longitude)
            direction = self._bearing_to_direction(bearing)
            
            steps.append(SpringRouteStep(
                instruccion=f"Continuar hacia el {direction} por {int(step_dist)} metros",
                distanciaMetros=int(step_dist),
                duracionSegundos=int(step_dur),
                startLat=start.latitude,
                startLng=start.longitude,
                endLat=end.latitude,
                endLng=end.longitude,
            ))
        
        return steps
    
    def _encode_polyline(self, path: list) -> str:
        """
        Codifica un path en formato Google Encoded Polyline.
        Compatible con google.maps.geometry.encoding.decodePath() del frontend.
        """
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
                    encoded.append(chr((0x20 | (v & 0x1f)) + 63))
                    v >>= 5
                encoded.append(chr(v + 63))
        
        return ''.join(encoded)
    
    @staticmethod
    def _haversine(lat1, lon1, lat2, lon2):
        """Calcula distancia en metros entre dos puntos."""
        import math
        R = 6371000
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    @staticmethod
    def _bearing(lat1, lon1, lat2, lon2):
        """Calcula el bearing entre dos puntos."""
        import math
        dlon = math.radians(lon2 - lon1)
        lat1r = math.radians(lat1)
        lat2r = math.radians(lat2)
        x = math.sin(dlon) * math.cos(lat2r)
        y = math.cos(lat1r) * math.sin(lat2r) - math.sin(lat1r) * math.cos(lat2r) * math.cos(dlon)
        return (math.degrees(math.atan2(x, y)) + 360) % 360
    
    @staticmethod
    def _bearing_to_direction(bearing):
        dirs = ["norte", "noreste", "este", "sureste", "sur", "suroeste", "oeste", "noroeste"]
        return dirs[int((bearing + 22.5) / 45) % 8]
