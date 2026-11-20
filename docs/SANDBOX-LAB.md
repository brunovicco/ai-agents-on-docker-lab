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

The kit installs `solar-plan`. The Shell sandbox runs it against the read-only forecast at `/forecast/day.json` and sends a proposal to the host verifier. The workspace is writable. The source at `/lab-src` is read-only.

To demonstrate enforcement, establish a baseline with an allow rule scoped to this sandbox, then replace it with a deny rule.

```bash
sbx policy allow network --sandbox solar-dispatch example.com
sbx env exec lab/sbxenv.yaml -- curl --max-time 10 -fsS -o /dev/null https://example.com/
sbx policy rm network --sandbox solar-dispatch --resource example.com
bash lab/probe.sh
sbx env exec lab/sbxenv.yaml -- curl --max-time 5 -fsS https://example.com/
sbx policy log solar-dispatch
```

The probe first verifies that the workspace is writable and the forecast cannot be opened for writing. It then adds a sandbox-scoped deny rule and queries the policy. The query exits with status 1 for the expected denial. Run the final request and log commands separately if your shell stops on errors. A blocked request should match the new deny rule in the log. DNS errors and timeouts alone are insufficient evidence of enforcement.

When finished, use `sbx stop solar-dispatch` and `sbx env rm lab/sbxenv.yaml`. The host workspace remains available. Keep the sandbox and its SSH alias in place while the VS Code remote workspace is open.

### Record evidence

Most readers cannot run a microVM, so keep a transcript of what the sandbox did. After `bash lab/demo.sh sandbox`, record the sandbox proposal and its host verification, the sandbox configuration, the probe, and the policy log.

```bash
bash lab/record.sh
```

After the section 2 experiments, add sandbox names to capture their MCP mode, for example `bash lab/record.sh solar-codex solar-dispatch-codex`. The transcript goes to `docs/evidence/<date>-local.md`, or to the path in `SOLAR_EVIDENCE`. Each run replaces that file. The probe adds the sandbox-scoped deny rule again. Review the transcript before committing it, because `sbx` output can include usernames and host paths. For a terminal recording, wrap the demo with `asciinema rec docs/evidence/demo.cast -c "bash lab/demo.sh sandbox"`.

## 2. Codex, credentials, and MCP

Register the forecast server from the repository root. The registration points to the synchronized Python environment and server code on the host, outside any sandbox workspace. Stdio servers run on the host with your privileges, so register only code you have reviewed.

```bash
uv sync --frozen --all-groups --extra observability --extra mcp
uv run --extra mcp python integrations/check_mcp.py
sbx mcp add solar-forecast --command "$PWD/.venv/bin/python" --args integrations/forecast_mcp.py --dir "$PWD"
sbx mcp inspect solar-forecast
```

### Static MCP: one tool, nothing else

Start Codex with the task workspace and a fixed tool catalog.

```bash
sbx run codex ./lab/desk --name solar-codex --static-mcp solar-forecast
```

This session mounts only `lab/desk`. It has no forecast mount, so `forecast_day` is the only way to read the forecast. In static mode the gateway does not offer `mcp-find`, `mcp-add`, or `mcp-config-set`, so the agent cannot attach other registered servers. Ask Codex to follow `TASK.md` and approve the read-only tool call if prompted. In another terminal, confirm the mode and verify the proposal against the original forecast.

```bash
sbx inspect solar-codex
set -o pipefail
sbx exec solar-codex cat /tmp/solar-answer.json |
  PYTHONPATH=src python3 -m solar_dispatch.entrypoints.dispatch verify lab/forecast/day.json
```

The MCP fields of `sbx inspect` should report static mode with `solar-forecast` as the only connected server.

### Contrast: dynamic MCP

Create the Codex environment on top of the Shell environment and load the server into the running sandbox.

```bash
sbx env create lab/sbxenv.yaml lab/codex.yaml
sbx mcp load solar-forecast --sandbox solar-dispatch-codex
sbx inspect solar-dispatch-codex
sbx env run lab/sbxenv.yaml lab/codex.yaml
```

This sandbox keeps the kit and the read-only mounts, and its gateway runs in dynamic mode. Dynamic mode exposes `mcp-find`, `mcp-add`, and `mcp-config-set`, so the agent can attach registered servers on its own. Compare its MCP fields with `solar-codex`. Prefer static mode unless the task needs tool discovery.

Remove the test sandboxes with `sbx rm solar-codex` and `sbx env rm lab/sbxenv.yaml lab/codex.yaml`, then remove the registration with `sbx mcp rm solar-forecast`.

For Codex sign-in, use `sbx secret set openai --oauth` or the `sbx secret set openai` prompt for an API key. The forecast server reads a fixed fixture and requires no credentials or path arguments. Remote OAuth servers use `sbx mcp auth`. Cloud registrations belong to the account gateway. [MCP gateway](https://docs.docker.com/ai/sandboxes/mcp-gateway/)

## 3. Kit, local preview, and supply chain

The environment selects a v3 mixin with an executable and context for the agent. Build the mixin with the official Buildx frontend. The application Dockerfile pins its base images and build tools by digest.

```bash
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

### Docker Hardened Images

The application uses Docker Official Images. To try a separate MCP server packaged as a Docker Hardened Image, authenticate to `dhi.io` and verify manifest access before registering it. The registry uses its own login.

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
