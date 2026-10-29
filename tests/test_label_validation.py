import numpy as np
import pandas as pd
import pytest

from mdva import label_validation as lv


def _siata_csv(tmp_path, minutos):
    df = pd.DataFrame(minutos, columns=["codigo_estacion", "fecha", "precipitacion_mm", "calidad"])
    ruta = tmp_path / "siata.csv"
    df.to_csv(ruta, index=False)
    return ruta


def test_hora_local_se_convierte_a_utc_y_filtra_calidad(tmp_path):
    minutos = [(59, f"2022-06-07 10:{m:02d}:00", 0.05, 1.0) for m in range(60)]
    minutos += [(59, "2022-06-07 11:00:00", 9.9, 4.0), (59, "2022-06-07 11:01:00", -1.0, 1.0)]
    horas, resumen = lv.siata_hourly(_siata_csv(tmp_path, minutos))
    assert horas["time_utc"].tolist() == [pd.Timestamp("2022-06-07 15:00", tz="UTC")]  # 10 h local = 15 h UTC
    assert horas["precip_obs_mm"].iloc[0] == pytest.approx(3.0)
    assert bool(horas["rain_obs"].iloc[0])
    assert resumen["minutes_discarded"] == 2


def test_horas_con_pocos_minutos_se_descartan(tmp_path):
    minutos = [(59, f"2022-06-07 10:{m:02d}:00", 0.0, 1.0) for m in range(49)]
    horas, resumen = lv.siata_hourly(_siata_csv(tmp_path, minutos))
    assert horas.empty and resumen["hours_discarded_low_coverage"] == 1


def test_umbral_por_igualacion_de_frecuencias():
    valores = pd.Series([0.0] * 85 + [0.4] * 5 + [0.6] * 10)  # ≥0.3 → 15 %, ≥0.5 → 10 %, ≥0.7 → 0 %
    umbral, tabla = lv.frequency_matched_threshold(valores, target_rate=0.11)
    assert umbral == 0.5
    assert {r["threshold_mm"]: r["rate"] for r in tabla}[0.3] == 0.15


def test_empate_de_frecuencias_elige_el_umbral_menor():
    umbral, _ = lv.frequency_matched_threshold(pd.Series([0.0] * 9 + [0.8]), target_rate=0.1)
    assert umbral == 0.1


def test_metricas_de_concordancia():
    obs = pd.Series([True, True, False, False])
    pred = pd.Series([True, False, True, False])
    a = lv.agreement(obs, pred)
    assert a["precision"] == 0.5 and a["recall"] == 0.5 and a["kappa"] == 0.0
    assert lv.agreement(obs, obs)["kappa"] == 1.0


def test_ventana_es_lluviosa_si_alguna_hora_lo_es():
    t = pd.date_range("2022-06-07", periods=6, freq="h", tz="UTC")
    df = pd.DataFrame({"station_id": 59, "time_utc": t, "rain_obs": [0, 0, 1, 0, 0, 0], "p": [1, 0, 0, 0, 0, 0]})
    w = lv.windowed(df.astype({"rain_obs": bool, "p": bool}), 3, "p")
    assert w["rain_obs"].tolist() == [True, False] and w["p"].tolist() == [True, False]


def test_calibra_con_la_primera_mitad_y_valida_con_la_segunda(tmp_path):
    rng = np.random.default_rng(0)
    inicio = pd.Timestamp("2022-06-07 00:00")
    horas_locales = pd.date_range(inicio, periods=200, freq="h")
    llueve = rng.random(200) < 0.2
    minutos = [
        (59, (h + pd.Timedelta(minutes=m)).strftime("%Y-%m-%d %H:%M:%S"), 0.01 if lluvia else 0.0, 1.0)
        for h, lluvia in zip(horas_locales, llueve)
        for m in range(60)
    ]
    t_utc = (horas_locales + pd.Timedelta(hours=5)).tz_localize("UTC")
    dataset = pd.DataFrame(
        {
            "station_id": np.int64(59),
            "time_utc": t_utc,
            "precipitation_ref": np.where(llueve, 0.8, 0.0),  # referencia perfecta a ≥ 0.5 mm
            "precipitation": np.where(rng.random(200) < 0.2, 0.8, 0.0),  # pronóstico aleatorio
            "era5_cell": "6.25,-75.5",
        }
    )
    r = lv.run(dataset=dataset, siata_csv=_siata_csv(tmp_path, minutos))
    assert r["calibration"]["rows"] + r["validation"]["rows"] == 200
    assert r["calibration"]["label_threshold_mm"] <= 0.7  # cualquier umbral ≤ 0.8 separa igual
    assert r["validation"]["rain_label"]["total"]["1h"]["kappa"] == 1.0
    assert r["validation"]["rain_forecast"]["total"]["1h"]["kappa"] < 0.5
    assert r["offset_kappa_label_1h"]["+0h"] == 1.0
    assert set(r["validation"]["rain_label"]["total"]) == {"1h", "3h", "6h"}
    assert r["stations_by_era5_cell"] == {"6.25,-75.5": [59]}
