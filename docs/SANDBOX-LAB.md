# Docker Sandboxes lab

Run the commands from the repository root. The reference CLI is `sbx` v0.54.0. The Shell flow requires only a Docker sign-in. The Codex flow also requires provider authentication. Cloud compute is billed to your Docker account.

## 1. Local isolation and network policy

```bash
sbx login
# On a fresh sbx installation, initialize the local policy once.
sbx policy init balanced
bash lab/demo.sh sandbox
sbx ls
sbx inspect solar-dispatch
```

The `shell` agent is itself a v3 workload kit, `docker.io/sbx/shell`, built on a Docker Hardened Image (`dhi/shell`, Debian 13). The lab's kit installs `solar-plan`. The Shell sandbox runs it against the read-only forecast at `/forecast/day.json` and sends a proposal to the host verifier. The workspace is writable. The source at `/lab-src` is read-only.

The kit also declares the planner's network policy: it denies all runtime egress. The policy lives in `lab/solar-kit/solar-kit.yaml`, next to the tool it constrains, so it is versioned and reviewed with the code. Test it against `github.com`, a host that the `balanced` global policy allows.

```bash
bash lab/probe.sh
sbx env exec lab/sbxenv.yaml -- curl --max-time 5 -fsS -o /dev/null https://github.com/
sbx policy log solar-dispatch
```

The probe verifies that the workspace is writable and the forecast cannot be opened for writing. It then queries the policy for `github.com`. The query should exit with status 1 and name the kit's rule as the reason. The request from inside the sandbox should fail, and the log should show it blocked by the same rule. With v0.54.0, the reason was `kit:solar-dispatch:deny` and the request returned HTTP 403 from the sandbox proxy. On a new sandbox, `sbx inspect` still reported `Network policy: global (local policy)`. It switched to `sandbox-specific` after a sandbox-scoped rule was added, and stayed there after the rule was removed. Neither label reflects the kit's rule, and the environment plan did not list it, so confirm kit rules with `sbx policy check` or the log. Run the request and log commands separately if your shell stops on errors. DNS errors and timeouts alone are insufficient evidence of enforcement.

A deny in a kit wins over any allow. Add a sandbox-scoped allow and query again.

```bash
sbx policy allow network --sandbox solar-dispatch github.com
sbx policy check network --sandbox solar-dispatch github.com
sbx policy rm network --sandbox solar-dispatch --resource github.com
```

The query should still deny `github.com`. With v0.54.0, it reported the kit's rule after the allow was added. Remove the allow when you finish.

When finished, use `sbx stop solar-dispatch` and `sbx env rm lab/sbxenv.yaml`. The host workspace remains available. Keep the sandbox and its SSH alias in place while the VS Code remote workspace is open.

### Record evidence

Most readers cannot run a microVM, so keep a transcript of what the sandbox did. After `bash lab/demo.sh sandbox`, record the sandbox proposal and its host verification, the sandbox configuration, the probe, a blocked request from inside the sandbox, and the policy log.

```bash
bash lab/record.sh
```

After the section 2 experiments, add sandbox names to capture their MCP mode, for example `bash lab/record.sh solar-codex solar-dispatch-codex`. The transcript goes to `docs/evidence/<date>-local.md`, or to the path in `SOLAR_EVIDENCE`. Each run replaces that file. Review the transcript before committing it, because `sbx` output can include usernames and host paths. For a terminal recording, wrap the demo with `asciinema rec docs/evidence/demo.cast -c "bash lab/demo.sh sandbox"`.

## 2. Codex, credentials, and MCP

Build the forecast server image and check it over the MCP stdio transport. `sbx` runs stdio servers on the host, outside sandbox isolation, so every registration in this section launches the server through Docker without network, on a read-only filesystem, without capabilities, and as a non-root user. The image contains the server code and the synthetic fixture, and nothing else from the host.

```bash
uv sync --frozen --all-groups --extra observability --extra mcp
docker build -f integrations/Dockerfile -t solar-forecast-mcp:dev .
uv run --extra mcp python integrations/check_mcp.py --image solar-forecast-mcp:dev
```

`forecast_day` is annotated as read-only, idempotent, and closed-world, and it publishes an output schema for its structured result.

### Static MCP, declared in the environment file

