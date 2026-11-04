import pytest
from PIL import Image

from photobot.cli import processar_pasta
from photobot.formatos import FORMATOS, ajustar_formato
from photobot.io import carregar


@pytest.mark.parametrize("formato", list(FORMATOS))
@pytest.mark.parametrize("origem", [(4000, 3000), (3000, 4000), (800, 800)])
def test_ajustar_formato_tamanho_exato(formato, origem):
    img = Image.new("RGB", origem, "gray")
    assert ajustar_formato(img, formato).size == FORMATOS[formato]


def test_formato_invalido():
    with pytest.raises(ValueError):
        ajustar_formato(Image.new("RGB", (10, 10)), "tiktok")


def test_processar_pasta(tmp_path):
    entrada, saida = tmp_path / "in", tmp_path / "out"
    entrada.mkdir()
    Image.new("RGB", (2000, 1500), "red").save(entrada / "a.png")
    Image.new("RGB", (1500, 2000), "blue").save(entrada / "b.jpg")
    (entrada / "nota.txt").write_text("ignorar")

    gerados = processar_pasta(entrada, saida, "feed", "nenhum")

    assert [g.name for g in gerados] == ["a_nenhum_feed.jpg", "b_nenhum_feed.jpg"]
    assert all(carregar(g).size == (1080, 1350) for g in gerados)
