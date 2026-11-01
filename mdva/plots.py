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
    "model_1_0_0": "Modelo 1.0.0",
    "logistic": "Regresión logística",
    "raw_forecast": "Pronóstico crudo",
    "climatology": "Climatología",
}


def reliability_diagram(filas: list[dict], path: Path, extra: dict | None = None) -> None:
    """Curva de confiabilidad de la prueba 2025 y, si se pasan, de otros periodos (holdout 2026)."""
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], "--", color="grey", label="Calibración perfecta")
    series = {"prueba 2025": filas, **{k: v for k, v in (extra or {}).items() if v}}
    for nombre, fs in series.items():
        ax.plot([f["mean_pred"] for f in fs], [f["obs_rate"] for f in fs], "o-", label=f"Modelo ({nombre})")
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


# ── Estudio de modelado (spec 012) ───────────────────────────────────────────


def study_figures(study: dict, out_dir: Path) -> None:
    sensitivity(study["search"]["trials"], out_dir / "study_hgb_sensitivity.png")
    permutation(study["permutation_importance"], out_dir / "study_permutation_importance.png")
    partial_dependence_plot(study["partial_dependence"], out_dir / "study_partial_dependence.png")
    hour_profile_plot(study["hour_profile"], out_dir / "study_hour_profile.png")
    ablation(study["ablation"], out_dir / "study_ablation.png")
    learning(study["learning_curve"], out_dir / "study_learning_curve.png")
    calibration_comparison(study["calibration"], out_dir / "study_calibration.png")
    cost(study["decision"], out_dir / "study_decision_cost.png")


def sensitivity(trials: list[dict], path: Path) -> None:
    hgb = [t for t in trials if t["family"] == "hgb"]
    params = list(hgb[0]["params"])
    fig, axes = plt.subplots(2, 3, figsize=(12, 7))
    ll = np.array([t["mean"]["log_loss"] for t in hgb])
    for ax, p in zip(axes.ravel(), params, strict=False):
        x = [t["params"][p] for t in hgb]
        ax.scatter(x, ll, s=14, alpha=0.7)
        if p in ("learning_rate", "l2_regularization", "max_leaf_nodes"):
            ax.set_xscale("log")
        ax.set_xlabel(p)
        ax.set_ylabel("log loss medio (CV)")
    fig.suptitle("Sensibilidad de HistGradientBoosting (60 ensayos, CV rolling-origin)")
    _guardar(fig, path)


def permutation(rows: list[dict], path: Path) -> None:
    rows = rows[::-1]
    fig, ax = plt.subplots(figsize=(7, 0.32 * len(rows) + 1.5))
    y = np.arange(len(rows))
    m = np.array([r["mean"] for r in rows])
    lo = m - np.array([r["ci95"][0] for r in rows])
    hi = np.array([r["ci95"][1] for r in rows]) - m
    ax.barh(y, m, xerr=[lo, hi], color="#4C78A8", capsize=2)
    ax.set_yticks(y, [r["feature"] for r in rows])
    ax.axvline(0, color="grey", lw=0.8)
    ax.set_xlabel("Aumento del log loss al permutar (IC 95 %)")
    ax.set_title("Importancia por permutación (folds de validación)")
    _guardar(fig, path)


def partial_dependence_plot(pdp: dict, path: Path) -> None:
    fig, axes = plt.subplots(1, len(pdp), figsize=(4 * len(pdp), 3.6), squeeze=False)
    for ax, (feat, d) in zip(axes[0], pdp.items(), strict=True):
        for curva in d["ice_sample"]:
            ax.plot(d["grid"], curva, color="#9ecae1", lw=0.6, alpha=0.6)
        ax.plot(d["grid"], d["pdp"], color="#08519c", lw=2.2, label="PDP")
        ax.set_xlabel(feat)
        ax.set_title(d["trend"])
    axes[0][0].set_ylabel("P(lluvia)")
    fig.suptitle("Dependencia parcial (azul) e ICE (celeste)")
    _guardar(fig, path)


def hour_profile_plot(perfil: dict, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.5, 3.6))
    m = perfil["model"]
    o = perfil["observed_rate_last_fold"]
    ax.plot([f["hour_local"] for f in m], [f["mean_probability"] for f in m], "o-", label="Modelo (PD conjunta)")
    ax.plot(
        [f["hour_local"] for f in o], [f["rain_rate"] for f in o], "s--", alpha=0.7, label="Observado (último fold)"
    )
    ax.set_xticks(range(0, 24, 3))
    ax.set_xlabel("Hora local (Bogotá)")
    ax.set_ylabel("P(lluvia)")
    ax.set_title("Ciclo diurno aprendido")
    ax.legend()
    _guardar(fig, path)


def ablation(ab: dict, path: Path) -> None:
    items = sorted(ab.items(), key=lambda kv: kv[1]["delta_vs_full"]["mean"])
    fig, ax = plt.subplots(figsize=(7, 4))
    y = np.arange(len(items))
    ax.barh(
        y,
        [v["delta_vs_full"]["mean"] for _, v in items],
        xerr=[v["delta_vs_full"]["se"] for _, v in items],
        color="#F58518",
        capsize=2,
    )
    ax.set_yticks(y, [k for k, _ in items])
    ax.axvline(0, color="grey", lw=0.8)
    ax.set_xlabel("Δ log loss al quitar el grupo (± EE entre folds)")
    ax.set_title("Ablación por grupos de features")
    _guardar(fig, path)


def learning(rows: list[dict], path: Path) -> None:
    fig, ax = plt.subplots(figsize=(5, 3.6))
    etiquetas = [str(r["train_months"]) for r in rows]
    ax.plot(etiquetas, [r["mean_log_loss"] for r in rows], "o-")
    ax.set_xlabel("Meses de entrenamiento antes del fold")
    ax.set_ylabel("log loss medio (3 folds recientes)")
    ax.set_title("Curva de aprendizaje")
    _guardar(fig, path)


def calibration_comparison(cal: dict, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot([0, 1], [0, 1], "--", color="grey")
    for m, d in cal["methods"].items():
        filas = d["reliability"]
        ax.plot(
            [f["mean_pred"] for f in filas], [f["obs_rate"] for f in filas], "o-", label=f"{m} (ECE {d['ece']:.3f})"
        )
    ax.set_xlabel("Probabilidad predicha")
    ax.set_ylabel("Frecuencia observada")
    ax.set_title("Calibración cross-fitted (OOF desarrollo)")
    ax.legend()
    _guardar(fig, path)


def cost(dec: dict, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6.5, 4))
    t = dec["thresholds"]
    for r, d in dec["ratios"].items():
        base = d["never_alert_cost"] or 1.0
        ax.plot(t, np.array(d["cost"]) / base, label=f"lluvia no avisada = {r}× falsa alarma")
    for b in (0.40, 0.70):
        ax.axvline(b, color="grey", ls=":", lw=1)
    ax.set_xlabel("Umbral de alerta")
    ax.set_ylabel("Costo relativo a no alertar nunca")
    ax.set_title("Curvas de costo de decisión (OOF calibrado)")
    ax.legend(fontsize=8)
    _guardar(fig, path)


def _guardar(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