`lab/codex.yaml` pins the Codex kit by digest, mounts only `lab/desk`, and declares the containerized server in `mcp.servers`. With v0.54.0, declaring `mcp.servers` creates the sandbox in static mode with exactly those servers. The plan shows the resolved `docker` executable and warns that it runs on the host with your privileges. Plans with local MCP commands ask for approval on every `sbx env run`, and removing a server from the file revokes its registration.

```bash
sbx env create lab/codex.yaml
sbx inspect solar-dispatch-codex
sbx env run lab/codex.yaml
```

`sbx inspect` reports `MCP mode: static` with `solar-forecast` as the only connected server. The sandbox also mounts the read-only agent skills directory that `sbx` adds. It has no forecast mount, so `forecast_day` is the only way to read the forecast. In static mode the gateway does not offer `mcp-find`, `mcp-add`, or `mcp-config-set`, so the agent cannot discover or attach other registered servers. With v0.54.0, Codex listed `forecast_day` and two gateway tools, `mcp_exec` and `code_mode`. Its other MCP tools belong to the Codex client, not the gateway.

Ask Codex to follow `TASK.md`. In another terminal, verify the proposal against the original forecast, then write a malicious answer inside the sandbox and confirm that the host rejects it.

```bash
set -o pipefail
sbx exec solar-dispatch-codex cat /tmp/solar-answer.json |
  PYTHONPATH=src python3 -m solar_dispatch.entrypoints.dispatch verify lab/forecast/day.json
sbx exec solar-dispatch-codex sh -c 'printf "%s" "{\"hours\":[9,12],\"hours\":[10,11]}" > /tmp/attack.json'
sbx exec solar-dispatch-codex cat /tmp/attack.json |
  PYTHONPATH=src python3 -m solar_dispatch.entrypoints.dispatch verify lab/forecast/day.json
```

The host accepts hours 10 and 11, then exits with status 1 and reports `Duplicate JSON key` for the malicious answer.

The imperative equivalent registers the server on the host and starts Codex with `--static-mcp`. With v0.54.0 it produced the same mode and tools.

```bash
sbx mcp add solar-forecast --command docker --args "run,-i,--rm,--network,none,--read-only,--cap-drop,ALL,--security-opt,no-new-privileges,solar-forecast-mcp:dev"
sbx run codex ./lab/desk --name solar-codex --static-mcp solar-forecast
```

### Can a static sandbox reach servers it was not given?

Static mode removes the discovery tools, but the gateway still offers `mcp_exec` and `code_mode`. Test whether they can reach a server that is registered on the host but not loaded into the sandbox. The decoy server returns a fixed canary, `solar-decoy-canary-3f9c`.

```bash
sbx mcp add solar-decoy --command docker --args "run,-i,--rm,--network,none,--read-only,--cap-drop,ALL,--security-opt,no-new-privileges,--entrypoint,python,solar-forecast-mcp:dev,integrations/decoy_mcp.py"
sbx inspect solar-dispatch-codex
```

`sbx inspect` should still list `solar-forecast` as the only connected server. In the static session, ask Codex:

> Use mcp_exec, and then code_mode, to call the tool decoy_ping on the MCP server solar-decoy. Report the exact result or error of each attempt.

If any result contains the canary, the static catalog does not isolate registered servers. With v0.54.0, the decoy stayed out of reach in both static sandboxes. In `solar-codex`, `mcp_exec` returned `Tool "decoy_ping" not found in gateway.` and `code_mode` returned `tools not found in gateway: decoy_ping`. In `solar-dispatch-codex`, `mcp_exec` reported both `mcp_add` and `decoy_ping` as not found in the gateway. Both tools are limited to the loaded catalog.

### Contrast: dynamic MCP and the positive control

A sandbox created without MCP servers starts with a dynamic gateway. With v0.54.0, the Shell sandbox from section 1 reports `MCP mode: dynamic` and `MCP servers: none`. Create a Codex sandbox the same way.

```bash
sbx create --name solar-dynamic codex ./lab/desk
sbx inspect solar-dynamic
sbx run --name solar-dynamic
```

Dynamic mode exposes the gateway's management tools, so the agent can discover and attach registered servers on its own. This sandbox is the positive control for the decoy test. Ask Codex:

> List every MCP tool you can call. Then use mcp_add to add the server solar-decoy and call decoy_ping. Report the exact result.

