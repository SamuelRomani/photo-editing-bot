import zipfile

import pytest
from PIL import Image

gr = pytest.importorskip("gradio")

from photobot.app import criar_app, editar_lote, editar_uma  # noqa: E402

OPCOES = ["P&B dramático", "Quadrado (1080x1080)", None, 0.8, 0.0, 0.0, "Desligada", 5, 10, -20, 3]


def test_criar_app():
    assert isinstance(criar_app(), gr.Blocks)


def test_editar_uma():
    img = Image.new("RGB", (1200, 900), (180, 120, 90))
    (antes, depois), arquivo, psd = editar_uma(img, *OPCOES)
    assert depois.size == (1080, 1080) and antes.size == depois.size
    assert Image.open(arquivo).size == (1080, 1080)
    assert psd is None


def test_editar_uma_com_psd():
    img = Image.new("RGB", (1200, 900), (180, 120, 90))
    _, arquivo, psd = editar_uma(img, *OPCOES, True, "Nenhum")
    assert psd.endswith(".psd") and open(psd, "rb").read(4) == b"8BPS"


def test_editar_uma_sem_foto():
    with pytest.raises(gr.Error):
        editar_uma(None, *OPCOES)


def test_editar_lote(tmp_path):
    caminhos = []
    for i in range(2):
        p = tmp_path / f"f{i}.png"
        Image.new("RGB", (800, 1000), (40 * i, 90, 120)).save(p)
        caminhos.append(str(p))
    galeria, zip_path = editar_lote(caminhos, *OPCOES, progress=lambda *a, **k: None)
    assert len(galeria) == 2
    assert sorted(zipfile.ZipFile(zip_path).namelist()) == ["f0_editada.jpg", "f1_editada.jpg"]


def test_editar_lote_com_psd(tmp_path):
    p = tmp_path / "f.png"
    Image.new("RGB", (800, 1000), (40, 90, 120)).save(p)
    galeria, zip_path = editar_lote([str(p)], *OPCOES, True, "Nenhum", progress=lambda *a, **k: None)
    assert len(galeria) == 1
    assert sorted(zipfile.ZipFile(zip_path).namelist()) == ["f_editada.jpg", "f_editada.psd"]
