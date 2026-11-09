"""Integración con TensorFlow (marca ml): corrida mínima de punta a punta en CPU (T018)."""

import copy
import os

import numpy as np
import pytest

pytestmark = pytest.mark.ml

tf = pytest.importorskip("tensorflow")

from avocadoia_datos.es_csv import leer_csv, leer_json  # noqa: E402

from avocadoia_modelo import config as mc  # noqa: E402
from avocadoia_modelo import entrenamiento, evaluacion, preparacion, registro  # noqa: E402


def _cache_sintetica(tmp_path):
    """12 imágenes 224 × 224 con un patrón de color por clase, en el formato de preparacion."""
    rng = np.random.default_rng(0)
    huella = "c" * 64
    ruta = preparacion.directorio(str(tmp_path / "drive"), preparacion.huella_cache(huella))
    os.makedirs(ruta)
    for p, n in (("train", 6), ("val", 3), ("test", 3)):
        y = np.array([i % 3 for i in range(n)], dtype=np.int8)
        x = rng.integers(0, 40, (n, 224, 224, 3)).astype(np.uint8)
        for i, c in enumerate(y):
            x[i, :, :, c] += 200
        np.savez(os.path.join(ruta, f"{p}.npz"), x=x, y=y, sha256=np.array([f"{p}{i}" for i in range(n)]),
                 fuente=np.array(["sintetica"] * n))
    return ruta, huella


def _cfg():
    cfg = mc.cargar("config/modelo.toml", entorno_="pc")
    cfg = copy.deepcopy(cfg)
    cfg["fase1"]["epocas"] = 1
    cfg["fase2"]["epocas"] = 1
    cfg["entrenamiento"]["lote"] = 4
    cfg["entrenamiento"]["deterministico"] = False
    cfg["evaluacion"]["bootstrap"] = 20
    cfg["evaluacion"]["min_por_fuente"] = 1
    return mc.con_corrida(cfg, "mobilenetv3", 42)


def test_corrida_minima(tmp_path, monkeypatch):
    cache, huella = _cache_sintetica(tmp_path)
    repo, salida = str(tmp_path / "repo"), str(tmp_path / "drive")
    verificacion = {"huella_manifiesto": huella, "estado": "ok_con_avisos",
                    "etiquetas_provisionales": {"train": 1}, "fuga_por_fruto": {"grupos": 0}}
    pedidas = []
    original = preparacion.cargar
    monkeypatch.setattr(preparacion, "cargar", lambda r, p: pedidas.append(p) or original(r, p))

    cfg = _cfg()
    id_ = entrenamiento.entrenar(cfg, cache, repo, salida, verificacion, pesos=None)
    assert "test" not in pedidas, "entrenar no debe abrir la partición de prueba (FR-005)"
    reg = registro.leer_registro(repo, id_)
    assert reg["estado"] == "en_curso" and reg["fase1_completa"] and reg["experimental"] is True
    assert reg["huella_config"] == mc.huella_config(cfg)

    res = evaluacion.evaluar(cfg, id_, cache, repo, salida)
    registro.actualizar_estado(repo, id_, "completa")
    assert set(res) == {"val", "test"} and res["test"]["n"] == 3
    dir_repo = os.path.join(repo, "experimentos", id_)
    for archivo in ("registro.json", "historial.csv", "curvas.png", "metricas.json", "matriz_confusion_test.csv"):
        assert os.path.exists(os.path.join(dir_repo, archivo)), archivo
    assert [f["fase"] for f in leer_csv(os.path.join(dir_repo, "historial.csv"))] == ["fase1", "fase2"]
    assert leer_json(os.path.join(dir_repo, "registro.json"))["estado"] == "completa"
    assert leer_csv(os.path.join(repo, "bitacora.csv"))[0]["id"] == id_
    assert os.path.exists(os.path.join(salida, "experimentos", id_, "logits.npz"))


def test_reanudacion_reutiliza_id(tmp_path):
    cache, huella = _cache_sintetica(tmp_path)
    repo, salida = str(tmp_path / "repo"), str(tmp_path / "drive")
    ver = {"huella_manifiesto": huella, "estado": "ok"}
    cfg = _cfg()
    id1 = entrenamiento.entrenar(cfg, cache, repo, salida, ver, pesos=None)
    registro.actualizar_estado(repo, id1, "incompleta")   # simula una desconexión de Colab
    id2 = entrenamiento.entrenar(cfg, cache, repo, salida, ver, pesos=None)
    assert id2 == id1
    assert registro.leer_registro(repo, id1)["estado"] == "en_curso"


def test_bn_congelada_en_fase2():
    from avocadoia_modelo import arquitecturas
    import keras

    _, capas, _ = arquitecturas.construir("mobilenetv3", pesos=None)
    arquitecturas.descongelar_fase2(capas, 0.30)
    assert not any(c.trainable for c in capas if isinstance(c, keras.layers.BatchNormalization))
    assert capas[-1].trainable or isinstance(capas[-1], keras.layers.BatchNormalization) or capas[-2].trainable
    assert not capas[0].trainable


def test_cam_equivale_a_cabeza():
    """T031: con GAP → Dense, la media espacial de CAM (sin ReLU ni normalizar) = logit − sesgo."""
    from avocadoia_modelo import arquitecturas, explicacion

    modelo, _, _ = arquitecturas.construir("mobilenetv3", pesos=None)
    x = np.random.default_rng(1).integers(0, 255, (2, 224, 224, 3)).astype(np.float32)
    clases = np.array([0, 2])
    mapas = explicacion.cam(modelo, x, clases, normalizar=False)
    logits = modelo.predict(x, verbose=0)
    sesgo = modelo.get_layer("logits").get_weights()[1]
    esperado = logits[np.arange(2), clases] - sesgo[clases]
    assert np.allclose(mapas.mean(axis=(1, 2)), esperado, atol=1e-3)


def test_gradcam_forma_y_rango():
    from avocadoia_modelo import arquitecturas, explicacion

    modelo, _, _ = arquitecturas.construir("efficientnetb0", pesos=None)
    x = np.random.default_rng(2).integers(0, 255, (3, 224, 224, 3)).astype(np.float32)
    m = explicacion.gradcam_pp(modelo, x, np.array([0, 1, 2]))
    assert m.shape == (3, 7, 7) and m.min() >= 0 and m.max() <= 1


def test_spike_explain(tmp_path):
    """T030: el spike corre de punta a punta y deja resultado.json con una decisión."""
    from avocadoia_modelo import exportacion

    cache, _ = _cache_sintetica(tmp_path)
    repo = str(tmp_path / "repo")
    res = exportacion.spike_explain(_cfg(), cache, repo, str(tmp_path / "drive"), pesos=None, n_comparar=3)
    assert res["decision"] in ("gradcam++", "cam", "sin_explain")
    assert res["variante_cam"]["convierte"], res["variante_cam"]["error"]
    assert os.path.exists(os.path.join(repo, "spike_explain", "resultado.json"))
    assert os.path.exists(os.path.join(repo, "spike_explain", "comparacion.png"))
