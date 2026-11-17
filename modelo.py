"""Construção do modelo de programação inteira (minimização do prazo do projeto)."""

from dataclasses import dataclass

import pulp

from dados import DadosProblema


@dataclass
class Modelo:
    problema: pulp.LpProblem
    x: dict                    # (tarefa, colaborador, dia) -> variável binária
    T: pulp.LpVariable         # prazo do projeto
    custo_total: pulp.LpAffineExpression
    opcoes_alocacao: list[tuple[str, str, int]]


def construir_modelo(dados: DadosProblema) -> Modelo:
    tarefas = dados.tarefas
    diaria = dados.diaria
    duracao = dados.duracao
    horizonte = dados.horizonte

    opcoes_alocacao = []
    for tarefa in tarefas:
        for colaborador in diaria:
            dias_necessarios = duracao[tarefa][colaborador]
            ultimo_inicio = horizonte - dias_necessarios + 1
            for dia in range(1, ultimo_inicio + 1):
                opcoes_alocacao.append((tarefa, colaborador, dia))

    modelo = pulp.LpProblem("Cronograma", pulp.LpMinimize)

    # x[tarefa, colaborador, dia] = 1 se a tarefa for atribuída ao colaborador
    # começando no dia; 0 caso contrário.
    x = {}
    for tarefa, colaborador, dia in opcoes_alocacao:
        x[tarefa, colaborador, dia] = modelo.add_variable(
            f"x_{tarefa}_{colaborador}_{dia}",
            cat=pulp.LpBinary,
        )

    # PRIMEIRA RESTRIÇÃO
    # Cada tarefa deve ser atribuída a exatamente um colaborador em um dia específico.
    for tarefa in tarefas:
        opcoes_tarefa = [x[opcao] for opcao in opcoes_alocacao if opcao[0] == tarefa]
        modelo += pulp.lpSum(opcoes_tarefa) == 1, f"Atribuicao_{tarefa}"

    # Expressões auxiliares de início e término
    inicio = {}
    fim = {}
    for tarefa in tarefas:
        inicio[tarefa] = pulp.lpSum(
            dia * x[i, colaborador, dia]
            for i, colaborador, dia in opcoes_alocacao
            if i == tarefa
        )
        fim[tarefa] = pulp.lpSum(
            (dia + duracao[i][colaborador] - 1) * x[i, colaborador, dia]
            for i, colaborador, dia in opcoes_alocacao
            if i == tarefa
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
    for pessoa in diaria:
        for dia_verificado in range(1, horizonte + 1):
            opcoes_que_ocupam_o_dia = []
            for tarefa, colaborador, dia_inicio in opcoes_alocacao:
                if colaborador != pessoa:
                    continue
                dia_fim = dia_inicio + duracao[tarefa][colaborador] - 1
                if dia_inicio <= dia_verificado <= dia_fim:
                    opcoes_que_ocupam_o_dia.append(x[tarefa, colaborador, dia_inicio])

            modelo += (
                pulp.lpSum(opcoes_que_ocupam_o_dia) <= 1,
                f"Capacidade_{pessoa}_{dia_verificado}",
            )

    # QUARTA RESTRIÇÃO
    # O custo total não pode exceder o orçamento.
    custo_total = pulp.lpSum(
        diaria[colaborador] * duracao[tarefa][colaborador] * x[tarefa, colaborador, dia]
        for tarefa, colaborador, dia in opcoes_alocacao
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
