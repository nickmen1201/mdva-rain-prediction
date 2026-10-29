# Data Model: Entrenamiento y evaluación

## Splits (máscaras sobre `rain_hourly`)

| Split | Desde (UTC) | Hasta (UTC) | Notas |
|---|---|---|---|
| train | 2022-01-01T00 | 2023-12-31T23 | excluye 2022-06-01 → 2022-07-31 |
| validation | 2024-01-02T00 | 2024-12-31T23 | 24 h de separación |
| test | 2025-01-02T00 | 2025-12-31T23 | 24 h de separación; se usa una vez |
| external | 2022-06-07 → 2022-07-07 | — | horas-estación con lluvia SIATA válida |

## Metrics report (`reports/metrics/rain_classifier/<version>/metrics.json`)

```text
{
  model_version, dataset_fingerprint, bootstrap: {B, block: "day_utc", seed},
  selection: {candidates: [{name, params, val_log_loss}], chosen},
  calibration_choice: {isotonic: ll, sigmoid: ll, chosen},
  splits: {validation|test: {models: {<nombre>: {roc_auc, pr_auc, brier, log_loss, bss, ece, ci95: {...}}},
                              paired_vs_model: {<baseline>: {brier_diff, log_loss_diff, ci95}}}},
  reliability: {test: [{bin, mean_pred, obs_rate, n}]},
  alert_levels: {test: {levels: {VERDE|AMARILLO|ROJO: {share, rain_rate}}, ge_amarillo: {precision, recall}, rojo: {precision, recall}}},
  external_siata: {n, rain_rate_obs, roc_auc: {model, forecast, label_reference}, kappa_model_at_amarillo},
  claims: {beats_climatology: bool, beats_raw_forecast: bool, ece_below_0_03: bool}
}
```

Nombres de modelos en el reporte: `model` (calibrado), `climatology`, `raw_forecast`, `logistic`, `persistence_reference`.

## Run record (`reports/runs/<UTC>_<sha>.json`)

`{run_at_utc, git_sha, dirty_worktree, model_version, dataset_fingerprint, seed, grid, chosen_params, calibration, val_metrics, test_metrics, duration_s}`
