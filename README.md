# Solar Dispatch Lab

Um carro precisa de 6 kWh até o fim da janela solar. Em quais dois blocos de uma hora ele deve carregar para importar o mínimo possível da rede? O agente recebe uma previsão sintética e devolve uma proposta. O operador usa a previsão original para verificar duração, horários e consumo antes de aceitar o resultado.

Projeto gerado pelo [Codex Python Engineering Harness de Bruno Vicco](https://github.com/brunovicco/codex-python-engineering-harness/tree/e9e297456573d216f070a41a7cdaa108dd599c5b), versão **1.2.1**, perfis **service** e **agentic**. O manifesto original está em `.harness.json`. O pacote preserva as instruções Codex, hooks, skills, arquitetura, inventários, quality gate e CI do gerador. O laboratório aplica a proposta do [anúncio da Docker](https://www.docker.com/blog/meet-the-new-docker-built-to-run-on-trust/) ao planejamento energético. Não há conexão com veículo ou inversor.

## Primeira execução

Na raiz, com Bash e Python 3.13:

```bash
bash lab/demo.sh local
```

Saída esperada: `{"decision": "accepted", "hours": [10, 11], "grid_wh": 600}`.

| Hora | Solar | Consumo da casa | Excedente | Energia da rede ao carregar |
|---|---:|---:|---:|---:|
| 09h | 1.600 Wh | 1.300 Wh | 300 Wh | 2.700 Wh |
| 10h | 3.900 Wh | 1.500 Wh | 2.400 Wh | 600 Wh |
| 11h | 4.800 Wh | 1.800 Wh | 3.000 Wh | 0 Wh |
| 12h | 3.600 Wh | 1.700 Wh | 1.900 Wh | 1.100 Wh |

Os blocos têm potência fixa de 3 kW, podem ser separados e empatam quando usam a mesma energia da rede. O verificador aceita qualquer ótimo. Para ver uma rejeição, envie dois horários válidos de custo maior:

```bash
echo '{"hours":[9,12]}' | PYTHONPATH=src python3 -m solar_dispatch.entrypoints.dispatch verify lab/forecast/day.json
```

## Apresentar com Docker Sandboxes

Com `sbx` instalado, login Docker e suporte a virtualização local, rode:

```bash
bash lab/demo.sh sandbox
bash lab/probe.sh
```

1. Leia o plano do ambiente. A mesa de trabalho é gravável. A previsão em `/forecast` e o pacote em `/lab-src` entram como somente leitura. O arquivo que configura o sandbox fica fora dessas montagens.
2. O mixin instala `solar-plan`. Ele roda dentro do sandbox Shell e escreve a proposta em stdout. O verificador roda no host. O teste de permissões tenta abrir a previsão para escrita sem alterar seu conteúdo.
3. Aplique uma regra de rede limitada ao sandbox e inspecione a decisão da política. O resultado da consulta representa a regra configurada. O roteiro inclui como confrontá-lo com uma requisição real e o log.
4. Para repetir com um agente de IA, use o perfil **Codex** e o servidor MCP de previsão. O roteiro inclui o teste do transporte MCP sem chave de modelo.

**[Roteiro das experiências e mapa de recursos](docs/SANDBOX-LAB.md)** · [Arquitetura do harness](docs/ARCHITECTURE.md) · [Governança](governance/README.md)

## Verificação e reprodução

```bash
uv sync --frozen --all-groups --extra observability --extra mcp
uv run python scripts/quality_gate.py
uv run --extra mcp python integrations/check_mcp.py
```

Para gerar a base novamente, execute no checkout do harness indicado acima:

```bash
python3 bootstrap.py --name solar-dispatch-lab --package solar_dispatch \
  --target ../solar-dispatch-lab --profile service --governance-profile agentic
```

No código do domínio, `dispatch.py` calcula o consumo adicional da rede. A CLI valida o JSON recebido, inclusive tamanho, tipos e duplicatas. `lab/` contém ambientes e experimentos. `integrations/` contém o servidor MCP e seu teste de protocolo. As decisões de governança ficam no host.

### Evidência desta versão

Em 19/11/2026, o quality gate passou com 22 testes e cobertura de 93,70% no pacote Python. O teste MCP negociou uma sessão, descobriu a ferramenta e consultou a previsão por stdio. O CLI sbx v0.54.0 interpretou os planos locais Shell, Codex e preview. O descritor do mixin passou pelo JSON Schema oficial da Docker. A criação da microVM, o build Buildx e as experiências no tenant cloud e empresarial dependem de execução em ambiente com esses recursos. A cobertura reportada mede o pacote Python.
