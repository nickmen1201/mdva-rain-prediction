import json

import pytest

from mdva import config
from mdva.modeling import model_card, train
from mdva.modeling.predict import model_dir

CARPETA = model_dir(train.MODEL_VERSION)


@pytest.mark.skipif(not (CARPETA / "metadata.json").exists(), reason="modelo no entrenado (make train)")
def test_model_card_versionada_coincide_con_metricas():
    metadata = json.loads((CARPETA / "metadata.json").read_text(encoding="utf-8"))
    metrics = json.loads((config.PROJ_ROOT / metadata["metrics_path"]).read_text(encoding="utf-8"))
    assert (CARPETA / "model_card.md").read_text(encoding="utf-8") == model_card.render(metadata, metrics)
