# Cronograma de Projeto com Programação Inteira

Trabalho final da disciplina **COS360 – Otimização**, da **Universidade Federal do Rio de Janeiro (UFRJ)**.

O programa usa programação linear inteira para alocar as tarefas de um projeto entre colaboradores. O objetivo é **minimizar o prazo total do projeto**, respeitando:

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
| $d_{ik}$ | duração (em dias) da tarefa $i$ quando executada por $k$ |
| $P$ | pares $(i, j)$: a tarefa $i$ precisa terminar antes de $j$ começar |
| $B$ | orçamento total |
| $H$ | horizonte de planejamento: $H = \sum_{i} \max_k d_{ik}$ |

### Variáveis de decisão

- $x_{ikt} \in \{0, 1\}$: vale 1 se a tarefa $i$ for feita pelo colaborador $k$ começando no dia $t$, com $t = 1, \dots, H - d_{ik} + 1$.
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
│   └── reduzido.json   # instância de exemplo (5 tarefas, 3 colaboradores)
├── dados.py            # leitura e validação dos dados de entrada
├── modelo.py           # construção do modelo de programação inteira
├── main.py             # interface de linha de comando: resolve e mostra o cronograma
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
```

Se não houver solução que caiba no orçamento, o programa mostra o status `Infeasible` e não imprime cronograma.

## Criando novas instâncias

Cada instância é um arquivo JSON na pasta `dados/`. Para criar uma nova, copie `dados/reduzido.json` e mude os valores:

```json
{
  "tarefas": ["A", "B", "C"],
  "diaria": { "Ana": 350, "Bruno": 300 },
  "duracao": {
    "A": { "Ana": 1, "Bruno": 2 },
    "B": { "Ana": 2, "Bruno": 1 },
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
| `duracao` | para cada tarefa, quantos dias cada colaborador leva para concluí-la |
| `precedencias` | pares `[predecessora, sucessora]` |
| `orcamento` | custo máximo permitido para o projeto |

Antes de montar o modelo, o programa confere se toda tarefa tem duração para todos os colaboradores e se as precedências citam apenas tarefas existentes. Se algo estiver errado, mostra uma mensagem explicando o problema.
