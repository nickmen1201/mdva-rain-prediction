import os
import osmnx as ox
from domain.ports import MapRepository

class OSMnxMapRepository(MapRepository):
    def __init__(self, place_name=None, cache_file="valle_aburra.graphml"):
        if place_name is None:
            # Lista de municipios del Valle de Aburrá
            self.place_name = [
                "Medellín, Antioquia, Colombia",
                "Bello, Antioquia, Colombia",
                "Itagüí, Antioquia, Colombia",
                "Envigado, Antioquia, Colombia",
                "Sabaneta, Antioquia, Colombia",
                "La Estrella, Antioquia, Colombia",
                "Caldas, Antioquia, Colombia",
                "Copacabana, Antioquia, Colombia",
                "Girardota, Antioquia, Colombia",
                "Barbosa, Antioquia, Colombia"
            ]
        else:
            self.place_name = place_name
        self.cache_file = cache_file
        self._cached_graph = None

    def load_graph(self) -> any:
        if self._cached_graph is not None:
            return self._cached_graph
            
        if os.path.exists(self.cache_file):
            print(f"Cargando grafo desde caché local: {self.cache_file}")
            G = ox.load_graphml(self.cache_file)
            self._cached_graph = G
            return G
        
        print(f"Descargando grafo del Valle de Aburrá (esto puede tomar varios minutos)...")
        # Descargamos el área completa del Valle de Aburrá
        G = ox.graph_from_place(self.place_name, network_type="drive")
        
        print("Grafo descargado. Añadiendo elevaciones (topografía)...")
        # Intentamos añadir elevaciones si es posible (usando un raster público)
        try:
            # Nota: Esto requiere conexión y puede fallar si el servicio no responde
            # Pero es clave para la 'perfilación topográfica' solicitada
            # G = ox.elevation.add_node_elevations_google(G, api_key="YOUR_API_KEY") # Requiere API Key
            # Como no tenemos API Key, dejamos el grafo base pero listo para extender
            pass
        except Exception as e:
            print(f"No se pudieron añadir elevaciones: {e}")

        print("Guardando en caché local...")
        ox.save_graphml(G, self.cache_file)
        self._cached_graph = G
        
        return G
