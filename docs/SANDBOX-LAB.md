# Experimentos de Docker Sandboxes

Use a raiz do projeto como diretório atual. O CLI de referência é o sbx v0.54.0. O percurso Shell roda sem provedor de modelo. Codex usa a autenticação do provedor. Recursos cloud usam a conta Docker e geram cobrança quando executados.

## 1. Máquina local, política e evidência

```bash
sbx login
bash lab/demo.sh sandbox
bash lab/probe.sh
sbx ls
sbx inspect solar-dispatch
sbx env exec lab/sbxenv.yaml -- curl --max-time 5 -fsS https://example.com/
sbx policy log solar-dispatch
```

Depois da regra de bloqueio, a requisição deve falhar. Procure a decisão de bloqueio no log. Uma falha isolada de DNS ou timeout também interrompe o curl e, sozinha, não demonstra enforcement. A regra usa o escopo do sandbox. A verificação do filesystem usa o próprio processo da microVM. Para encerrar, use `sbx stop solar-dispatch` e depois `sbx env rm lab/sbxenv.yaml` quando quiser descartar o ambiente. Os arquivos da mesa montada permanecem no host.

## 2. Codex, credenciais e MCP

Crie o ambiente Codex com o mesmo conjunto de montagens. Registre o servidor confiável a partir desta raiz. O registro aponta para o Python do venv já sincronizado e para o código no host, fora da mesa gravável.

```bash
uv sync --frozen --all-groups --extra observability --extra mcp
uv run --extra mcp python integrations/check_mcp.py
sbx mcp add solar-forecast --command "$PWD/.venv/bin/python" --args integrations/forecast_mcp.py --dir "$PWD"
sbx mcp inspect solar-forecast
sbx env create lab/sbxenv.yaml lab/codex.yaml
sbx mcp load solar-forecast --sandbox solar-dispatch-codex
sbx env run lab/sbxenv.yaml lab/codex.yaml
```

No Codex, peça: **“Consulte forecast_day pelo MCP. Escolha os horários que minimizam a energia da rede e grave somente o JSON com hours em /tmp/solar-answer.json.”** Em outro terminal, valide o arquivo contra os dados originais:

```bash
set -o pipefail
sbx exec solar-dispatch-codex cat /tmp/solar-answer.json |
  PYTHONPATH=src python3 -m solar_dispatch.entrypoints.dispatch verify lab/forecast/day.json
```

Para demonstrar um catálogo fixo, crie outra sessão: `sbx run codex ./lab/desk --name solar-fixed --static-mcp solar-forecast`. Nela, a única fonte necessária é o MCP. Compare o campo MCP de `sbx inspect solar-fixed` com o da sessão dinâmica. Encerre com `sbx rm solar-fixed` e `sbx env rm lab/sbxenv.yaml lab/codex.yaml`. Remova o registro de teste com `sbx mcp rm solar-forecast`.

