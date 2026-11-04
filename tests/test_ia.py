"""Testes da parte de IA.

Os testes de máscara usam uma máscara sintética (não precisam do rembg). Os que
precisam baixar modelos só rodam se as dependências estiverem instaladas.
"""

import numpy as np
import pytest
from PIL import Image

from photobot import ajustes as a
from photobot.ia import desfocar_fundo, garantir_resolucao, suavizar_mascara


def quadriculado(w=200, h=250, passo=10):
    y, x = np.mgrid[0:h, 0:w]
    arr = (((x // passo) + (y // passo)) % 2).astype(np.float32)
    return a.para_imagem(np.repeat(arr[..., None], 3, axis=2))


def mascara_centro(w=200, h=250):
    m = np.zeros((h, w), np.float32)
    m[60:190, 50:150] = 1
    return m


def test_desfocar_fundo_preserva_pessoa_e_borra_fundo():
    img = quadriculado(passo=3)
    out = a.para_array(desfocar_fundo(img, 0.8, mascara=mascara_centro()))
    orig = a.para_array(img)
    assert np.abs(out[110:140, 80:120] - orig[110:140, 80:120]).max() < 0.02
    assert out[:40].std() < orig[:40].std() / 3


def test_escurecer_fundo():
    img = Image.new("RGB", (200, 250), (200, 200, 200))
    out = a.para_array(desfocar_fundo(img, 0, escurecer=0.5, mascara=mascara_centro()))
    assert out[5, 5].mean() == pytest.approx(100 / 255, abs=0.02)
    assert out[125, 100].mean() == pytest.approx(200 / 255, abs=0.02)


def test_suavizar_mascara_fica_no_intervalo():
    m = suavizar_mascara(mascara_centro(), 4)
    assert m.min() >= 0 and m.max() <= 1 and 0 < m[60, 100] < 1


def test_garantir_resolucao_nao_mexe_em_foto_grande():
    img = Image.new("RGB", (2000, 3000))
    assert garantir_resolucao(img) is img


def _tem(modulo):
    try:
        __import__(modulo)
        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _tem("cv2.dnn_superres"), reason="opencv-contrib não instalado")
@pytest.mark.rede
def test_aumentar_resolucao_fsrcnn():
    from photobot.ia import aumentar_resolucao

    out = aumentar_resolucao(quadriculado(60, 80), 2, "fsrcnn")
    assert out.size == (120, 160)


@pytest.mark.skipif(not _tem("rembg"), reason="rembg não instalado")
@pytest.mark.rede
def test_mascara_pessoa_formato():
    from photobot.ia import mascara_pessoa

    m = mascara_pessoa(quadriculado())
    assert m.shape == (250, 200) and m.dtype == np.float32
