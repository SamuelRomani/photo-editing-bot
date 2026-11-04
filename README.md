# photo-editing-bot

Edição automática de fotos para posts no Instagram, com visual editorial esportivo
(preto e branco dramático, tons frios dessaturados, fundo desfocado). Usa só ferramentas
gratuitas: Pillow/OpenCV para a edição clássica e modelos open source para a parte de IA.

## Roteiro

- [x] **1. Base:** estrutura do projeto, leitura/gravação de fotos, recorte nos formatos do Instagram e linha de comando
- [ ] **2. Presets:** brilho, contraste, balanço de branco, "P&B dramático", "Frio dessaturado", vinheta, granulação e cópia de estilo a partir de uma foto de referência
- [ ] **3. IA gratuita:** recorte do atleta com rembg para desfocar só o fundo; aumento de resolução com Real-ESRGAN
- [ ] **4. Interface:** app Gradio com antes/depois e download

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

## Uso

Coloque as fotos em `entrada/` e rode:

```bash
photobot                    # recorta tudo para o feed (1080x1350) e salva em saida/
photobot -f stories         # 1080x1920
photobot minhas_fotos/ prontas/ -f quadrado
```

Formatos disponíveis:

| Formato    | Tamanho     | Uso                         |
|------------|-------------|-----------------------------|
| `feed`     | 1080x1350   | Retrato 4:5, padrão do feed |
| `quadrado` | 1080x1080   | 1:1                         |
| `paisagem` | 1080x566    | 1.91:1                      |
| `stories`  | 1080x1920   | Stories e Reels             |

## Pastas

- `entrada/`: fotos originais
- `saida/`: fotos editadas
- `referencias/`: fotos de exemplo do estilo desejado (usadas na cópia de estilo)

O conteúdo dessas pastas não vai para o Git, para não publicar fotos de terceiros.

## Testes

```bash
pip install -r requirements-dev.txt
pytest
```
