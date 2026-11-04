import numpy as np
import pytest
from PIL import Image

from photobot.cli import Resultado, main, salvar_camadas
from photobot.psd import Camada, salvar_psd

psd_tools = pytest.importorskip("psd_tools")


def _abrir(caminho):
    return psd_tools.PSDImage.open(caminho)


def test_psd_camadas_e_composta(tmp_path):
    a = Image.new("RGB", (64, 48), (200, 10, 10))
    b = Image.new("RGB", (64, 48), (10, 200, 10))
    m = np.zeros((48, 64), np.float32)
    m[10:30, 10:40] = 1
    caminho = salvar_psd(
        [Camada("Original", a), Camada("Editada", b), Camada("Atleta recortado", b, m, visivel=False)],
        tmp_path / "x",
    )
    assert caminho.suffix == ".psd"
    psd = _abrir(caminho)
    assert psd.size == (64, 48)
    assert [c.name for c in psd] == ["Original", "Editada", "Atleta recortado"]
    assert [c.visible for c in psd] == [True, True, False]
    assert psd[0].topil().getpixel((5, 5)) == (200, 10, 10)
    recorte = psd[2].topil()
    assert recorte.mode == "RGBA" and recorte.getpixel((20, 20))[3] == 255 and recorte.getpixel((0, 0))[3] == 0
    assert psd.topil().getpixel((5, 5)) == (10, 200, 10)


def test_psd_tamanho_diferente_falha(tmp_path):
    with pytest.raises(ValueError):
        salvar_psd([Camada("a", Image.new("RGB", (10, 10))), Camada("b", Image.new("RGB", (11, 10)))], tmp_path / "x")


def test_salvar_camadas_sem_mascara(tmp_path):
    res = Resultado(Image.new("RGB", (30, 20)), Image.new("RGB", (30, 20), (255, 255, 255)))
    assert [c.name for c in _abrir(salvar_camadas(res, tmp_path / "y"))] == ["Original", "Editada"]


def test_cli_psd(tmp_path):
    entrada, saida = tmp_path / "in", tmp_path / "out"
    entrada.mkdir()
    Image.new("RGB", (1200, 1500), (90, 90, 90)).save(entrada / "foto.png")
    main([str(entrada), str(saida), "--psd", "-p", "nenhum"])
    assert sorted(p.name for p in saida.iterdir()) == ["foto_nenhum_feed.jpg", "foto_nenhum_feed.psd"]
    assert _abrir(saida / "foto_nenhum_feed.psd").size == (1080, 1350)
