"""Nodo más cercano sin scikit-learn (spec 009, research R5).

`ox.distance.nearest_nodes` exige scikit-learn (BallTree) en grafos sin proyectar. A la escala del
Valle de Aburrá (~40 km), la distancia equirectangular tiene un error < 0.1 % frente a haversine y
se vectoriza con numpy sobre todos los nodos.
"""

import math

import numpy as np


class NearestNodeIndex:
    def __init__(self, graph):
        ids, lats, lons = [], [], []
        for node, data in graph.nodes(data=True):
            ids.append(node)
            lats.append(data["y"])
            lons.append(data["x"])
        self._ids = np.asarray(ids)
        self._lat = np.radians(np.asarray(lats, dtype=float))
        self._lon = np.radians(np.asarray(lons, dtype=float))

    def nearest(self, lat: float, lon: float):
        """Id del nodo más cercano a (lat, lon) en grados."""
        lat_r, lon_r = math.radians(lat), math.radians(lon)
        x = (self._lon - lon_r) * np.cos((self._lat + lat_r) / 2)
        y = self._lat - lat_r
        return self._ids[int(np.argmin(x * x + y * y))].item()
