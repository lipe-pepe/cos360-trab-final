"""Gráfico de Gantt de um resultado gravado em resultados/.

Uso:
    python gantt.py resultados/completo.json
    python gantt.py resultados/*.json

Gera resultados/<nome>.png (300 dpi), ao lado do JSON de resultado. Cada barra cobre o intervalo inclusivo [início, fim]
em dias úteis: uma tarefa do dia 16 ao dia 18 ocupa as colunas 16, 17 e 18
(de 15,5 a 18,5 no eixo).
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

COR_BARRA = "#D9D9D9"
TINTA = "#222222"
GRADE = "#E6E6E6"
EIXO = "#999999"

LARGURA_A4_TEXTO = 6.3  # pol. (~16 cm, largura útil de texto em A4)
ALTURA_POR_TAREFA = 0.22  # pol.
ALTURA_EXTRA = 1.1  # pol. (título, eixo x e legenda)
FONTE = 7.5
FOLGA_PX = 5  # folga mínima (px a 100 dpi) entre rótulo e borda da barra


def reais(valor: float) -> str:
    """Formata em reais no padrão brasileiro, escapando o $ do mathtext."""
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if texto.endswith(",00"):
        texto = texto[:-3]
    return f"R\\$ {texto}"


def passo_dos_dias(prazo: int) -> int:
    """Intervalo entre rótulos do eixo x, para não amontoar números."""
    for passo in (1, 2, 5, 10):
        if prazo / passo <= 30:
            return passo
    return 20


def desenhar(ax, solucao: dict, titulo: str) -> list:
    cronograma = solucao["cronograma"]
    prazo = solucao["prazo"]
    altura = 0.68

    rotulos = []
    for y, item in enumerate(cronograma):
        x0 = item["inicio"] - 0.5
        largura = item["fim"] - item["inicio"] + 1  # intervalo inclusivo
        ax.barh(y, largura, left=x0, height=altura, color=COR_BARRA,
                edgecolor="white", linewidth=0.8, zorder=2)
        txt = ax.text(x0 + largura / 2, y, item["colaborador"], ha="center",
                      va="center", fontsize=FONTE, color=TINTA, zorder=3)
        rotulos.append((txt, x0, largura, y))

    # Marca do prazo ótimo
    ax.axvline(prazo + 0.5, color=TINTA, linewidth=0.8,
               linestyle=(0, (3, 2)), zorder=1)

    ax.set_title(titulo, fontsize=9, loc="left", pad=4)
    tarefas = [item["tarefa"] for item in cronograma]
    ax.set_yticks(range(len(tarefas)), tarefas, fontsize=FONTE)
    ax.set_ylim(len(tarefas) - 0.4, -0.6)

    passo = passo_dos_dias(prazo)
    ax.set_xticks([1] + list(range(passo, prazo + 1, passo)) if passo > 1
                  else range(1, prazo + 1))
    ax.tick_params(axis="x", labelsize=FONTE)
    ax.tick_params(axis="both", length=0)
    # espaço à direita (~9% da largura) para rótulos fora da última barra
    ax.set_xlim(0.5, prazo + 0.5 + 0.1 * prazo)
    ax.set_xlabel("Dia útil", fontsize=FONTE + 0.5)

    # grade nas fronteiras entre dias: cada coluna é um dia útil
    ax.set_xticks([d + 0.5 for d in range(0, prazo + 1)], minor=True)
    ax.tick_params(axis="x", which="minor", length=0)
    if prazo <= 60:
        ax.grid(axis="x", which="minor", color=GRADE, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        ax.spines[lado].set_visible(False)
    ax.spines["bottom"].set_color(EIXO)
    return rotulos


def ajustar_rotulos(ax, rotulos, renderer) -> None:
    """Move para a direita da barra os rótulos que não cabem dentro dela."""
    for txt, x0, largura, y in rotulos:
        larg_txt = txt.get_window_extent(renderer).width
        larg_barra = (ax.transData.transform((x0 + largura, 0))[0]
                      - ax.transData.transform((x0, 0))[0])
        if larg_txt > larg_barra - 2 * FOLGA_PX:
            txt.set_position((x0 + largura + 0.15, y))
            txt.set_horizontalalignment("left")
            # contorno branco: grade e linha de prazo não cortam o rótulo
            txt.set_path_effects([pe.withStroke(linewidth=2.5, foreground="white")])


def gerar_gantt(solucao: dict, nome: str, pasta: Path) -> Path | None:
    """Gera o Gantt de uma solução. Devolve o PNG gravado, ou None se
    a solução não tiver cronograma (ex.: instância inviável)."""
    if "cronograma" not in solucao:
        return None

    titulo = (f"{nome} — prazo ótimo de {solucao['prazo']} dias úteis, "
              f"custo de {reais(solucao['custo_total'])} "
              f"(teto de {reais(solucao['orcamento'])})")

    plt.rcParams.update({"font.family": "DejaVu Sans"})
    n_tarefas = len(solucao["cronograma"])
    fig, ax = plt.subplots(
        figsize=(LARGURA_A4_TEXTO, ALTURA_EXTRA + ALTURA_POR_TAREFA * n_tarefas),
        layout="constrained",
    )
    rotulos = desenhar(ax, solucao, titulo)
    fig.legend(handles=[Line2D([], [], color=TINTA, linewidth=0.8,
                               linestyle=(0, (3, 2)), label="Prazo ótimo")],
               loc="outside lower center", fontsize=FONTE, frameon=False)

    # Fixa o layout antes de medir, para a escala do eixo x não mudar depois.
    fig.canvas.draw()
    fig.set_layout_engine("none")
    ajustar_rotulos(ax, rotulos, fig.canvas.get_renderer())

    pasta.mkdir(exist_ok=True)
    destino = pasta / f"{nome}.png"
    fig.savefig(destino, dpi=300)
    plt.close(fig)
    return destino


def main() -> None:
    parser = argparse.ArgumentParser(description="Gantt de um resultado do modelo.")
    parser.add_argument("arquivos", nargs="+", help="JSON(s) de resultado.")
    args = parser.parse_args()

    houve_erro = False
    for caminho in map(Path, args.arquivos):
        with open(caminho, encoding="utf-8") as f:
            solucao = json.load(f)
        destino = gerar_gantt(solucao, caminho.stem, caminho.parent)
        if destino is None:
            print(f"{caminho}: status {solucao.get('status')}, sem cronograma.",
                  file=sys.stderr)
            houve_erro = True
        else:
            print(f"{caminho}: Gantt salvo em {destino}")

    if houve_erro:
        sys.exit(1)


if __name__ == "__main__":
    main()
