"""Genera la model card desde metadata.json, metrics.json y study.json (specs 005 y 012, charter R-16, R-44).

Las cifras nunca se escriben a mano: `tests/test_model_card.py` regenera la tarjeta y la compara con
la versionada.
"""

# El cuerpo es una plantilla Markdown: sus filas de tabla no se parten en varias líneas.
# ruff: noqa: E501

from __future__ import annotations

NOMBRES = {
    "model": "**Modelo 1.1.0**",
    "model_1_0_0": "Modelo 1.0.0 (spec 005)",
    "logistic": "Regresión logística",
    "raw_forecast": "Pronóstico crudo",
    "climatology": "Climatología",
    "persistence_reference": "Persistencia (no desplegable)",
}
FAMILIAS = {
    "hgb": "HistGradientBoosting",
    "spline_logistic": "Logística con *splines* (GAM)",
    "random_forest": "Bosque aleatorio",
    "hgb_v1": "HGB con la configuración 1.0.0",
}

# Signo esperado por la física de la lluvia para las features más importantes (R-46)
FISICA = {
    "precipitation": ("creciente", "más lluvia pronosticada, más probabilidad"),
    "relative_humidity_2m": ("creciente", "aire más cerca de la saturación"),
    "dew_point_depression": ("decreciente", "a menor depresión, más saturación"),
    "cloud_cover": ("creciente", "nubosidad como condición necesaria"),
    "cape": ("creciente", "más inestabilidad convectiva"),
    "month_": ("no monotónica", "régimen bimodal"),
}


def _f(x, nd=3):
    return "—" if x is None else f"{x:.{nd}f}"


def _ic(ci):
    return f"[{_f(ci[0])}, {_f(ci[1])}]"


def _pct(x, nd=1):
    return "—" if x is None else f"{x * 100:.{nd}f} %"


def _fisica(feature: str, tendencia: str) -> str:
    for prefijo, (esperada, porque) in FISICA.items():
        if feature.startswith(prefijo):
            ok = "✔ concuerda" if esperada == tendencia else "✘ no concuerda"
            return f"{esperada} ({porque}) — {ok}"
    return "sin expectativa física fuerte"


def _tabla_desempeno(split: dict, B: int) -> str:
    filas = []
    for k, nombre in NOMBRES.items():
        if k not in split["models"]:
            continue
        m = split["models"][k]
        filas.append(
            f"| {nombre} | {_f(m['roc_auc'])} {_ic(m['ci95']['roc_auc'])} | {_f(m['pr_auc'])} | "
            f"{_f(m['brier'], 4)} {_ic(m['ci95']['brier'])} | {_f(m['log_loss'])} | {_f(m['bss'])} | {_f(m['ece'], 4)} |"
        )
    pareadas = split["paired_vs_model"]
    veredictos = []
    for b, nombre in NOMBRES.items():
        if b in pareadas and b != "persistence_reference":
            ok = split["claims"][f"beats_{b}"]
            d = pareadas[b]["brier_diff"]
            veredictos.append(
                f"- vs {nombre.strip('*')}: {'**supera**' if ok else 'no supera de forma concluyente'} "
                f"(Δ Brier {_f(d['mean'], 4)} {_ic(d['ci95'])})"
            )
    niveles = split["alert_levels"]
    lineas_niveles = "\n".join(
        f"| {n} | {_pct(v['share'])} | {_pct(v['rain_rate'])} |" for n, v in niveles["levels"].items()
    )
    return f"""Periodo {split["period"][0][:10]} → {split["period"][1][:10]} · {split["rows"]:,} horas-estación · llueve en el {_pct(split["rain_rate"])}. IC 95 % por bootstrap en bloques de días (B = {B}).

| Modelo | ROC-AUC | PR-AUC | Brier | Log loss | BSS vs climatología | ECE |
|---|---|---|---|---|---|---|
{chr(10).join(filas)}

Diferencias pareadas (modelo − baseline; IC 95 % < 0 en Brier y log loss = supera):
{chr(10).join(veredictos)}

| Nivel de alerta | % de horas | Llueve dentro del nivel |
|---|---|---|
{lineas_niveles}

Alerta ≥ AMARILLO: precisión {_f(niveles["ge_amarillo"]["precision"])}, sensibilidad {_f(niveles["ge_amarillo"]["recall"])} · ROJO: precisión {_f(niveles["rojo"]["precision"])}, sensibilidad {_f(niveles["rojo"]["recall"])}."""


