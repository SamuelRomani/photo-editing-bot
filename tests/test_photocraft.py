"""Testes da integração com o PhotoCraft usando um photocraft-cli falso.

O falso imita o `batch`: lê as fotos de --in, inverte as cores e grava em --out.
"""

import json
import sys

import pytest
from PIL import Image

from photobot import photocraft
from photobot.cli import main

FALSO = '''
import json, sys
from pathlib import Path
from PIL import Image, ImageOps
args = sys.argv[1:]
Path(__file__).with_name("chamadas.json").write_text(json.dumps(args))
if "--falhar" in open(args[args.index("--actions") + 1]).read():
    print("comando desconhecido", file=sys.stderr)
    sys.exit(3)
entrada, saida = Path(args[args.index("--in") + 1]), Path(args[args.index("--out") + 1])
for p in entrada.iterdir():
    ImageOps.invert(Image.open(p).convert("RGB")).save(saida / (p.stem + ".png"))
'''


@pytest.fixture
def cli_falso(tmp_path, monkeypatch):
    script = tmp_path / "photocraft_falso.py"
    script.write_text(FALSO)
    monkeypatch.setenv("PHOTOCRAFT_CLI", f'"{sys.executable}" "{script}"')
    return tmp_path / "chamadas.json"


def test_sem_photocraft(monkeypatch):
    monkeypatch.delenv("PHOTOCRAFT_CLI", raising=False)
    monkeypatch.setattr(photocraft.shutil, "which", lambda _: None)
    assert not photocraft.disponivel()
    with pytest.raises(photocraft.PhotoCraftIndisponivel):
        photocraft.aplicar_acabamento(Image.new("RGB", (4, 4)), "nitidez")


def test_appimage_recebe_cli(monkeypatch):
    monkeypatch.setenv("PHOTOCRAFT_CLI", "/opt/photocraft-1.0-linux-x86_64.AppImage")
    assert photocraft.comando_cli() == ["/opt/photocraft-1.0-linux-x86_64.AppImage", "--cli"]


def test_acabamentos_padrao_sao_validos():
    todos = photocraft.acabamentos()
    assert {"nitidez", "curva_contraste", "nitidez_e_contraste"} <= set(todos)
    for arq in todos.values():
        for passo in json.loads(arq.read_text()):
            assert isinstance(passo["command"], str) and isinstance(passo["params"], dict)


def test_acabamento_do_usuario(tmp_path, monkeypatch):
    monkeypatch.setenv("PHOTOBOT_ACABAMENTOS", str(tmp_path))
    (tmp_path / "meu.json").write_text("[]")
    assert photocraft.acabamentos()["meu"] == tmp_path / "meu.json"


def test_aplicar_acabamento(cli_falso):
    out = photocraft.aplicar_acabamento(Image.new("RGB", (8, 6), (10, 20, 30)), "nitidez")
    assert out.size == (8, 6) and out.getpixel((0, 0)) == (245, 235, 225)
    args = json.loads(cli_falso.read_text())
    assert args[0] == "batch" and args[args.index("--actions") + 1].endswith("nitidez.json")


def test_acabamento_desconhecido(cli_falso):
    with pytest.raises(ValueError, match="nitidez"):
        photocraft.aplicar_acabamento(Image.new("RGB", (4, 4)), "nao_existe")


def test_erro_do_photocraft(cli_falso, tmp_path):
    acoes = tmp_path / "ruim.json"
    acoes.write_text('[{"command": "--falhar", "params": {}}]')
    with pytest.raises(RuntimeError, match="comando desconhecido"):
        photocraft.aplicar_acabamento(Image.new("RGB", (4, 4)), str(acoes))


def test_cli_com_acabamento(cli_falso, tmp_path):
    entrada, saida = tmp_path / "in", tmp_path / "out"
    entrada.mkdir()
    Image.new("RGB", (1080, 1350), (0, 0, 0)).save(entrada / "a.png")
    main([str(entrada), str(saida), "-p", "nenhum", "--acabamento-photocraft", "nitidez"])
    assert Image.open(saida / "a_nenhum_feed.jpg").getpixel((5, 5))[0] > 240
