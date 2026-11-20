# Solar Dispatch Lab

[English](README.md) · **Português do Brasil**

> **Confie no verificador, não no agente.** Um planejador dentro de um sandbox Docker só pode propor. O host decide, usando uma previsão que o sandbox não consegue alterar.

Execute um planejador de recarga no **Docker Sandboxes** e valide a proposta no host. O sandbox recebe uma área de trabalho gravável e uma previsão solar de somente leitura. O host mantém a previsão original e toma a decisão final.

O exercício usa dados sintéticos. Um veículo elétrico precisa de **6 kWh**, e o planejador deve escolher as duas horas de menor consumo de energia da rede.

## Execute o experimento com Docker

Na raiz do repositório, com Bash, Python 3.13 e uma sessão autenticada no `sbx` em uma máquina com suporte à virtualização local:

```bash
bash lab/demo.sh sandbox
```

O script exibe o plano do ambiente, cria uma microVM Shell e executa o comando `solar-plan` do kit. O verificador no host imprime:

```json
{"decision": "accepted", "hours": [10, 11], "grid_wh": 600}
```

Para guardar uma transcrição revisável da execução, rode `bash lab/record.sh` em seguida. Veja [Record evidence](docs/SANDBOX-LAB.md#record-evidence).

Para a primeira configuração, incluindo a inicialização da política de rede local, consulte o [roteiro de Docker Sandboxes](docs/SANDBOX-LAB.md#1-local-isolation-and-network-policy).

## Como o experimento funciona

```mermaid
flowchart TB
    Forecast["Previsão original no host"]
    subgraph Sandbox["Sandbox Docker"]
        Planner["Planejador Shell ou agente Codex"]
    end
    Forecast -->|"Montagem somente leitura (Shell)"| Planner
    Forecast --> MCP["Ferramenta forecast_day de somente leitura no host"]
    MCP -->|"Gateway MCP (Codex)"| Planner
    Planner -->|"Horários propostos em JSON"| Verify{"Proposta válida e ótima? (verificador no host)"}
    Forecast -->|"Dados originais"| Verify
    Verify -->|"Sim"| Accept["Aceita e informa o consumo da rede"]
    Verify -->|"Não"| Reject["Rejeita a proposta"]
```

## Explore outras etapas

| Experimento | O que observar |
| --- | --- |
| [Sistema de arquivos e política de rede](docs/SANDBOX-LAB.md#1-local-isolation-and-network-policy) | Confirme que a área de trabalho é gravável e a previsão é somente leitura. Identifique no log a regra que bloqueou uma requisição. |
| [Codex via MCP](docs/SANDBOX-LAB.md#2-codex-credentials-and-mcp) | Dê ao Codex uma única ferramenta MCP estática, valide a proposta no host e compare com um gateway dinâmico. |
| [Buildx e cadeia de suprimentos](docs/SANDBOX-LAB.md#3-kit-local-preview-and-supply-chain) | Compile o kit e a imagem da aplicação, sirva a previsão em loopback e exporte um arquivo OCI com SBOM e proveniência. |
| [Docker Cloud](docs/SANDBOX-LAB.md#4-cloud-execution-and-transfer) | Execute o planejador em um sandbox temporário na nuvem e valide o resultado no host. |

A documentação técnica está em inglês.

[Modelo de recarga](docs/DISPATCH.md) · [Arquitetura](docs/ARCHITECTURE.md) · [Governança](governance/README.md) · [Desenvolvimento e testes locais](docs/DEVELOPMENT.md)
