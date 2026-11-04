"""Interface web simples (Gradio): envie a foto, escolha o estilo e baixe o resultado.

Rode com `photobot-app` (ou `python -m photobot.app`) e abra http://127.0.0.1:7860
"""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import gradio as gr
from PIL import Image

from . import ajustes as a
from . import photocraft
from .cli import Resultado, editar_camadas, salvar_camadas
from .formatos import FORMATOS, ajustar_formato
from .io import carregar, salvar
from .presets import PRESETS

NOMES_PRESET = {
    "Natural": "natural",
    "P&B dramático": "pb_dramatico",
    "Frio dessaturado": "frio_dessaturado",
    "Nenhum (só recorte)": "nenhum",
}
NOMES_FORMATO = {
    "Feed 4:5 (1080x1350)": "feed",
    "Quadrado (1080x1080)": "quadrado",
    "Paisagem (1080x566)": "paisagem",
    "Stories / Reels (1080x1920)": "stories",
}
NOMES_SR = {"Desligada": None, "Rápida (FSRCNN)": "fsrcnn", "Qualidade (EDSR, lenta)": "edsr"}
SEM_ACABAMENTO = "Nenhum"

assert set(NOMES_PRESET.values()) <= set(PRESETS) and set(NOMES_FORMATO.values()) <= set(FORMATOS)


def _processar(
    img: Image.Image,
    preset: str,
    formato: str,
    referencia: Image.Image | None,
    forca_ref: float,
    desfoque: float,
    escurecer: float,
    super_res: str,
    brilho: float,
    contraste: float,
    saturacao: float,
    temperatura: float,
    gerar_psd: bool = False,
    acabamento: str = SEM_ACABAMENTO,
) -> Resultado:
    res = editar_camadas(
        img.convert("RGB"),
        NOMES_FORMATO[formato],
        NOMES_PRESET[preset],
        referencia.convert("RGB") if referencia is not None else None,
        forca_ref,
        desfoque_fundo=desfoque,
        escurecer_fundo=escurecer,
        super_resolucao=NOMES_SR[super_res],
        calcular_mascara=gerar_psd,
    )
    out = res.editada
    # Ajustes finos por último, por cima do preset
    if brilho:
        out = a.brilho(out, brilho / 100)
    if contraste:
        out = a.contraste(out, 1 + contraste / 100)
    if saturacao:
        out = a.saturacao(out, 1 + saturacao / 100)
    if temperatura:
        out = a.temperatura(out, temperatura / 300)
    if acabamento and acabamento != SEM_ACABAMENTO:
        try:
            out = photocraft.aplicar_acabamento(out, acabamento)
        except (photocraft.PhotoCraftIndisponivel, RuntimeError, ValueError) as e:
            raise gr.Error(str(e)) from e
    res.editada = out
    return res


def _salvar(res: Resultado, caminho: Path, gerar_psd: bool) -> list[Path]:
    arquivos = [salvar(res.editada, caminho)]
    if gerar_psd:
        arquivos.append(salvar_camadas(res, caminho))
    return arquivos


def _quer_psd(opcoes) -> bool:
    """A caixa "Gerar PSD" é a 12ª opção (veja a lista `opcoes` em criar_app)."""
    return len(opcoes) > 11 and bool(opcoes[11])


def editar_uma(img, *opcoes):
    if img is None:
        raise gr.Error("Envie uma foto primeiro.")
    res = _processar(img, *opcoes)
    antes = ajustar_formato(img.convert("RGB"), NOMES_FORMATO[opcoes[1]])  # mesmo recorte, sem edição
    arquivos = _salvar(res, Path(tempfile.mkdtemp()) / "photobot", _quer_psd(opcoes))
    psd = str(arquivos[1]) if len(arquivos) > 1 else None
    return (antes, res.editada), str(arquivos[0]), psd


