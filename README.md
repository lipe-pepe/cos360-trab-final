# Cronograma de Projeto com Programação Inteira

Trabalho final da disciplina **COS360 – Otimização**, da **Universidade Federal do Rio de Janeiro (UFRJ)**.

O programa usa programação linear inteira para alocar as tarefas de um projeto entre colaboradores. Cada tarefa tem seu próprio conjunto de colaboradores habilitados a executá-la. O objetivo é **minimizar o prazo total do projeto**, respeitando:

- as precedências entre tarefas;
- a disponibilidade de cada colaborador (uma tarefa por vez);
- o orçamento disponível.

O modelo é escrito em Python com a biblioteca [PuLP](https://coin-or.github.io/pulp/) e resolvido pelo solver **CBC** (COIN-OR Branch and Cut).

## O problema

São dados:

| Símbolo | Significado |
|---|---|
| $I$ | conjunto de tarefas |
| $K$ | conjunto de colaboradores |
| $c_k$ | diária do colaborador $k$ |
| $E_i \subseteq K$ | colaboradores elegíveis para a tarefa $i$ (os que têm duração cadastrada) |
| $d_{ik}$ | duração (em dias) da tarefa $i$ quando executada por $k \in E_i$ |
| $P$ | pares $(i, j)$: a tarefa $i$ precisa terminar antes de $j$ começar |
| $B$ | orçamento total |
| $H$ | horizonte de planejamento: $H = \sum_{i} \max_{k \in E_i} d_{ik}$ |

### Variáveis de decisão

- $x_{ikt} \in \{0, 1\}$: vale 1 se a tarefa $i$ for feita pelo colaborador $k$ começando no dia $t$. Só existe para $k \in E_i$ e $t = 1, \dots, H - d_{ik} + 1$. Pares tarefa-colaborador não elegíveis não geram variável.

No que segue, toda soma em $k$ percorre apenas $E_i$.
- $T$: prazo do projeto (último dia de trabalho).

Expressões auxiliares:

$$\text{início}_i = \sum_{k,t} t \, x_{ikt}, \qquad \text{fim}_i = \sum_{k,t} (t + d_{ik} - 1) \, x_{ikt}$$

### Formulação

$$\min \; T$$

sujeito a:

1. **Atribuição**: cada tarefa é feita exatamente uma vez, por um único colaborador, com um único dia de início.
   $$\sum_{k,t} x_{ikt} = 1 \quad \forall i \in I$$
2. **Precedência**: a sucessora só começa depois que a predecessora termina.
   $$\text{início}_j \ge \text{fim}_i + 1 \quad \forall (i, j) \in P$$
3. **Capacidade**: em cada dia, cada colaborador trabalha em no máximo uma tarefa.
   $$\sum_{i} \sum_{t \,:\, t \le \tau \le t + d_{ik} - 1} x_{ikt} \le 1 \quad \forall k \in K,\ \tau = 1, \dots, H$$
4. **Orçamento**:
   $$\sum_{i,k,t} c_k \, d_{ik} \, x_{ikt} \le B$$
5. **Prazo**: o projeto só termina quando todas as tarefas terminam.
   $$T \ge \text{fim}_i \quad \forall i \in I$$

## Estrutura do projeto

```
.
├── dados/
│   ├── reduzido.json                # instância de exemplo (5 tarefas, 3 colaboradores)
│   └── elegibilidade_restrita.json  # exemplo com colaboradores elegíveis por tarefa
├── dados.py            # leitura e validação dos dados de entrada
├── modelo.py           # construção do modelo de programação inteira
├── resultados/         # soluções gravadas pelo main.py (criada na primeira execução)
├── main.py             # interface de linha de comando: resolve, mostra e grava o cronograma
├── gantt.py            # gráfico de Gantt a partir de um JSON de resultado
└── requirements.txt    # dependências
```

## Instalação

É preciso ter **Python 3.12 ou mais recente**.

```bash
python3 -m venv .venv
source .venv/bin/activate          # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

O extra `pulp[cbc]` instala o executável do CBC junto com o PuLP. Não é preciso instalar nenhum solver separadamente.

## Como executar

Com o ambiente virtual ativado:

```bash
# Resolve uma instância
python main.py dados/reduzido.json

# Resolve várias instâncias de uma vez
python main.py dados/*.json

# Oculta o log do solver CBC
python main.py dados/reduzido.json --silent
```

Exemplo de saída para `dados/reduzido.json`:

```
===== dados/reduzido.json =====
Status: Optimal
Prazo ótimo: 3 dias úteis

Cronograma encontrado:
Tarefa A: Ana, início no dia 2, término no dia 2, custo de R$ 350
Tarefa B: Caio, início no dia 1, término no dia 2, custo de R$ 400
Tarefa C: Ana, início no dia 3, término no dia 3, custo de R$ 350
Tarefa D: Bruno, início no dia 1, término no dia 2, custo de R$ 600
Tarefa E: Bruno, início no dia 3, término no dia 3, custo de R$ 300

Custo total: R$ 2000.00

Resultado gravado em .../resultados/reduzido.json
```

Se não houver solução que caiba no orçamento, o programa mostra o status `Infeasible` e não imprime cronograma.

### Arquivos de resultado

O resultado de cada instância é gravado em `resultados/`, com o mesmo nome do arquivo de entrada. Por exemplo, `dados/reduzido.json` gera `resultados/reduzido.json`. Se o arquivo já existir, é sobrescrito.

```json
{
  "status": "Optimal",
  "orcamento": 2500,
  "prazo": 3,
  "custo_total": 2000.0,
  "cronograma": [
    { "tarefa": "A", "colaborador": "Ana", "inicio": 2, "fim": 2, "custo": 350 },
    ...
  ]
}
```

Quando não há solução ótima, o arquivo traz apenas `status` e `orcamento`.

### Gráfico de Gantt

Junto com o JSON, o `main.py` gera o gráfico de Gantt do cronograma em `resultados/<nome>.png` (300 dpi). Cada barra é uma tarefa, rotulada com o colaborador que a executa. A linha tracejada marca o prazo ótimo. Instâncias sem solução não geram gráfico.

Para refazer o gráfico a partir de um resultado já gravado, sem rodar o solver:

```bash
python gantt.py resultados/completo.json
python gantt.py resultados/*.json
```

## Criando novas instâncias

Cada instância é um arquivo JSON na pasta `dados/`. Para criar uma nova, copie `dados/reduzido.json` e mude os valores:

```json
{
  "tarefas": ["A", "B", "C"],
  "diaria": { "Ana": 350, "Bruno": 300 },
  "duracao": {
    "A": { "Ana": 1, "Bruno": 2 },
    "B": { "Bruno": 1 },
    "C": { "Ana": 1, "Bruno": 1 }
  },
  "precedencias": [["A", "C"], ["B", "C"]],
  "orcamento": 2000
}
```

| Campo | Descrição |
|---|---|
| `tarefas` | lista com os nomes das tarefas |
| `diaria` | custo diário de cada colaborador |
| `duracao` | para cada tarefa, quantos dias (inteiro positivo) cada colaborador **elegível** leva para concluí-la |
| `precedencias` | pares `[predecessora, sucessora]` |
| `orcamento` | custo máximo permitido para o projeto |

### Colaboradores elegíveis

A tabela `duracao` define quem pode executar cada tarefa. **Um colaborador que não aparece na tabela de uma tarefa não pode executá-la.** No exemplo acima, só Bruno pode fazer a tarefa B. O modelo não cria variáveis para os pares proibidos.

Todo colaborador citado em `duracao` precisa estar em `diaria`. Já um colaborador de `diaria` pode estar cadastrado em poucas tarefas, ou até em nenhuma.

### Validação

Antes de montar o modelo, o programa confere se:

- toda tarefa tem pelo menos um colaborador elegível;
- toda duração é um inteiro positivo e cita um colaborador que existe em `diaria`;
- `duracao` e `precedencias` citam apenas tarefas existentes.

Se algo estiver errado, mostra uma mensagem que indica a tarefa com problema e não chama o solver.
