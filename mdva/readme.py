"""Genera la tabla de resultados del README desde `metrics.json` (charter R-44: ninguna cifra a mano).

Reemplaza dos bloques: el titular (`<!-- headline:start/end -->`, modelo frente al pronóstico que ya
existe) y la tabla completa (`<!-- metrics:start/end -->`). `tests/test_readme.py` verifica que el
README versionado coincida con lo que generaría este módulo.

Uso: `make readme`
"""

from __future__ import annotations

import json

from mdva import config

README = config.PROJ_ROOT / "README.md"
START, END = "<!-- metrics:start -->", "<!-- metrics:end -->"
HEAD_START, HEAD_END = "<!-- headline:start -->", "<!-- headline:end -->"
VERSION = "1.1.0"
NOMBRES = {
    "model": "**rain_classifier 1.1.0**",
    "model_1_0_0": "rain_classifier 1.0.0",
    "logistic": "Regresión logística",
    "climatology": "Climatología (hora × mes)",
    "raw_forecast": "Pronóstico crudo de Open-Meteo",
}


def metrics_path(version: str = VERSION):
    return config.METRICS_DIR / "rain_classifier" / version / "metrics.json"


def render(metrics: dict) -> str:
    lineas = [START, ""]
    titulos = {"holdout_2026": "Holdout fresco 2026 (nunca usado en ninguna decisión)", "test_2025": "Prueba 2025"}
    for split in ("holdout_2026", "test_2025"):
        s = metrics["splits"].get(split)
        if not s:
            continue
        lineas += [
            f"**{titulos[split]}** — {s['period'][0][:10]} → {s['period'][1][:10]}, {s['rows']:,} horas-estación, "
            f"llueve en el {s['rain_rate'] * 100:.1f} %. IC 95 % por bootstrap en bloques de días.",
            "",
            "| Modelo | ROC-AUC | PR-AUC | Brier | BSS vs climatología | ECE |",
            "|---|---|---|---|---|---|",
        ]
        for k, nombre in NOMBRES.items():
            if k in s["models"]:
                m = s["models"][k]
                lo, hi = m["ci95"]["roc_auc"]
                lineas.append(
                    f"| {nombre} | {m['roc_auc']:.3f} [{lo:.3f}, {hi:.3f}] | {m['pr_auc']:.3f} | {m['brier']:.4f} | "
                    f"{m['bss']:.3f} | {m['ece']:.3f} |"
                )
        supera = [NOMBRES[b].strip("*") for b in NOMBRES if b != "model" and s["claims"].get(f"beats_{b}")]
        lineas += ["", f"Supera con IC pareado (Brier y log loss) a: {', '.join(supera)}.", ""]
    lineas.append(END)
    return "\n".join(lineas)


def render_headline(metrics: dict) -> str:
    """Pronóstico crudo de Open-Meteo frente al modelo, en los dos periodos nunca usados para decidir."""
    titulos = {"holdout_2026": "2026 (holdout, ene–oct)", "test_2025": "2025 (prueba, año completo)"}
    lineas = [
        HEAD_START,
        "",
        "| Periodo nunca visto | ROC-AUC: pronóstico → modelo | Brier: pronóstico → modelo | Error de probabilidad |",
        "|---|---|---|---|",
    ]
    for split, titulo in titulos.items():
        s = metrics["splits"].get(split)
        if not s:
            continue
        raw, mod = s["models"]["raw_forecast"], s["models"]["model"]
        reduccion = (1 - mod["brier"] / raw["brier"]) * 100
        lineas.append(
            f"| {titulo} | {raw['roc_auc']:.2f} → **{mod['roc_auc']:.2f}** | "
            f"{raw['brier']:.3f} → **{mod['brier']:.3f}** | **−{reduccion:.0f} %** |"
        )
    lineas += ["", HEAD_END]
    return "\n".join(lineas)


def _replace(text: str, start: str, end: str, block: str) -> str:
    i, j = text.index(start), text.index(end) + len(end)
    return text[:i] + block + text[j:]


def updated(readme: str, metrics: dict) -> str:
    readme = _replace(readme, HEAD_START, HEAD_END, render_headline(metrics))
    return _replace(readme, START, END, render(metrics))


def main() -> None:
    metrics = json.loads(metrics_path().read_text(encoding="utf-8"))
    README.write_text(updated(README.read_text(encoding="utf-8"), metrics), encoding="utf-8", newline="\n")
    print("README actualizado desde", metrics_path().relative_to(config.PROJ_ROOT))


if __name__ == "__main__":
    main()
