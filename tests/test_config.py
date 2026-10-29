from mdva import config


def test_raiz_del_proyecto_contiene_el_paquete():
    assert (config.PROJ_ROOT / "mdva" / "config.py").is_file()
    assert (config.PROJ_ROOT / "pyproject.toml").is_file()


def test_carpetas_ccds_v2_existen():
    for carpeta in [
        config.RAW_DATA_DIR,
        config.INTERIM_DATA_DIR,
        config.PROCESSED_DATA_DIR,
        config.EXTERNAL_DATA_DIR,
        config.MODELS_DIR,
        config.FIGURES_DIR,
    ]:
        assert carpeta.is_dir(), carpeta


def test_rutas_cuelgan_de_la_raiz():
    assert config.DATA_DIR.parent == config.PROJ_ROOT
    assert config.RAW_DATA_DIR.parent == config.DATA_DIR
    assert config.FIGURES_DIR.parent == config.REPORTS_DIR
