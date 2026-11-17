"""Leitura e validação dos dados de entrada do problema de cronograma."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DadosProblema:
    tarefas: list[str]
    diaria: dict[str, float]               # colaborador -> custo por dia
    # tarefa -> colaborador -> dias. Só aparecem os colaboradores elegíveis
    # para a tarefa: quem não está cadastrado ali não pode executá-la.
    duracao: dict[str, dict[str, int]]
    precedencias: list[tuple[str, str]]    # (predecessora, sucessora)
    orcamento: float

    @property
    def colaboradores(self) -> list[str]:
        return list(self.diaria)

    def elegiveis(self, tarefa: str) -> list[str]:
        """Colaboradores com duração cadastrada para a tarefa (na ordem de `diaria`)."""
        cadastrados = self.duracao.get(tarefa, {})
        return [c for c in self.colaboradores if c in cadastrados]

    @property
    def horizonte(self) -> int:
        """Soma, por tarefa, da maior duração entre seus elegíveis (limite superior do prazo)."""
        return sum(
            max(self.duracao[t][c] for c in self.elegiveis(t))
            for t in self.tarefas
        )


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

    for tarefa, por_colaborador in dados.duracao.items():
        if tarefa not in dados.tarefas:
            erros.append(f"Durações cadastradas para tarefa inexistente '{tarefa}'.")
        for colaborador, dias in por_colaborador.items():
            if colaborador not in dados.diaria:
                erros.append(
                    f"Duração de '{tarefa}' cadastrada para '{colaborador}', "
                    f"que não está em 'diaria'."
                )
            if not isinstance(dias, int) or isinstance(dias, bool) or dias < 1:
                erros.append(
                    f"Duração de '{tarefa}' para '{colaborador}' deve ser um "
                    f"inteiro positivo (recebido: {dias!r})."
                )

    for tarefa in dados.tarefas:
        if not dados.elegiveis(tarefa):
            erros.append(
                f"Tarefa '{tarefa}' não tem nenhum colaborador elegível "
                f"(nenhuma duração cadastrada para membros da equipe)."
            )

    for p in dados.precedencias:
        if len(p) != 2:
            erros.append(f"Precedência inválida: {p}.")
            continue
        for t in p:
            if t not in dados.tarefas:
                erros.append(f"Precedência {p} cita tarefa inexistente '{t}'.")

    if erros:
        raise ValueError("Dados de entrada inválidos:\n  " + "\n  ".join(erros))
