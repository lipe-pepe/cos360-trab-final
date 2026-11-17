"""Resolve o problema de cronograma para um arquivo de dados.

Uso:
    python main.py dados/reduzido.json
    python main.py dados/reduzido.json dados/outro.json   # várias instâncias
    python main.py dados/*.json --silent              # sem log do CBC

O resultado de cada instância é gravado em resultados/<nome do arquivo de entrada>,
junto com o gráfico de Gantt (resultados/<nome>.png).
"""

import argparse
import json
import sys
from pathlib import Path

import pulp

from dados import DadosProblema, carregar_dados
from gantt import gerar_gantt
from modelo import Modelo, construir_modelo

PASTA_RESULTADOS = Path(__file__).resolve().parent / "resultados"


def extrair_solucao(dados: DadosProblema, m: Modelo, resultado) -> dict:
    """Resume a solução em um dicionário (serializável em JSON)."""
    solucao = {"status": resultado.status_str, "orcamento": dados.orcamento}

    if resultado.status != pulp.LpSolveStatus.Optimal:
        return solucao

    cronograma = []
    for tarefa, colaborador, dia in m.opcoes_alocacao:
        if pulp.value(m.x[tarefa, colaborador, dia]) > 0.5:
            dias_necessarios = dados.duracao[tarefa][colaborador]
            cronograma.append({
                "tarefa": tarefa,
                "colaborador": colaborador,
                "inicio": dia,
                "fim": dia + dias_necessarios - 1,
                "custo": dados.diaria[colaborador] * dias_necessarios,
            })
    cronograma.sort(key=lambda item: dados.tarefas.index(item["tarefa"]))

    solucao["prazo"] = round(pulp.value(m.T))
    solucao["custo_total"] = pulp.value(m.custo_total)
    solucao["cronograma"] = cronograma
    return solucao


def imprimir_solucao(solucao: dict) -> None:
    print("Status:", solucao["status"])

    if "cronograma" not in solucao:
        return

    print(f"Prazo ótimo: {solucao['prazo']} dias úteis")
    print("\nCronograma encontrado:")
    for item in solucao["cronograma"]:
        print(
            f"Tarefa {item['tarefa']}: {item['colaborador']}, "
            f"início no dia {item['inicio']}, término no dia {item['fim']}, "
            f"custo de R$ {item['custo']}"
        )

    print(f"\nCusto total: R$ {solucao['custo_total']:.2f}")


def gravar_solucao(caminho_entrada: str, solucao: dict) -> Path:
    """Grava a solução em resultados/ com o mesmo nome do arquivo de entrada."""
    PASTA_RESULTADOS.mkdir(exist_ok=True)
    destino = PASTA_RESULTADOS / Path(caminho_entrada).name
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(solucao, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return destino


def main() -> None:
    parser = argparse.ArgumentParser(description="Solver do problema de cronograma.")
    parser.add_argument("arquivos", nargs="+", help="Arquivo(s) JSON com os dados de entrada.")
    parser.add_argument("--silent", action="store_true", help="Oculta o log do solver CBC.")
    args = parser.parse_args()

    houve_erro = False
    for caminho in args.arquivos:
        print(f"\n===== {caminho} =====")
        try:
            dados = carregar_dados(caminho)
            m = construir_modelo(dados)
        except ValueError as erro:
            print(erro, file=sys.stderr)
            houve_erro = True
            continue
        resultado = m.problema.solve(pulp.COIN_CMD(msg=not args.silent))
        solucao = extrair_solucao(dados, m, resultado)
        imprimir_solucao(solucao)
        destino = gravar_solucao(caminho, solucao)
        print(f"\nResultado gravado em {destino}")
        grafico = gerar_gantt(solucao, destino.stem, destino.parent)
        if grafico:
            print(f"Gantt salvo em {grafico}")

    if houve_erro:
        sys.exit(1)


if __name__ == "__main__":
    main()
