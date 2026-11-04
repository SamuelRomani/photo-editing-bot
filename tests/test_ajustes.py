import numpy as np
import pytest
from PIL import Image

from photobot import ajustes as a
from photobot.cli import editar
from photobot.estilo import transferir_estilo
from photobot.presets import PRESETS


def foto_teste(w=300, h=375, seed=1):
    """Gradiente colorido com ruído e uma dominante amarelada."""
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[0:h, 0:w] / max(w, h)
    arr = np.stack([0.3 + 0.5 * x, 0.25 + 0.5 * y, 0.15 + 0.3 * x * y], axis=2)
    arr += rng.normal(0, 0.03, arr.shape)
    return a.para_imagem(arr.astype(np.float32))


def media(img):
    return a.para_array(img).mean(axis=(0, 1))


def test_brilho_e_contraste():
    img = foto_teste()
    assert media(a.brilho(img, 0.1)).mean() > media(img).mean()
    assert a.para_array(a.contraste(img, 1.5)).std() > a.para_array(img).std()
    assert a.contraste(img, 1.0).tobytes() == img.tobytes()


def test_saturacao_zero_e_cinza():
    arr = a.para_array(a.saturacao(foto_teste(), 0))
    assert np.abs(arr[..., 0] - arr[..., 2]).max() < 2 / 255


def test_balanco_branco_neutraliza_dominante():
    img = foto_teste()
    antes = media(img)
    depois = media(a.balanco_branco(img))
    assert np.ptp(depois) < np.ptp(antes) / 2


def test_auto_niveis_usa_faixa_toda():
    img = a.contraste(foto_teste(), 0.3)
    lum = a.luminancia(a.para_array(a.auto_niveis(img)))
    assert lum.min() < 0.02 and lum.max() > 0.93


def test_auto_niveis_imagem_lisa_nao_quebra():
    img = Image.new("RGB", (50, 50), (120, 120, 120))
    assert a.auto_niveis(img).tobytes() == img.tobytes()


def test_vinheta_escurece_bordas():
    img = Image.new("RGB", (200, 200), (200, 200, 200))
    arr = a.para_array(a.vinheta(img, 0.5))
    assert arr[0, 0].mean() < arr[100, 100].mean() - 0.2


def test_granulacao_reprodutivel():
    img = foto_teste()
    assert a.granulacao(img, semente=3).tobytes() == a.granulacao(img, semente=3).tobytes()


def test_transferir_estilo_de_pb_gera_pb():
    ref = a.preto_e_branco(foto_teste(seed=2))
    arr = a.para_array(transferir_estilo(foto_teste(), ref, 1.0))
    assert np.abs(arr[..., 0] - arr[..., 1]).mean() < 0.02


@pytest.mark.parametrize("preset", list(PRESETS))
def test_presets_mantem_tamanho_e_modo(preset):
    img = foto_teste()
    out = PRESETS[preset](img)
    assert out.size == img.size and out.mode == "RGB"


def test_pb_dramatico_e_pb_e_contrastado():
    img = foto_teste()
    arr = a.para_array(PRESETS["pb_dramatico"](img))
    assert np.abs(arr[..., 0] - arr[..., 2]).max() < 2 / 255
    assert arr.std() > a.para_array(img).std()


def test_editar_pipeline_completo():
    out = editar(foto_teste(800, 600), "feed", "frio_dessaturado", foto_teste(seed=5), 0.5)
    assert out.size == (1080, 1350)