Para um agente autenticado por chave, use o prompt de `sbx secret set openai` conforme a configuração do provedor. O servidor desta demo só lê a fixture, sem argumentos de caminho e sem credenciais. Para servidores remotos OAuth, a autorização usa `sbx mcp auth`; os registros cloud pertencem ao gateway da conta. [MCP gateway](https://docs.docker.com/ai/sandboxes/mcp-gateway/).

## 3. Kit, porta local e supply chain

O ambiente seleciona um mixin v3 com um executável e contexto para o agente. Valide o descritor pelo frontend oficial no Buildx. A imagem da aplicação usa a base e a ferramenta de build fixadas por digest no Dockerfile do harness.

```bash
docker buildx build -f lab/solar-kit/solar-kit.yaml -t solar-kit:dev lab/solar-kit
docker build -t solar-dispatch:dev .
docker run --rm --read-only --network none solar-dispatch:dev
sbx env create lab/sbxenv.yaml lab/preview.yaml
sbx env exec lab/sbxenv.yaml lab/preview.yaml -- python3 -m http.server 8000 --directory /forecast
```

Abra http://localhost:8765/day.json em outro terminal ou navegador. O serviço expõe a previsão sintética. Interrompa o servidor e rode `sbx env rm lab/sbxenv.yaml lab/preview.yaml`. Para gerar SBOM e proveniência sem publicar imagem, use um builder com exportador OCI:

```bash
docker buildx create --name solar-attest --driver docker-container
docker buildx build --builder solar-attest --sbom=true --provenance=mode=max --output type=oci,dest=solar.oci.tar .
docker buildx rm solar-attest
```

A imagem Python deste projeto usa Docker Official Images. O catálogo Docker Hardened Images tem distribuição e atestações próprias. Um exercício adicional com registro DHI é `sbx mcp add fetch-dhi --url dhi.io/fetch-mcp:latest`, seguido de `sbx mcp inspect fetch-dhi` e `sbx mcp rm fetch-dhi`. Esse servidor é dispensável para o plano solar.

## 4. Cloud e transferência

Com acesso a compute cloud, crie um sandbox com expiração e copie somente código e previsão. Em uma instância nova:

```bash
sbx --cloud create --name solar-cloud --ttl 30m --on-timeout delete shell
sbx --cloud cp ./src solar-cloud:/tmp/solar-src
sbx --cloud cp ./lab/forecast/day.json solar-cloud:/tmp/day.json
set -o pipefail
sbx --cloud exec solar-cloud env PYTHONPATH=/tmp/solar-src python3 -m solar_dispatch.entrypoints.dispatch plan /tmp/day.json |
  PYTHONPATH=src python3 -m solar_dispatch.entrypoints.dispatch verify lab/forecast/day.json
sbx --cloud ttl solar-cloud
sbx --cloud rm solar-cloud
```

Para explorar a alternativa declarativa, rode `sbx --cloud env plan lab/cloud.yaml`. O cloud tem armazenamento próprio para segredos, políticas e volumes. Verifique a política de destino depois de um `sbx move`. O workspace montado no host precisa de transferência explícita. Portas publicadas no cloud geram URLs externas. [Diferenças entre local e cloud](https://docs.docker.com/ai/sandboxes/cloud/local-vs-cloud/).

## 5. Demais famílias de recursos

| Família | Experimento ou ponto de inspeção | O que observar |
|---|---|---|
| Git e worktrees | Em um checkout Git com commit, use `sbx run codex --clone .`. Consulte `sbx create --help` para selecionar uma branch | O clone interno permite revisar mudanças antes de integrá-las |
| Skills e modelos | `sbx skills ls`, `sbx create --help`. Compare o contexto do mixin com `.agents/skills/` do harness | Skills do host, instruções do projeto e contexto do kit têm origens distintas. A mesa padrão contém apenas a tarefa |
| IDE e SSH | `sbx setup ssh`. Abra o sandbox com o cliente SSH do VS Code ou Cursor | O editor acessa a máquina em que o agente trabalha |
| Proxies, espelhos e políticas de kits | `sbx settings --help`, `sbx kit --help` | Compare configuração do host, fontes aceitas e políticas da organização |
| Hardware e outros agentes | Inspecione `sbx create --help` para opções disponíveis na sua plataforma e `sbx run --help` para os workloads | GPU, USB, display e virtualização aninhada dependem do host. A previsão usa apenas CPU |
| Volumes, templates e migração | `sbx --cloud volume ls`, `sbx template ls`, `sbx move --help` | Diferencie estado persistente da VM, transferência de arquivos e snapshot de volume |
| Agendamento | `sbx --cloud schedule create shell --name solar-clock --cron '0 8 * * *' --timezone America/Sao_Paulo --enabled=false --command 'date -u'` | Cria um exemplo pausado. Veja em `sbx --cloud schedule ls`; remova pelo ID. Para agendar a previsão, disponibilize código e dados em um kit cloud |
| Operação e diagnóstico | `sbx df`, `sbx tui`, `sbx diagnose --help` | Inspeção de estado, disco e suporte |
| Gestão empresarial | Compare a política local com o perfil aplicado por um administrador em uma organização licenciada | Docker AI Governance e MCP Enterprise Gateway dependem do tenant. Inventários JSON desta aplicação registram decisões de projeto. [Docker AI Governance](https://docs.docker.com/ai/governance/) |
| APIs, SDK, editores e integrações adicionais | [Índice oficial de Sandboxes](https://docs.docker.com/ai/sandboxes/) | Confira disponibilidade por backend e produto |

Para explorar **todos os comandos e flags expostos pelo CLI instalado**, gere o catálogo pesquisável a partir do próprio help. O script percorre os dois backends sob demanda. Não cria recursos. As integrações de IDE, SDKs e painéis empresariais têm documentação própria.

```bash
bash lab/catalog.sh local > /tmp/solar-sbx-local.md
bash lab/catalog.sh cloud > /tmp/solar-sbx-cloud.md
```
