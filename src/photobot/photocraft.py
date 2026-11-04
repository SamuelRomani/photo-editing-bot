"""Integração opcional com o PhotoCraft (https://github.com/storytold/photocraft).

O PhotoCraft é um editor de imagens open source (MIT/Apache-2.0) que roda local. O
`photocraft-cli` dele aplica qualquer comando do editor (curvas, níveis, nitidez,
LUTs, blur de lente...) sem abrir a janela. Aqui ele vira um "acabamento" aplicado
depois da edição do bot.

Nada disso é obrigatório: se o PhotoCraft não estiver instalado o bot funciona igual,
só sem essa opção.

Como o bot encontra o PhotoCraft, em ordem:
1. variável de ambiente `PHOTOCRAFT_CLI` (caminho do `photocraft-cli` ou do AppImage);
2. `photocraft-cli` no PATH.

Os acabamentos são listas de ações do PhotoCraft em JSON (o mesmo formato do
`photocraft-cli batch --actions`). Os que vêm com o bot ficam em
`photobot/acabamentos/`; para criar outros, salve um `.json` em
`~/.config/photobot/acabamentos/` (ou na pasta de `PHOTOBOT_ACABAMENTOS`).
Para ver os comandos disponíveis: `photocraft-cli commands`.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

PASTA_PADRAO = Path(__file__).parent / "acabamentos"
PASTA_USUARIO = Path.home() / ".config" / "photobot" / "acabamentos"


class PhotoCraftIndisponivel(RuntimeError):
    pass


def comando_cli() -> list[str] | None:
    """O comando para chamar o `photocraft-cli`, ou None se não estiver instalado."""
    env = os.environ.get("PHOTOCRAFT_CLI", "").strip()
    if env:
        if os.name == "nt":  # shlex não entende caminhos do Windows com barra invertida
            partes = [p.strip('"') for p in shlex.split(env, posix=False)]
        else:
            partes = shlex.split(env)
        # O AppImage do Linux abre a janela, a menos que receba --cli
        if partes[0].lower().endswith(".appimage") and "--cli" not in partes:
            partes.append("--cli")
        return partes
    achado = shutil.which("photocraft-cli")
    return [achado] if achado else None


def disponivel() -> bool:
    return comando_cli() is not None


def _pastas() -> list[Path]:
    extra = os.environ.get("PHOTOBOT_ACABAMENTOS")
    return [PASTA_PADRAO, PASTA_USUARIO, *([Path(extra)] if extra else [])]


def acabamentos() -> dict[str, Path]:
    """Nome -> arquivo de ações. Um arquivo do usuário com o mesmo nome substitui o padrão."""
    encontrados: dict[str, Path] = {}
    for pasta in _pastas():
        if pasta.is_dir():
            for arq in sorted(pasta.glob("*.json")):
                encontrados[arq.stem] = arq
    return encontrados


def aplicar_acabamento(img: Image.Image, nome: str, timeout: float = 300) -> Image.Image:
    """Roda o acabamento `nome` (ou um caminho para um .json de ações) no PhotoCraft."""
    cmd = comando_cli()
    if cmd is None:
        raise PhotoCraftIndisponivel(
            "PhotoCraft não encontrado. Instale pelo site getartcraft.com/apps/photocraft "
            "e coloque o photocraft-cli no PATH, ou aponte a variável PHOTOCRAFT_CLI para ele."
        )
    acoes = Path(nome)
    if not acoes.is_file():
        todos = acabamentos()
        if nome not in todos:
            raise ValueError(f"Acabamento desconhecido: {nome!r}. Disponíveis: {sorted(todos)}")
        acoes = todos[nome]

    with tempfile.TemporaryDirectory(prefix="photobot-pc-") as tmp:
        entrada, saida = Path(tmp) / "entrada", Path(tmp) / "saida"
        entrada.mkdir()
        saida.mkdir()
        # PNG para não perder qualidade na ida; o bot recomprime no final
        img.convert("RGB").save(entrada / "foto.png")
        args = [*cmd, "batch", "--actions", str(acoes), "--in", str(entrada), "--out", str(saida), "--format", "png"]
        try:
            proc = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        except OSError as e:
            raise PhotoCraftIndisponivel(f"Não consegui executar o PhotoCraft ({cmd[0]}): {e}") from e
        if proc.returncode != 0:
            detalhe = (proc.stderr or proc.stdout).strip()[-800:]
            raise RuntimeError(f"O PhotoCraft falhou (código {proc.returncode}): {detalhe}")
        gerados = sorted(saida.rglob("*.png"))
        if not gerados:
            raise RuntimeError(f"O PhotoCraft não gerou nenhuma imagem. Saída: {proc.stdout.strip()[-800:]}")
        with Image.open(gerados[0]) as out:
            return out.convert("RGB")
