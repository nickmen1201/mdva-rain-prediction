"""Genera y ejecuta `notebooks/3.0-nm-evaluacion-y-calibracion.ipynb` (spec 012, charter R-51, E-02).

El notebook narra el proceso de modelado leyendo **solo** artefactos generados en `reports/`
(`study.json`, `metrics.json`, figuras). No entrena ni recalcula métricas: es comunicación, no
lógica. Las figuras se enlazan (no se incrustan) para mantener las salidas ligeras (E-03).

Uso: `make notebook`
"""

from __future__ import annotations

import nbformat
from nbclient import NotebookClient
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

from mdva import config

NOTEBOOK = config.PROJ_ROOT / "notebooks" / "3.0-nm-evaluacion-y-calibracion.ipynb"


def _md(texto: str):
    return new_markdown_cell(texto.strip())


def _code(codigo: str):
    return new_code_cell(codigo.strip())


CELDAS = [
    _md("""
# 3.0 — Evaluación y calibración del clasificador de lluvia

Este notebook **no entrena nada**: lee los artefactos que generan `make study` y `make train`
(`reports/metrics/rain_classifier/...`) y cuenta cómo se tomó cada decisión. Para regenerarlo:
`make study train notebook`.

**Pregunta**: ¿lloverá (≥ 0.5 mm) en la celda ERA5 de un punto del Valle de Aburrá en una hora dada, a partir del
pronóstico de Open-Meteo para ese punto? **Reglas del juego**: toda decisión se toma con validación cruzada temporal
dentro de 2022–2024; 2025 se usó para reportar la versión 1.0.0 y 2026 es un holdout que no tocó ninguna decisión.
"""),
    _code("""
import json
from pathlib import Path

import pandas as pd

RAIZ = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
M = RAIZ / "reports" / "metrics" / "rain_classifier"
study = json.loads((M / "study" / "study.json").read_text(encoding="utf-8"))
version = sorted(p.name for p in M.iterdir() if p.name[0].isdigit())[-1]
metrics = json.loads((M / version / "metrics.json").read_text(encoding="utf-8"))
pd.set_option("display.precision", 4)
print("Modelo", version, "· desarrollo", study["development"]["start"][:10], "→", study["development"]["end"][:10],
      f"· {study['development']['rows']:,} filas · tasa de lluvia {study['development']['rain_rate']:.1%}")
pd.DataFrame(study["folds"])
"""),
    _md("""
## 1. Validación cruzada *rolling origin*

Seis folds trimestrales con ventana de entrenamiento creciente y 24 h de hueco: la autocorrelación horaria haría
optimista un K-fold aleatorio, y el modelo siempre predice el futuro respecto de lo que vio.
"""),
    _md("""
## 2. ¿Qué features agregar? (con la configuración de referencia 1.0.0)

La ventana del pronóstico (t−2…t+2) absorbe errores de *timing* del modelo numérico; la ubicación captura gradientes
dentro del valle. La ubicación se acepta solo si también mejora en validación **espacial** (entrenar sin una celda ERA5
y evaluar en ella), porque el producto predice en puntos arbitrarios.
"""),
    _code("""
sets = pd.DataFrame({k: {"log loss CV": v["cv"]["mean"]["log_loss"], "Δ vs base": v["vs_base"]["mean"],
                         "EE": v["vs_base"]["se"], "log loss espacial": study["spatial_cv"][k]["mean_log_loss"]}
                     for k, v in study["feature_candidates"]["sets"].items()}).T
marginal = pd.DataFrame(study["feature_candidates"]["marginal"]).T[["mean", "se", "better_by_1se"]]
display(sets)
marginal
"""),
    _md("""
## 3. Búsqueda de hiperparámetros

Búsqueda aleatoria (semilla fija) de 60 configuraciones de HistGradientBoosting más dos familias de referencia
(logística con *splines*, un GAM aditivo, y bosque aleatorio, la familia del modelo heredado). Se elige con la regla de
**un error estándar**: entre las configuraciones a ≤ 1 EE de la mejor, la más simple.

![Sensibilidad](../reports/figures/study_hgb_sensitivity.png)
"""),
    _code("""
t = pd.json_normalize(study["search"]["trials"])
t["ll"] = t["mean.log_loss"]
print("Elegida:", study["search"]["chosen"]["family"], study["search"]["chosen"]["params"])
print("Δ vs configuración 1.0.0 (misma CV):", study["search"]["chosen_vs_v1"])
t.groupby("family")["ll"].describe()[["count", "min", "50%", "max"]]
"""),
    _md("""
## 4. Qué aprendió el modelo

Importancia por permutación (aumento del log loss al barajar cada feature en los folds de validación, IC 95 % entre
folds × repeticiones) y dependencia parcial de las cuatro principales, contrastada con la física de la lluvia.

![Permutación](../reports/figures/study_permutation_importance.png)
![PDP](../reports/figures/study_partial_dependence.png)
"""),
    _code("""
imp = pd.DataFrame(study["permutation_importance"]).set_index("feature")
pdp = {f: d["trend"] for f, d in study["partial_dependence"].items()}
display(imp.head(10))
pdp
"""),
    _md("""
## 5. Ablación y curva de aprendizaje

![Ablación](../reports/figures/study_ablation.png)
![Curva de aprendizaje](../reports/figures/study_learning_curve.png)
"""),
    _code("""
ab = pd.DataFrame({g: {"Δ log loss": v["delta_vs_full"]["mean"], "EE": v["delta_vs_full"]["se"]}
                   for g, v in study["ablation"].items()}).T.sort_values("Δ log loss", ascending=False)
display(ab)
pd.DataFrame(study["learning_curve"])[["train_months", "mean_log_loss"]]
"""),
    _md("""
## 6. Dónde falla (predicciones *out-of-fold*)
"""),
    _code("""
for dim in ("season", "hour_local", "forecast_precip_mm"):
    display(pd.DataFrame(study["errors_oof"][dim]).set_index("segment"))
"""),
    _md("""
## 7. Calibración y umbrales de decisión

Cada fold se calibra solo con las predicciones de los folds anteriores (*cross-fitting* temporal), así que la
comparación no mira el fold evaluado. Con probabilidades calibradas, el umbral de costo mínimo es 1/(1+r) cuando una
lluvia no avisada cuesta r veces una falsa alarma: que el óptimo empírico coincida con el teórico es otra prueba de
calibración.

![Calibración](../reports/figures/study_calibration.png)
![Costo](../reports/figures/study_decision_cost.png)
"""),
    _code("""
display(pd.DataFrame({m: {"log loss": d["log_loss"], "ECE": d["ece"]}
                      for m, d in study["calibration"]["methods"].items()}).T)
pd.DataFrame({r: {"umbral teórico": d["theoretical_threshold"], "umbral óptimo": d["optimal_threshold"],
                  "regret 0.40": d["business_thresholds"]["0.4"]["regret_vs_optimal"],
                  "regret 0.70": d["business_thresholds"]["0.7"]["regret_vs_optimal"]}
              for r, d in study["decision"]["ratios"].items()}).T
"""),
    _md("""
## 8. Evaluación final (una sola vez): prueba 2025 y holdout 2026

IC 95 % por bootstrap en bloques de días. "Supera" = el IC de la diferencia pareada de Brier **y** de log loss
queda por debajo de 0.

![Confiabilidad](../reports/figures/rain_classifier_reliability.png)
"""),
    _code("""
for nombre, s in metrics["splits"].items():
    tabla = pd.DataFrame({k: {m: v[m] for m in ("roc_auc", "pr_auc", "brier", "log_loss", "bss", "ece")}
                          for k, v in s["models"].items()}).T
    print(nombre, s["period"][0][:10], "→", s["period"][1][:10], f"· {s['rows']:,} filas", s["claims"])
    display(tabla)
"""),
    _md("""
## 9. Registro de decisiones

Qué se decidió, con qué evidencia y con qué datos. Ninguna fila usa el holdout 2026.
"""),
    _code("""
pd.DataFrame(metrics["decision_log"])
"""),
    _md("""
## Limitaciones

La etiqueta es reanálisis ERA5 (~25 km), no lluvia medida: frente a pluviómetros SIATA la concordancia horaria es baja
con cualquier fuente de malla (`reports/metrics/label_validation.json`). Las 13 estaciones caen en 5 celdas: hay muchas
menos observaciones independientes que filas, por eso los IC remuestrean días completos. Detalle en la model card
(`models/rain_classifier/<versión>/model_card.md`).
"""),
]


def build() -> nbformat.NotebookNode:
    nb = new_notebook(cells=CELDAS)
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    return nb


def main() -> None:
    nb = build()
    NotebookClient(
        nb, timeout=120, kernel_name="python3", resources={"metadata": {"path": str(NOTEBOOK.parent)}}
    ).execute()
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, NOTEBOOK)
    print(f"Notebook escrito: {NOTEBOOK.relative_to(config.PROJ_ROOT)}")


if __name__ == "__main__":
    main()
