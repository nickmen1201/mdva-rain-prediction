"""Baselines de referencia (spec 005, research R4)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from mdva.features import LOCAL_TZ


class Climatology:
    """P(lluvia | hora local, mes) estimada en entrenamiento; la tasa global si la celda no tiene datos."""

    def fit(self, time_utc: pd.Series, y: np.ndarray) -> Climatology:
        clave = self._clave(time_utc)
        self.global_rate_ = float(np.mean(y))
        self.table_ = pd.Series(np.asarray(y, dtype=float)).groupby(clave.to_numpy()).mean()
        return self

    def predict_proba(self, time_utc: pd.Series) -> np.ndarray:
        return self._clave(time_utc).map(self.table_).fillna(self.global_rate_).to_numpy(dtype=float)

    @staticmethod
    def _clave(time_utc: pd.Series) -> pd.Series:
        local = time_utc.dt.tz_convert(LOCAL_TZ)
        return (local.dt.month * 100 + local.dt.hour).reset_index(drop=True)


class RawForecast:
    """Convierte la precipitación pronosticada en probabilidad (regresión logística de una variable)."""

    def fit(self, X: pd.DataFrame, y: np.ndarray) -> RawForecast:
        self.model_ = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
        self.model_.fit(X[["precipitation_log1p"]], y)
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.model_.predict_proba(X[["precipitation_log1p"]])[:, 1]


def persistence(station_id: pd.Series, time_utc: pd.Series, y: pd.Series) -> np.ndarray:
    """Etiqueta de la hora anterior en la misma estación (referencia NO desplegable).

    Si la hora anterior no existe en el conjunto, usa la tasa global del conjunto.
    """
    df = pd.DataFrame({"s": station_id.to_numpy(), "t": time_utc.to_numpy(), "y": np.asarray(y, dtype=float)})
    previo = df.assign(t=df["t"] + pd.Timedelta(hours=1)).rename(columns={"y": "y_prev"})
    m = df.merge(previo, on=["s", "t"], how="left")
    return m["y_prev"].fillna(df["y"].mean()).to_numpy(dtype=float)
