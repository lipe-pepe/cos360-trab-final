"""Construção do modelo de programação inteira (minimização do prazo do projeto)."""

from collections import defaultdict
from dataclasses import dataclass

import pulp

from dados import DadosProblema, validar


@dataclass
class Modelo:
    problema: pulp.LpProblem
    x: dict                    # (tarefa, colaborador, dia) -> variável binária
    T: pulp.LpVariable         # prazo do projeto
    custo_total: pulp.LpAffineExpression
    opcoes_alocacao: list[tuple[str, str, int]]


def gerar_opcoes(dados: DadosProblema) -> list[tuple[str, str, int]]:
    """Opções (tarefa, colaborador, dia de início) válidas.

    Só considera pares tarefa-colaborador com duração cadastrada e dias de
    início em que a tarefa inteira cabe no horizonte.
    """
    horizonte = dados.horizonte
    opcoes = []
    for tarefa in dados.tarefas:
        for colaborador in dados.elegiveis(tarefa):
            ultimo_inicio = horizonte - dados.duracao[tarefa][colaborador] + 1
            for dia in range(1, ultimo_inicio + 1):
                opcoes.append((tarefa, colaborador, dia))
    return opcoes


def construir_modelo(dados: DadosProblema) -> Modelo:
    # Garante mensagens claras (ex.: tarefa sem elegíveis) antes de montar o modelo.
    validar(dados)

    tarefas = dados.tarefas
    diaria = dados.diaria
    duracao = dados.duracao
    horizonte = dados.horizonte

    opcoes_alocacao = gerar_opcoes(dados)

    # Índices das opções válidas, usados por todas as restrições abaixo.
    opcoes_por_tarefa = defaultdict(list)
    opcoes_por_colaborador = defaultdict(list)
    for opcao in opcoes_alocacao:
        tarefa, colaborador, _ = opcao
        opcoes_por_tarefa[tarefa].append(opcao)
        opcoes_por_colaborador[colaborador].append(opcao)

    def dias_de(opcao):
        tarefa, colaborador, _ = opcao
        return duracao[tarefa][colaborador]

    modelo = pulp.LpProblem("Cronograma", pulp.LpMinimize)

    # x[tarefa, colaborador, dia] = 1 se a tarefa for atribuída ao colaborador
    # começando no dia; 0 caso contrário. Criada só para opções válidas.
    x = {}
    for tarefa, colaborador, dia in opcoes_alocacao:
        x[tarefa, colaborador, dia] = modelo.add_variable(
            f"x_{tarefa}_{colaborador}_{dia}",
            cat=pulp.LpBinary,
        )

    # PRIMEIRA RESTRIÇÃO
    # Cada tarefa deve ser atribuída a exatamente um colaborador elegível em um dia.
    for tarefa in tarefas:
        modelo += (
            pulp.lpSum(x[o] for o in opcoes_por_tarefa[tarefa]) == 1,
            f"Atribuicao_{tarefa}",
        )

    # Expressões auxiliares de início e término
    inicio = {}
    fim = {}
    for tarefa in tarefas:
        inicio[tarefa] = pulp.lpSum(o[2] * x[o] for o in opcoes_por_tarefa[tarefa])
        fim[tarefa] = pulp.lpSum(
            (o[2] + dias_de(o) - 1) * x[o] for o in opcoes_por_tarefa[tarefa]
        )

    # SEGUNDA RESTRIÇÃO
    # Tarefas predecessoras devem terminar antes do início das sucessoras.
    for predecessora, sucessora in dados.precedencias:
        modelo += (
            inicio[sucessora] >= fim[predecessora] + 1,
            f"Precedencia_{predecessora}_{sucessora}",
        )

    # TERCEIRA RESTRIÇÃO
    # Cada colaborador só pode trabalhar em uma tarefa por dia.
    # Colaboradores sem nenhuma opção (ou dias sem opção) não geram restrição.
    for pessoa in diaria:
        for dia_verificado in range(1, horizonte + 1):
            ocupam_o_dia = [
                x[o] for o in opcoes_por_colaborador[pessoa]
                if o[2] <= dia_verificado <= o[2] + dias_de(o) - 1
            ]
            if ocupam_o_dia:
                modelo += (
                    pulp.lpSum(ocupam_o_dia) <= 1,
                    f"Capacidade_{pessoa}_{dia_verificado}",
                )

    # QUARTA RESTRIÇÃO
    # O custo total não pode exceder o orçamento.
    custo_total = pulp.lpSum(
        diaria[o[1]] * dias_de(o) * x[o] for o in opcoes_alocacao
    )
    modelo += (custo_total <= dados.orcamento, "Orcamento")

    # Variável de prazo do projeto
    T = modelo.add_variable("T", lowBound=1, upBound=horizonte)

    # QUINTA RESTRIÇÃO
    # O prazo do projeto deve ser maior ou igual ao término de todas as tarefas.
    for tarefa in tarefas:
        modelo += (T >= fim[tarefa], f"Conclusao_{tarefa}")

    # FUNÇÃO OBJETIVO
    # Minimizar o prazo do projeto.
    modelo += T

    return Modelo(modelo, x, T, custo_total, opcoes_alocacao)
