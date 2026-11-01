import json

import pytest

from mdva import readme


@pytest.mark.skipif(not readme.metrics_path().exists(), reason="modelo no entrenado (make train)")
def test_tabla_del_readme_sale_de_metrics_json():
    metrics = json.loads(readme.metrics_path().read_text(encoding="utf-8"))
    actual = readme.README.read_text(encoding="utf-8")
    assert actual == readme.updated(actual, metrics)
