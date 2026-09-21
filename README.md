# Load & Resize Image by Megapixel

Node do ComfyUI que carrega uma imagem (com seletor, upload e preview, igual ao **Load Image** nativo) e já
redimensiona para um alvo em megapixels, com largura e altura divisíveis por N.

Exemplo: `1.0 MP` divisível por `32` → uma foto 1920×1080 vira 1344×736; uma 960×1280 vira 864×1152.

## Nodes

- **Load & Resize Image by Megapixel** (`image`): Load Image + resize.
- **Resize Image by Megapixel** (`image/transform`): mesmo resize para um `IMAGE` vindo de outro node
  (aceita `MASK` opcional).

## Widgets

| Widget | Efeito |
|---|---|
| `image` | Imagem da pasta `input` (upload e preview como no Load Image) |
| `resize` | Desligado: devolve a imagem no tamanho original |
| `megapixels` | Alvo em MP (padrão `1.0`, ~1024×1024) |
| `divisible_by` | 8, 16, 32, 64, 112 ou 128 (padrão `32`) |
| `upscale_method` | lanczos, bicubic, bilinear, area, nearest-exact |
| `rounding` | `nearest` fica o mais perto do alvo; `floor` nunca passa dele; `ceil` nunca fica abaixo |
| `fit_mode` | `crop` mantém a proporção cortando do centro os pixels perdidos no arredondamento; `stretch` distorce levemente |

## Saídas

`IMAGE`, `width`, `height`, `MASK` (alpha da imagem, redimensionado junto).

## Instalação

```sh
cd ComfyUI/custom_nodes
git clone https://github.com/gabxav/ComfyUI-Load-Resize-Image-by-Megapixel.git
```

Reinicie o ComfyUI. Sem dependências além das do próprio ComfyUI.
