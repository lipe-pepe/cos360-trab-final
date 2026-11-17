"""Resolve o problema de cronograma para um arquivo de dados.

Uso:
    python main.py dados/reduzido.json
    python main.py dados/reduzido.json dados/outro.json   # várias instâncias
    python main.py dados/*.json --silent              # sem log do CBC
"""

import argparse
import sys

import pulp

from dados import DadosProblema, carregar_dados
from modelo import Modelo, construir_modelo


def imprimir_solucao(dados: DadosProblema, m: Modelo, resultado) -> None:
    print("Status:", resultado.status_str)

    if resultado.status != pulp.LpSolveStatus.Optimal:
        return

    print(f"Prazo ótimo: {pulp.value(m.T):g} dias úteis")
    print("\nCronograma encontrado:")

    for tarefa, colaborador, dia in m.opcoes_alocacao:
        if pulp.value(m.x[tarefa, colaborador, dia]) > 0.5:
            dias_necessarios = dados.duracao[tarefa][colaborador]
            ultimo_dia = dia + dias_necessarios - 1
            custo = dados.diaria[colaborador] * dias_necessarios
            print(
                f"Tarefa {tarefa}: {colaborador}, "
                f"início no dia {dia}, término no dia {ultimo_dia}, "
                f"custo de R$ {custo}"
            )

    print(f"\nCusto total: R$ {pulp.value(m.custo_total):.2f}")


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
        imprimir_solucao(dados, m, resultado)

    if houve_erro:
        sys.exit(1)


if __name__ == "__main__":
    main()