def editar_lote(arquivos, *opcoes, progress=gr.Progress()):
    if not arquivos:
        raise gr.Error("Envie pelo menos uma foto.")
    pasta = Path(tempfile.mkdtemp())
    gerados = []
    for i, caminho in enumerate(arquivos):
        progress(i / len(arquivos), desc=f"Editando {i + 1} de {len(arquivos)}")
        caminho = Path(caminho)
        res = _processar(carregar(caminho), *opcoes)
        gerados.extend(_salvar(res, pasta / f"{caminho.stem}_editada", _quer_psd(opcoes)))
    zip_path = pasta / "fotos_editadas.zip"
    with zipfile.ZipFile(zip_path, "w") as z:
        for g in gerados:
            z.write(g, g.name)
    return [str(g) for g in gerados if g.suffix == ".jpg"], str(zip_path)


def criar_app() -> gr.Blocks:
    with gr.Blocks(title="Photobot") as app:
        gr.Markdown("# Photobot\nEdição automática de fotos para o Instagram.")

        with gr.Row():
            with gr.Column(scale=1):
                preset = gr.Radio(list(NOMES_PRESET), value="P&B dramático", label="Estilo")
                formato = gr.Dropdown(list(NOMES_FORMATO), value="Feed 4:5 (1080x1350)", label="Formato")
                with gr.Accordion("Fundo (IA)", open=True):
                    desfoque = gr.Slider(0, 1, 0, step=0.05, label="Desfocar fundo")
                    escurecer = gr.Slider(0, 1, 0, step=0.05, label="Escurecer fundo")
                with gr.Accordion("Copiar estilo de outra foto", open=False):
                    referencia = gr.Image(type="pil", label="Foto de referência", height=200)
                    forca_ref = gr.Slider(0, 1, 0.8, step=0.05, label="Intensidade")
                with gr.Accordion("Ajustes finos", open=False):
                    brilho = gr.Slider(-30, 30, 0, step=1, label="Brilho")
                    contraste = gr.Slider(-50, 50, 0, step=1, label="Contraste")
                    saturacao = gr.Slider(-100, 50, 0, step=1, label="Saturação")
                    temperatura = gr.Slider(-30, 30, 0, step=1, label="Temperatura (frio ↔ quente)")
                super_res = gr.Radio(list(NOMES_SR), value="Desligada", label="Super-resolução para fotos pequenas (IA)")
                with gr.Accordion("PhotoCraft (opcional)", open=False):
                    gerar_psd = gr.Checkbox(
                        False,
                        label="Gerar também PSD em camadas",
                        info="Original, editada e atleta recortado. Abre no PhotoCraft, Photoshop, GIMP ou Photopea.",
                    )
                    tem_pc = photocraft.disponivel()
                    acabamento = gr.Dropdown(
                        [SEM_ACABAMENTO, *photocraft.acabamentos()] if tem_pc else [SEM_ACABAMENTO],
                        value=SEM_ACABAMENTO,
                        label="Acabamento do PhotoCraft",
                        info=None if tem_pc else "PhotoCraft não encontrado: instale o photocraft-cli para usar.",
                        interactive=tem_pc,
                    )

            opcoes = [preset, formato, referencia, forca_ref, desfoque, escurecer, super_res,
                      brilho, contraste, saturacao, temperatura, gerar_psd, acabamento]

            with gr.Column(scale=2):
                with gr.Tab("Uma foto"):
                    with gr.Row():
                        entrada = gr.Image(type="pil", label="Foto original", height=420)
                        comparacao = gr.ImageSlider(label="Antes / depois (arraste)", height=420, format="png")
                    botao = gr.Button("Editar", variant="primary")
                    download = gr.File(label="Baixar JPG em alta qualidade")
                    download_psd = gr.File(label="Baixar PSD em camadas")
                    botao.click(editar_uma, [entrada, *opcoes], [comparacao, download, download_psd])
                with gr.Tab("Várias fotos"):
                    arquivos = gr.File(file_count="multiple", file_types=["image"], type="filepath", label="Fotos")
                    botao_lote = gr.Button("Editar todas", variant="primary")
                    galeria = gr.Gallery(label="Resultado", columns=3, height=420, format="png")
                    zip_out = gr.File(label="Baixar todas (.zip)")
                    botao_lote.click(editar_lote, [arquivos, *opcoes], [galeria, zip_out])
    return app


def main() -> None:
    criar_app().launch()


if __name__ == "__main__":
    main()
