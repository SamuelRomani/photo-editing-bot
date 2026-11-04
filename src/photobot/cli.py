"""Linha de comando: processa uma pasta de fotos."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from .estilo import transferir_estilo
from .formatos import FORMATOS, ajustar_formato
from .io import carregar, listar_imagens, salvar
from .presets import PRESETS, aplicar_preset
from .psd import Camada, salvar_psd


@dataclass
class Resultado:
    """A foto editada e o que é preciso para montar o PSD em camadas."""

    original: Image.Image  # só recortada no formato, sem edição
    editada: Image.Image
    mascara: np.ndarray | None = None  # atleta (1) / fundo (0), se a IA foi usada


def editar_camadas(
    img: Image.Image,
    formato: str = "feed",
    preset: str = "natural",
    referencia: Image.Image | None = None,
    forca_referencia: float = 1.0,
    desfoque_fundo: float = 0.0,
    escurecer_fundo: float = 0.0,
    super_resolucao: str | None = None,
    calcular_mascara: bool = False,
) -> Resultado:
    """Pipeline completo.

    1. Aumenta a resolução, se pedido e se a foto for pequena (IA)
    2. Recorta no formato do Instagram
    3. Copia o estilo da referência (opcional)
    4. Desfoca/escurece o fundo (IA, opcional)
    5. Aplica o preset (vinheta e granulação ficam por último, como num filme)

    Com `calcular_mascara`, recorta o atleta mesmo sem mexer no fundo (para o PSD),
    se as dependências de IA estiverem instaladas.
    """
    if super_resolucao:
        from .ia import garantir_resolucao

        img = garantir_resolucao(img, FORMATOS[formato][0], super_resolucao)
    img = ajustar_formato(img, formato)
    original = img
    mascara = None
    if desfoque_fundo > 0 or escurecer_fundo > 0 or calcular_mascara:
        from .ia import DependenciaFaltando, mascara_pessoa

        try:
            mascara = mascara_pessoa(img)
        except (DependenciaFaltando, ImportError):
            if desfoque_fundo > 0 or escurecer_fundo > 0:
                raise
    if referencia is not None:
        img = transferir_estilo(img, referencia, forca_referencia)
    if desfoque_fundo > 0 or escurecer_fundo > 0:
        from .ia import desfocar_fundo

        img = desfocar_fundo(img, desfoque_fundo, escurecer_fundo, mascara=mascara)
    return Resultado(original, aplicar_preset(img, preset), mascara)


def editar(img: Image.Image, *args, **kwargs) -> Image.Image:
    """Como `editar_camadas`, mas devolve só a foto editada."""
    return editar_camadas(img, *args, **kwargs).editada


def salvar_camadas(res: Resultado, caminho: Path) -> Path:
    """PSD com a original embaixo, a editada por cima e o atleta recortado (oculto)."""
    camadas = [Camada("Original", res.original), Camada("Editada", res.editada)]
    if res.mascara is not None:
        camadas.append(Camada("Atleta recortado", res.editada, res.mascara, visivel=False))
    return salvar_psd(camadas, caminho, composta=res.editada)


def processar_pasta(
    entrada: Path,
    saida: Path,
    formato: str = "feed",
    preset: str = "natural",
    referencia: Path | None = None,
    forca_referencia: float = 1.0,
    psd: bool = False,
    acabamento: str | None = None,
    **opcoes_ia,
) -> list[Path]:
    """Edita cada foto da pasta. Com `psd`, salva também um PSD em camadas;
    com `acabamento`, passa a foto pelo PhotoCraft no final."""
    ref = carregar(referencia) if referencia else None
    gerados = []
    for caminho in listar_imagens(entrada):
        res = editar_camadas(
            carregar(caminho), formato, preset, ref, forca_referencia, calcular_mascara=psd, **opcoes_ia
        )
        if acabamento:
            from .photocraft import aplicar_acabamento

            res.editada = aplicar_acabamento(res.editada, acabamento)
        nome = saida / f"{caminho.stem}_{preset}_{formato}"
        gerados.append(salvar(res.editada, nome))
        if psd:
            gerados.append(salvar_camadas(res, nome))
    return gerados


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="photobot", description=__doc__)
    parser.add_argument("entrada", type=Path, nargs="?", default=Path("entrada"), help="pasta com as fotos originais")
    parser.add_argument("saida", type=Path, nargs="?", default=Path("saida"), help="pasta onde salvar as fotos editadas")
    parser.add_argument("-f", "--formato", choices=list(FORMATOS), default="feed")
    parser.add_argument("-p", "--preset", choices=list(PRESETS), default="natural")
    parser.add_argument("-r", "--referencia", type=Path, help="foto cujo estilo de cor/tom será copiado")
    parser.add_argument("--forca-referencia", type=float, default=0.8, help="0 a 1 (padrão 0.8)")
    ia = parser.add_argument_group("IA (requer: pip install -r requirements-ia.txt)")
    ia.add_argument("--desfocar-fundo", type=float, default=0.0, metavar="0-1", help="desfoca o fundo atrás do atleta")
    ia.add_argument("--escurecer-fundo", type=float, default=0.0, metavar="0-1", help="escurece o fundo atrás do atleta")
    ia.add_argument(
        "--super-resolucao", choices=["fsrcnn", "espcn", "edsr"], help="aumenta a resolução de fotos pequenas"
    )
    pc = parser.add_argument_group("PhotoCraft (opcional, veja o README)")
    pc.add_argument("--psd", action="store_true", help="salva também um PSD em camadas (abre no PhotoCraft)")
    pc.add_argument(
        "--acabamento-photocraft",
        metavar="NOME",
        help="aplica um acabamento do PhotoCraft no final (nome ou caminho de um .json de ações)",
    )
    pc.add_argument("--listar-acabamentos", action="store_true", help="mostra os acabamentos e sai")
    args = parser.parse_args(argv)

    if args.listar_acabamentos:
        from .photocraft import acabamentos, comando_cli

        cli = comando_cli()
        print(f"PhotoCraft: {' '.join(cli) if cli else 'não encontrado'}")
        for nome, arq in acabamentos().items():
            print(f"  {nome}  ({arq})")
        return
    if args.acabamento_photocraft:
        from .photocraft import disponivel

        if not disponivel():
            parser.error("PhotoCraft não encontrado: instale o photocraft-cli ou defina PHOTOCRAFT_CLI")

    gerados = processar_pasta(
        args.entrada,
        args.saida,
        args.formato,
        args.preset,
        args.referencia,
        args.forca_referencia,
        psd=args.psd,
        acabamento=args.acabamento_photocraft,
        desfoque_fundo=args.desfocar_fundo,
        escurecer_fundo=args.escurecer_fundo,
        super_resolucao=args.super_resolucao,
    )
    for g in gerados:
        print(f"✔ {g}")
    print(f"{sum(g.suffix == '.jpg' for g in gerados)} foto(s) processada(s).")


if __name__ == "__main__":
    main()
