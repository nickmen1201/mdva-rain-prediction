"""Genera la model card a partir de metadata.json y metrics.json (spec 005, R9).

Las cifras nunca se escriben a mano: `tests/test_model_card.py` regenera la tarjeta y la
compara con la versionada.
"""

# El cuerpo es una plantilla Markdown: sus filas de tabla no se parten en varias líneas.
# ruff: noqa: E501

from __future__ import annotations


def _f(x, nd=3):
    return f"{x:.{nd}f}"


def _ic(ci):
    return f"[{_f(ci[0])}, {_f(ci[1])}]"


def _calibracion(metadata: dict, metrics: dict) -> str:
    c = metrics["calibration_choice"]
    lls = ", ".join(f"{k} {c[k]:.4f}" for k in ("none", "isotonic", "sigmoid") if k in c)
    if metadata["calibration"]["method"] == "none":
        return (
            "ninguna. En el sub-split de validación (ajuste ene–jun, evaluación jul–dic de 2024) las probabilidades "
            f"nativas tuvieron el menor log loss ({lls})."
        )
    return f"`{metadata['calibration']['method']}` ajustada en validación (log loss en el sub-split: {lls})."


def render(metadata: dict, metrics: dict) -> str:
    test = metrics["splits"]["test"]["models"]
    val = metrics["splits"]["validation"]["models"]
    sp = metadata["splits"]
    pareadas = metrics["splits"]["test"]["paired_vs_model"]
    niveles = metrics["alert_levels"]["test"]
    ext = metrics["external_siata"]
    claims = metrics["claims"]
    chosen = metrics["selection"]["chosen"]

    filas = []
    nombres = {
        "model": "**Modelo**",
        "logistic": "Regresión logística",
        "raw_forecast": "Pronóstico crudo",
        "climatology": "Climatología",
        "persistence_reference": "Persistencia (no desplegable)",
    }
    for k, nombre in nombres.items():
        m = test[k]
        filas.append(
            f"| {nombre} | {_f(m['roc_auc'])} {_ic(m['ci95']['roc_auc'])} | {_f(m['pr_auc'])} | "
            f"{_f(m['brier'], 4)} {_ic(m['ci95']['brier'])} | {_f(m['log_loss'])} | {_f(m['bss'])} | {_f(m['ece'], 4)} |"
        )

    def veredicto(ok):
        return "sí (IC 95 % de la diferencia < 0 en Brier y log loss)" if ok else "**no** de forma concluyente"

    lineas_niveles = "\n".join(
        f"| {n} | {_f(v['share'] * 100, 1)} % | "
        f"{'—' if v['rain_rate'] is None else _f(v['rain_rate'] * 100, 1) + ' %'} |"
        for n, v in niveles["levels"].items()
    )

    return f"""# Model card — {metadata["model_name"]} {metadata["model_version"]}

> Generada automáticamente por `mdva.modeling.model_card` desde `metadata.json` y
> `{metadata["metrics_path"]}`. No editar a mano.

## Qué predice

Probabilidad calibrada de que en la celda de reanálisis ERA5 que contiene un punto del Valle de Aburrá caiga
lluvia apreciable (≥ {metadata["label"]["threshold_mm"]} mm) en una hora dada, a partir del pronóstico de
Open-Meteo para ese punto y esa hora (13 features, contrato v{metadata["feature_contract_version"]};
ver `docs/features.md`).

**Uso previsto**: alertas de lluvia para planificar trayectos (VERDE < {metadata["alert_thresholds"]["amarillo"]},
AMARILLO ≤ {metadata["alert_thresholds"]["rojo"]}, ROJO > {metadata["alert_thresholds"]["rojo"]}).
**No** es un pronóstico de intensidad ni de lluvia en un punto exacto.

## Modelo

- Base: `{metadata["base_estimator"]["class"]}` `{chosen["params"]}`, elegido por log loss en validación entre
  {len(metrics["selection"]["candidates"])} candidatos.
- Calibración: {_calibracion(metadata, metrics)}
- Tamaño: {_f(metadata["size_bytes"] / 1e6, 2)} MB · scikit-learn {metadata["library_versions"]["scikit-learn"]} ·
  semilla {metadata["seed"]}.

## Datos

| Split | Periodo (UTC) | Filas | Tasa de lluvia |
|---|---|---|---|
| Entrenamiento | {sp["train"]["start"][:10]} → {sp["train"]["end"][:10]} (sin jun–jul 2022) | {sp["train"]["rows"]:,} | {_f(sp["train"]["rain_rate"] * 100, 1)} % |
| Validación | {sp["validation"]["start"][:10]} → {sp["validation"]["end"][:10]} | {sp["validation"]["rows"]:,} | {_f(sp["validation"]["rain_rate"] * 100, 1)} % |
| Prueba | {sp["test"]["start"][:10]} → {sp["test"]["end"][:10]} | {sp["test"]["rows"]:,} | {_f(sp["test"]["rain_rate"] * 100, 1)} % |

13 estaciones SIATA como ubicaciones (5 celdas ERA5 distintas). Huella del dataset: `{metadata["dataset_fingerprint"][:16]}…`.

## Desempeño en prueba (2025, usado una sola vez)

IC 95 % por bootstrap en bloques de días (B = {metrics["bootstrap"]["B"]}).

| Modelo | ROC-AUC | PR-AUC | Brier | Log loss | BSS vs climatología | ECE |
|---|---|---|---|---|---|---|
{chr(10).join(filas)}

- ¿Supera a la climatología? {veredicto(claims["beats_climatology"])}.
- ¿Supera al pronóstico crudo? {veredicto(claims["beats_raw_forecast"])}.
- ¿Supera a la regresión logística? {veredicto(claims["beats_logistic"])}.
- Diferencia de Brier modelo − climatología: {_f(pareadas["climatology"]["brier_diff"]["mean"], 4)}
  {_ic(pareadas["climatology"]["brier_diff"]["ci95"])}.
- Validación (2024): ROC-AUC {_f(val["model"]["roc_auc"])}, Brier {_f(val["model"]["brier"], 4)}.

## Calibración y niveles de alerta (prueba)

ECE = {_f(test["model"]["ece"], 4)} ({"< 0.03" if claims["ece_below_0_03"] else "≥ 0.03"}).
Curva de confiabilidad: `reports/figures/{metadata["model_name"]}_reliability.png`.

| Nivel | % de horas | Llueve dentro del nivel |
|---|---|---|
{lineas_niveles}

- Alerta ≥ AMARILLO: precisión {_f(niveles["ge_amarillo"]["precision"])}, sensibilidad {_f(niveles["ge_amarillo"]["recall"])}.
- Alerta ROJO: precisión {_f(niveles["rojo"]["precision"])}, sensibilidad {_f(niveles["rojo"]["recall"])}.

## Validación externa contra pluviómetros SIATA (jun–jul 2022, fuera del entrenamiento)

{ext["n"]:,} horas-estación; llueve en el pluviómetro en el {_f(ext["rain_rate_obs"] * 100, 1)} %.

| Puntaje | ROC-AUC frente a la lluvia medida |
|---|---|
| Modelo | {_f(ext["roc_auc"]["model"])} |
| Precipitación pronosticada (cruda) | {_f(ext["roc_auc"]["raw_forecast_mm"])} |
| Precipitación de referencia ERA5 (la etiqueta) | {_f(ext["roc_auc"]["label_reference_mm"])} |

Kappa del modelo al umbral AMARILLO: {_f(ext["kappa_model_at_amarillo"])}.

## Limitaciones

- La etiqueta es reanálisis (ERA5, ~25 km), no lluvia medida: el modelo predice lluvia **de la celda**. Frente a
  pluviómetros, la concordancia horaria es baja con cualquier fuente de malla (ver `reports/metrics/label_validation.json`).
- Las 13 estaciones caen en 5 celdas: hay menos observaciones independientes que filas.
- La tasa de lluvia cambia entre años ({_f(sp["validation"]["rain_rate"] * 100, 1)} % en validación,
  {_f(sp["test"]["rain_rate"] * 100, 1)} % en prueba); la calibración se ajustó en un año más seco que el de prueba.
- Transparencia metodológica: durante el desarrollo se comparó una vez, sobre el año de prueba, el efecto de distintas
  estrategias de calibración. La decisión final (sin calibración posterior) se tomó con evidencia solo de validación
  (`specs/005-model-training/research.md`, R10), pero la prueba ya no es estrictamente "no vista" para esa decisión.
- Los pronósticos archivados corresponden a horizontes cortos; para horas lejanas el pronóstico de entrada es menos
  preciso y el desempeño puede ser menor.
"""