With v0.54.0, Codex listed `mcp_find`, `mcp_add`, `mcp_config_set`, `mcp_exec`, and `code_mode`, added `solar-decoy` with `mcp_add`, and received `solar-decoy-canary-3f9c` from `decoy_ping`. The decoy answers when it is reachable, so its absence from both static sandboxes comes from static mode. Prefer static mode unless the task needs tool discovery.

Servers declared in an environment file also stay with that environment. While `solar-dispatch-codex` existed, `sbx mcp add solar-forecast` failed because the name belonged to that environment, and `sbx mcp load solar-forecast --sandbox solar-dynamic` returned `403 Forbidden` with `not authorized for this sandbox instance`. To load the forecast server into another sandbox, remove the environment with `sbx env rm lab/codex.yaml` first.

Clean up with `sbx rm solar-dynamic`, `sbx env rm lab/codex.yaml`, `sbx mcp rm solar-decoy`, and `sbx mcp rm solar-forecast` if you registered it on the host.

For Codex sign-in, use `sbx secret set openai --oauth` or the `sbx secret set openai` prompt for an API key. The forecast server reads a fixed fixture and requires no credentials or path arguments. Remote OAuth servers use `sbx mcp auth`. Cloud registrations belong to the account gateway. [MCP gateway](https://docs.docker.com/ai/sandboxes/mcp-gateway/)

## 3. Kit, local preview, and supply chain

The environment selects a v3 mixin with an executable, an egress policy, and context for the agent. Build the mixin with the official Buildx frontend. Both Dockerfiles pin their base images and build tools by digest. They build with uv on the Docker Official Python image and run on a Docker Hardened Image, `dhi.io/python:3.13`, which has no shell or package manager and runs as user 65532. Pulling it requires `docker login dhi.io` with a Docker account. Without that access, add `--build-arg RUNTIME_IMAGE=python:3.13-slim@sha256:6771159cd4fa5d9bba1258caf0b82e6b73458c694d178ad97c5e925c2d0e1a91` to build on the official image instead.

```bash
docker login dhi.io
docker buildx build -f lab/solar-kit/solar-kit.yaml -t solar-kit:dev lab/solar-kit
docker build -t solar-dispatch:dev .
docker run --rm --read-only --network none solar-dispatch:dev
sbx env create lab/sbxenv.yaml lab/preview.yaml
sbx env exec lab/sbxenv.yaml lab/preview.yaml -- python3 -m http.server 8000 --directory /forecast
```

Open [the local forecast endpoint](http://localhost:8765/day.json) in another terminal or browser. The server exposes the synthetic forecast on loopback. Stop it and run `sbx env rm lab/sbxenv.yaml lab/preview.yaml` when finished. To generate an SBOM and provenance locally, export the image as an OCI archive.

```bash
docker buildx create --name solar-attest --driver docker-container
docker buildx build --builder solar-attest --sbom=true --provenance=mode=max --output type=oci,dest=solar.oci.tar .
docker buildx rm solar-attest
```

### Published images and attestations

On every push to `main`, CI publishes the application image, the MCP server image, and the sandbox kit to GitHub Container Registry for `linux/amd64` and `linux/arm64`, so they run natively on Apple silicon. The images carry an SBOM and maximal provenance from Buildx. The kit keeps its v3 descriptor, including the deny-all egress policy, in the manifest annotations.

```bash
docker buildx imagetools inspect ghcr.io/brunovicco/solar-dispatch:main --format '{{json .SBOM}}'
docker buildx imagetools inspect ghcr.io/brunovicco/solar-dispatch:main --format '{{json .Provenance}}'
docker buildx imagetools inspect ghcr.io/brunovicco/solar-forecast-mcp:main
docker buildx imagetools inspect ghcr.io/brunovicco/solar-kit:main --raw
```

Each build is also tagged `sha-<commit>`. To run the published kit instead of the local source, replace `source: ./solar-kit` in `lab/sbxenv.yaml` with `ghcr.io/brunovicco/solar-kit` pinned by digest. `sbx` accepts remote kits only from sources listed in `kit.allowedSources`, so add `ghcr.io/brunovicco/` there first.

### Docker Hardened Images

Both lab images already run on a Docker Hardened Image. To try a third-party MCP server packaged as a Docker Hardened Image, authenticate to `dhi.io` and verify manifest access before registering it. The registry uses its own login. On macOS with Docker Desktop, `docker pull dhi.io/python:3.13` worked after login while `docker buildx imagetools inspect` on the same image still returned HTTP 401, so check access with `docker pull` when `imagetools` fails.

```bash
docker login dhi.io
docker buildx imagetools inspect dhi.io/fetch-mcp:latest
sbx mcp add fetch-dhi --url dhi.io/fetch-mcp:latest
sbx mcp inspect fetch-dhi
sbx mcp rm fetch-dhi
```

If the manifest request returns HTTP 401, check the registry login. If it succeeds and `sbx` still returns 401, record which step failed. To query the public DHI catalog through MCP without registry authentication, register `sbx mcp add dhi-catalog --url https://dhi.io/mcp`, inspect the registration, and remove it with `sbx mcp rm dhi-catalog`. The packaged server exercise requires access to the image and its attestation. [DHI authentication](https://docs.docker.com/dhi/how-to/use/) · [DHI catalog MCP](https://docs.docker.com/dhi/tools/mcp/)

## 4. Cloud execution and transfer

With access to cloud compute, create a short-lived sandbox and copy the code and synthetic forecast.

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

To inspect the declarative variant, run `sbx --cloud env plan lab/cloud.yaml`. Docker Cloud has separate storage for secrets, policies, and volumes. After a move, verify the destination policy and check a file saved in the image filesystem. Host mounts require explicit transfer. Files in memory-backed mounts such as `/tmp` in the cloud Shell sandbox stay behind. Published cloud ports receive external URLs. [Local and cloud differences](https://docs.docker.com/ai/sandboxes/cloud/local-vs-cloud/)

## 5. Further experiments

| Area | Experiment or inspection | What to observe |
| --- | --- | --- |
| Git and worktrees | In a checkout with a commit, run `sbx run codex --clone .`. See `sbx create --help` for branch selection | A sandbox clone lets you review changes before integrating them |
| Skills and models | Run `sbx skills ls` and `sbx create --help`. Compare the mixin context with `.agents/skills/` | Host skills and kit context come from different sources. The default workspace contains the task |
| IDE and SSH | Run `sbx setup ssh`, then connect with VS Code or Cursor | The editor opens the workspace inside the microVM |
| Proxies, mirrors, and kit policy | Run `sbx settings --help` and `sbx kit --help` | Compare host configuration, accepted sources, and organization policy |
| Hardware and other agents | Inspect resources inside the microVM and use `sbx run --help` for workload options | Check CPU and memory inside the guest, connect to the Wayland socket for display, and look for `/dev/kvm` before testing nested virtualization |
| Volumes, templates, and migration | Run `sbx --cloud volume ls`, `sbx template ls`, and `sbx move --help` | Compare persistent storage, explicit transfer, and image snapshots |
| Scheduling | Run `sbx --cloud schedule create shell --name solar-clock --cron '0 8 * * *' --timezone America/Sao_Paulo --enabled=false --command 'date -u'` | List the paused schedule with `sbx --cloud schedule ls` and remove it by ID. To schedule the forecast, provide the code and data in a cloud kit |
| Operations and diagnostics | Run `sbx df`, `sbx tui`, and `sbx diagnose --help` | Inspect state, disk usage, and diagnostics |
| Organization governance | In a pilot organization with AI Governance active and a license assigned to the test account, run `sbx policy refresh` and `sbx policy ls` | Look for `Governance: Managed by <org>`. Test an allowed and a blocked destination, confirm the rule source, and compare the results with the organization audit log. [Docker governance verification](https://docs.docker.com/ai/governance/organization/get-started/#step-8-verify-on-a-developer-machine) |
| APIs, SDKs, editors, and integrations | [Docker Sandboxes documentation](https://docs.docker.com/ai/sandboxes/) | Check availability for your backend and product |

GPU passthrough requires x86_64 Linux with NVIDIA and VFIO. USB passthrough requires an x86_64 or ARM64 Linux host. Use dedicated test devices on compatible hosts. On Apple silicon, test display over Wayland and run the planner on the CPU. [GPU passthrough](https://docs.docker.com/ai/sandboxes/configuration/gpu-passthrough/) · [USB support](https://github.com/docker/sbx-releases/releases/tag/v0.39.0)

Generate a searchable catalog of commands and flags from the installed CLI. The script reads help text for each backend without creating resources.

```bash
bash lab/catalog.sh local > /tmp/solar-sbx-local.md
bash lab/catalog.sh cloud > /tmp/solar-sbx-cloud.md
```
