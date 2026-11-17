"""Leitura e validação dos dados de entrada do problema de cronograma."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DadosProblema:
    tarefas: list[str]
    diaria: dict[str, float]               # colaborador -> custo por dia
    duracao: dict[str, dict[str, int]]     # tarefa -> colaborador -> dias
    precedencias: list[tuple[str, str]]    # (predecessora, sucessora)
    orcamento: float

    @property
    def colaboradores(self) -> list[str]:
        return list(self.diaria)

    @property
    def horizonte(self) -> int:
        """Soma das durações máximas de cada tarefa (limite superior do prazo)."""
        return sum(max(self.duracao[t].values()) for t in self.tarefas)


def carregar_dados(caminho: str | Path) -> DadosProblema:
    with open(caminho, encoding="utf-8") as f:
        bruto = json.load(f)

    dados = DadosProblema(
        tarefas=list(bruto["tarefas"]),
        diaria=dict(bruto["diaria"]),
        duracao={t: dict(d) for t, d in bruto["duracao"].items()},
        precedencias=[tuple(p) for p in bruto["precedencias"]],
        orcamento=bruto["orcamento"],
    )
    validar(dados)
    return dados


def validar(dados: DadosProblema) -> None:
    erros = []

    for tarefa in dados.tarefas:
        if tarefa not in dados.duracao:
            erros.append(f"Tarefa '{tarefa}' sem durações definidas.")
            continue
        for colaborador in dados.colaboradores:
            if colaborador not in dados.duracao[tarefa]:
                erros.append(f"Duração de '{tarefa}' para '{colaborador}' ausente.")

    for p in dados.precedencias:
        if len(p) != 2:
            erros.append(f"Precedência inválida: {p}.")
            continue
        for t in p:
            if t not in dados.tarefas:
                erros.append(f"Precedência {p} cita tarefa inexistente '{t}'.")

    if erros:
        raise ValueError("Dados de entrada inválidos:\n  " + "\n  ".join(erros))