def render(metadata: dict, metrics: dict, study: dict) -> str:
    sp = metadata["splits"]
    ext = metrics["external_siata"]
    busqueda = study["search"]
    elegido = busqueda["chosen"]
    B = metrics["bootstrap"]["B"]

    familias = (
        "\n".join(
            f"| {FAMILIAS[f]} | {_f(r['mean']['log_loss'], 4)} ± {_f(r['se_log_loss'], 4)} | {_f(r['mean']['roc_auc'])} | `{r['params']}` |"
            for f, r in busqueda["best_by_family"].items()
        )
        + f"\n| {FAMILIAS['hgb_v1']} | {_f(busqueda['v1_reference']['mean']['log_loss'], 4)} ± {_f(busqueda['v1_reference']['se_log_loss'], 4)} | {_f(busqueda['v1_reference']['mean']['roc_auc'])} | `{busqueda['v1_reference']['params']}` |"
    )

    cand = study["feature_candidates"]
    candidatos = "\n".join(
        f"| `{k}` | {_f(v['cv']['mean']['log_loss'], 4)} | {_f(v['vs_base']['mean'], 4)} ± {_f(v['vs_base']['se'], 4)} | "
        f"{_f(study['spatial_cv'][k]['mean_log_loss'], 4)} |"
        for k, v in cand["sets"].items()
    )
    marginal = "\n".join(
        f"| {k.replace('|', ' dado ')} | {_f(v['mean'], 4)} ± {_f(v['se'], 4)} | {'sí' if v['better_by_1se'] else 'no'} |"
        for k, v in cand["marginal"].items()
    )
    ablacion = "\n".join(
        f"| {g} | {', '.join(f'`{c}`' for c in v['removed'])} | {_f(v['delta_vs_full']['mean'], 4)} ± {_f(v['delta_vs_full']['se'], 4)} |"
        for g, v in sorted(study["ablation"].items(), key=lambda kv: -kv[1]["delta_vs_full"]["mean"])
    )
    importancia = "\n".join(
        f"| {i} | `{r['feature']}` | {_f(r['mean'], 4)} {_ic(r['ci95'])} |"
        for i, r in enumerate(study["permutation_importance"][:10], 1)
    )
    pdp = "\n".join(
        f"| `{f}` | {d['trend']} | {_fisica(f, d['trend'])} |" for f, d in study["partial_dependence"].items()
    )
    perfil = study["hour_profile"]["model"]
    obs = {f["hour_local"]: f["rain_rate"] for f in study["hour_profile"]["observed_rate_last_fold"]}
    pico = max(perfil, key=lambda f: f["mean_probability"])
    valle = min(perfil, key=lambda f: f["mean_probability"])
    pico_obs = max(obs, key=obs.get)
    horario = (
        f"El modelo aprendió un ciclo diurno con máximo a las {pico['hour_local']}:00 "
        f"(P media {_pct(pico['mean_probability'])}) y mínimo a las {valle['hour_local']}:00 "
        f"({_pct(valle['mean_probability'])}); en el último fold la lluvia observada fue máxima a las {pico_obs}:00 "
        f"({_pct(obs[pico_obs])}). Las tormentas de la tarde en el valle son el patrón esperado."
    )
    curva = " · ".join(f"{r['train_months']} meses: {_f(r['mean_log_loss'], 4)}" for r in study["learning_curve"])

    def peores(dim, n=3):
        filas = [f for f in study["errors_oof"][dim] if "brier" in f]
        return ", ".join(
            f"{f['segment']} (Brier {_f(f['brier'], 3)}, AUC {_f(f['roc_auc'], 2)})"
            for f in sorted(filas, key=lambda f: -f["brier"])[:n]
        )

    temporada = "\n".join(
        f"| {f['segment']} | {f['n']:,} | {_pct(f['rain_rate'])} | {_pct(f['mean_pred'])} | {_f(f.get('roc_auc'))} | {_f(f.get('ece'), 3)} |"
        for f in study["errors_oof"]["season"]
    )
    cal = study["calibration"]
    calibracion = "\n".join(
        f"| `{m}` | {_f(d['log_loss'], 4)} | {_f(d['ece'], 4)} |" for m, d in cal["methods"].items()
    )
    decision = "\n".join(
        f"| 1 : {r} | {_f(d['theoretical_threshold'], 2)} | {_f(d['optimal_threshold'], 2)} | "
        f"{_f(d['business_thresholds']['0.4']['regret_vs_optimal'], 4)} | {_f(d['business_thresholds']['0.7']['regret_vs_optimal'], 4)} |"
        for r, d in study["decision"]["ratios"].items()
    )
    log_decisiones = "\n".join(
        f"| {d['decision']} | {d['data']} | `{d['evidence']}` |" for d in metrics["decision_log"]
    )

    holdout = (
        f"## Holdout fresco 2026 (nunca usado en ninguna decisión)\n\n{_tabla_desempeno(metrics['splits']['holdout_2026'], B)}"
        if "holdout_2026" in metrics["splits"]
        else "## Holdout fresco 2026\n\nNo disponible en esta corrida (`make data-holdout`)."
    )

    return f"""# Model card — {metadata["model_name"]} {metadata["model_version"]}

> Generada automáticamente por `mdva.modeling.model_card` desde `metadata.json`, `{metadata["metrics_path"]}`
> y `reports/metrics/rain_classifier/study/study.json`. No editar a mano.

## Qué predice

Probabilidad calibrada de que en la celda de reanálisis ERA5 que contiene un punto del Valle de Aburrá caiga lluvia
apreciable (≥ {metadata["label"]["threshold_mm"]} mm) en una hora dada, a partir del pronóstico horario de Open-Meteo
para ese punto ({len(metadata["features"])} features, contrato v{metadata["feature_contract_version"]}: variables de la
hora, ventana t−2…t+2 del mismo pronóstico y ubicación; ver `docs/features.md`).

**Uso previsto**: alertas de lluvia para planificar trayectos (VERDE < {metadata["alert_thresholds"]["amarillo"]},
AMARILLO ≤ {metadata["alert_thresholds"]["rojo"]}, ROJO > {metadata["alert_thresholds"]["rojo"]}).
**No** es un pronóstico de intensidad ni de lluvia medida en un punto exacto.

## Modelo

- **{FAMILIAS[elegido["family"]]}** `{elegido["params"]}`.
- Elegido con validación cruzada temporal *rolling origin* ({len(study["folds"])} folds trimestrales 2023-T3 → 2024-T4,
  ventana creciente, hueco de 24 h) entre {len(busqueda["trials"])} configuraciones ({busqueda["n_hgb_trials"]} HGB por
  búsqueda aleatoria + familias de referencia), con la **regla de un error estándar** (la más simple a ≤ 1 EE de la mejor).
- Frente a la configuración 1.0.0 en la misma CV: Δ log loss {_f(busqueda["chosen_vs_v1"]["mean"], 4)} ± {_f(busqueda["chosen_vs_v1"]["se"], 4)}
  ({"mejora en más de 1 EE" if busqueda["chosen_vs_v1"]["better_by_1se"] else "sin mejora mayor a 1 EE"}).
- Calibración: `{metadata["calibration"]["method"]}`, mapa ajustado sobre {metadata["calibration"]["fitted_on"]}.
- Tamaño: {_f(metadata["size_bytes"] / 1e6, 2)} MB · scikit-learn {metadata["library_versions"]["scikit-learn"]} · semilla {metadata["seed"]}.

| Familia (mejor configuración) | Log loss CV (media ± EE) | ROC-AUC CV | Hiperparámetros |
|---|---|---|---|
{familias}

Sensibilidad por hiperparámetro: `reports/figures/study_hgb_sensitivity.png`.

## Datos

| Periodo | Rango (UTC) | Filas | Tasa de lluvia | Uso |
|---|---|---|---|---|
| Desarrollo | {sp["development"]["start"][:10]} → {sp["development"]["end"][:10]} (sin jun–jul 2022) | {sp["development"]["rows"]:,} | {_pct(sp["development"]["rain_rate"])} | todas las decisiones (CV) y el ajuste final |
| Prueba 2025 | {sp["test"]["start"][:10]} → {sp["test"]["end"][:10]} | {sp["test"]["rows"]:,} | {_pct(sp["test"]["rain_rate"])} | evaluación (ya usada para reportar 1.0.0) |
| Holdout 2026 | {sp.get("holdout_2026", {}).get("start", "—")[:10]} → {sp.get("holdout_2026", {}).get("end", "—")[:10]} | {sp.get("holdout_2026", {}).get("rows", 0):,} | {_pct(sp.get("holdout_2026", {}).get("rain_rate"))} | evaluación única, nunca vista |

13 estaciones SIATA como ubicaciones (5 celdas ERA5). Huella del dataset: `{metadata["dataset_fingerprint"][:16]}…`.

{holdout}

## Desempeño en prueba 2025

{_tabla_desempeno(metrics["splits"]["test_2025"], B)}

## Qué features importan y por qué (desarrollo, *out-of-fold*)

### Candidatas evaluadas (configuración de referencia 1.0.0)

| Conjunto | Log loss CV | Δ vs base (± EE) | Log loss CV espacial (celda fuera) |
|---|---|---|---|
{candidatos}

| Aporte marginal | Δ log loss (± EE) | > 1 EE |
|---|---|---|
{marginal}

### Ablación del modelo elegido (Δ log loss al quitar el grupo; positivo = el grupo ayuda)

| Grupo | Features | Δ log loss (± EE) |
|---|---|---|
{ablacion}

### Importancia por permutación (aumento del log loss, IC 95 % entre folds × repeticiones)

| # | Feature | Importancia |
|---|---|---|
{importancia}

### Dependencia parcial de las principales, contrastada con la física

| Feature | Tendencia de la PDP | Esperado |
|---|---|---|
{pdp}

**Ciclo diurno** (dependencia parcial conjunta de `hour_sin` y `hour_cos`): {horario}

Figuras: `reports/figures/study_permutation_importance.png`, `study_partial_dependence.png`, `study_hour_profile.png`, `study_ablation.png`.

**Curva de aprendizaje** (log loss medio en los 3 folds recientes según los meses de entrenamiento): {curva}.
Figura: `reports/figures/study_learning_curve.png`.

## Dónde falla (predicciones *out-of-fold* de desarrollo)

| Temporada | Horas | Llueve | Predicho medio | ROC-AUC | ECE |
|---|---|---|---|---|---|
{temporada}

- Horas locales con peor Brier: {peores("hour_local")}.
- Celdas ERA5 con peor Brier: {peores("era5_cell")}.
- Por lluvia pronosticada (mm/h): {peores("forecast_precip_mm")}.

## Calibración y umbrales

Calibración elegida por *cross-fitting* temporal (cada fold se calibra solo con los anteriores):

| Método | Log loss | ECE |
|---|---|---|
{calibracion}

Curvas de costo (costo de una falsa alarma = 1, de una lluvia no avisada = r). Con probabilidades calibradas el umbral
óptimo teórico es 1/(1+r); el óptimo empírico coincide, lo que confirma la calibración. *Regret* = costo extra por hora
de usar el corte de negocio en lugar del óptimo:

| Razón de costo | Umbral teórico | Umbral óptimo | *Regret* AMARILLO (0.40) | *Regret* ROJO (0.70) |
|---|---|---|---|---|
{decision}

Lectura: 0.40 es casi óptimo cuando no avisar una lluvia cuesta 1–2 veces una falsa alarma (alerta de "lleve paraguas");
0.70 corresponde a una alerta fuerte en la que las falsas alarmas se penalizan más. Se conservan (charter RF-10).
Figuras: `reports/figures/study_calibration.png`, `study_decision_cost.png`, `{metadata["model_name"]}_reliability.png`.

## Validación externa contra pluviómetros SIATA (jun–jul 2022, fuera del entrenamiento)

{ext["n"]:,} horas-estación; llueve en el pluviómetro en el {_pct(ext["rain_rate_obs"])}.

| Puntaje | ROC-AUC frente a la lluvia medida |
|---|---|
| Modelo | {_f(ext["roc_auc"]["model"])} |
| Precipitación pronosticada (cruda) | {_f(ext["roc_auc"]["raw_forecast_mm"])} |
| Precipitación de referencia ERA5 (la etiqueta) | {_f(ext["roc_auc"]["label_reference_mm"])} |

## Registro de decisiones (qué periodo tocó cada una)

| Decisión | Datos usados | Evidencia |
|---|---|---|
{log_decisiones}

## Limitaciones

- La etiqueta es reanálisis (ERA5, ~25 km), no lluvia medida: el modelo predice lluvia **de la celda**. Frente a
  pluviómetros, la concordancia horaria es baja con cualquier fuente de malla (`reports/metrics/label_validation.json`).
- Las 13 estaciones caen en 5 celdas y sus etiquetas están muy correlacionadas: hay muchas menos observaciones
  independientes que filas. Por eso los IC se calculan remuestreando días completos.
- La ubicación generaliza a celdas no vistas dentro del valle (validación espacial), pero no se evaluó fuera de él;
  el contrato rechaza coordenadas fuera del Valle de Aburrá.
- La tasa de lluvia varía entre años; la calibración se ajustó con predicciones *out-of-fold* de 2023–2024.
- 2025 ya se había usado para reportar la versión 1.0.0; por eso el holdout 2026 es la estimación más limpia.
"""
