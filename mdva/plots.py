"""Figuras de reportes (CCDS v2). Se guardan en reports/figures/."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from sklearn.metrics import precision_recall_curve  # noqa: E402

NOMBRES = {
    "model": "Modelo",
    "logistic": "Regresión logística",
    "raw_forecast": "Pronóstico crudo",
    "climatology": "Climatología",
}


def reliability_diagram(filas: list[dict], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], "--", color="grey", label="Calibración perfecta")
    x = [f["mean_pred"] for f in filas]
    yv = [f["obs_rate"] for f in filas]
    ax.plot(x, yv, "o-", label="Modelo (prueba 2025)")
    ax.set_xlabel("Probabilidad predicha")
    ax.set_ylabel("Frecuencia observada de lluvia")
    ax.set_title("Curva de confiabilidad")
    ax.legend(loc="upper left")
    _guardar(fig, path)


def pr_curves(y: np.ndarray, preds: dict[str, np.ndarray], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 5))
    for k, nombre in NOMBRES.items():
        if k in preds:
            p, r, _ = precision_recall_curve(y, preds[k])
            ax.plot(r, p, label=nombre)
    ax.axhline(np.mean(y), color="grey", ls="--", label="Tasa base")
    ax.set_xlabel("Sensibilidad (recall)")
    ax.set_ylabel("Precisión")
    ax.set_title("Curvas precisión–sensibilidad (prueba 2025)")
    ax.legend()
    _guardar(fig, path)


def _guardar(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
