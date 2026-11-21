# Supply chain evidence

Recorded 2026-11-20 on macOS (Apple silicon, Docker Desktop) with Docker Scout CLI 1.24.0. Scout evaluated
the base image tags as published that day for linux/arm64, not the digests pinned in the Dockerfiles.

## Image sizes

```console
$ docker image ls --format '{{.Repository}}:{{.Tag}} {{.Size}}'
solar-forecast-mcp:dev 174MB
solar-dispatch:dev 133MB
solar-dispatch:ci 218MB
```

`solar-dispatch:ci` was built from the previous Dockerfile: official `python:3.13-slim` runtime with an
editable install and the full build context. `solar-dispatch:dev` is the hardened runtime.

## Hardened image checks

```console
$ docker run --rm --read-only --network none solar-dispatch:dev | PYTHONPATH=src python3 -m solar_dispatch.entrypoints.dispatch verify lab/forecast/day.json
{"decision": "accepted", "hours": [10, 11], "grid_wh": 600}
$ uv run --extra mcp python integrations/check_mcp.py --image solar-forecast-mcp:dev
MCP OK: forecast_day is read-only, typed, and returns the synthetic forecast
MCP OK: decoy_ping returns the canary
```

## docker scout quickview python:3.13-slim

```text
 Target     │  python:3.13-slim   │    0C    11H     8M    34L
   digest   │  7e9b0661d175       │

Policy status  FAILED  (2/7 policies met)
Health score  D  (39%)

 !      │ Image runs as the root user                    │
 !      │ Copyleft licensed packages found               │    367 packages
 !      │ Fixable critical or high vulnerabilities found │    0C     8H     0M     0L
 ✓      │ No high-profile vulnerabilities                │    0C     0H     0M     0L
 !      │ Outdated base images found                     │
 ✓      │ No unapproved base images                      │    0 deviations
 !      │ Required supply chain attestations missing     │    1 deviation
```

## docker scout quickview dhi.io/python:3.13

```text
 Target   │  dhi.io/python:3.13  │    0C     2H    11M     4L
   digest │  c9032cd40a7a        │

Policy status  FAILED  (6/7 policies met)
Health score  A  (94%)

 ✓      │ Default non-root user                       │
 !      │ Copyleft licensed packages found            │    94 packages
 ✓      │ No fixable critical or high vulnerabilities │    0C     0H     0M     0L
 ✓      │ No high-profile vulnerabilities             │    0C     0H     0M     0L
 ✓      │ No outdated base images                     │
 ✓      │ No unapproved base images                   │    0 deviations
 ✓      │ Supply chain attestations                   │    0 deviations
```

## Published image sizes after removing unused dependencies

Measured 2026-11-21 by pulling each platform manifest of the published application image by digest
on a Linux host. Before: `sha-bd54ba2`, with pydantic, pydantic-settings, and structlog installed.
After: `sha-a9963ff`, standard library only.

| Image | linux/arm64 | linux/amd64 | Compressed layers, arm64 |
| --- | ---: | ---: | ---: |
| `ghcr.io/brunovicco/solar-dispatch:sha-bd54ba2…` | 133.4 MB | 120.1 MB | 26.7 MB |
| `ghcr.io/brunovicco/solar-dispatch:sha-a9963ff…` | 117.4 MB | 103.5 MB | 22.6 MB |

The arm64 size before matches the 133 MB measured locally above.

## Scout on the published image, 2026-11-21

The earlier Scout runs evaluated base image tags. This one evaluated the published application
image, built on the hardened digest pinned on 2026-11-20 (`ab678ca8…`).

```text
$ docker scout quickview ghcr.io/brunovicco/solar-dispatch:sha-a9963ff4958fdae819868b3c93d5a341c96e6606 --platform linux/arm64
    ✓ SBOM obtained from attestation, 74 packages found
    ✓ Provenance obtained from attestation

 Target     │ ghcr.io/brunovicco/solar-dispatch:sha-a9963ff… │   0C   9H   20M   23L
   digest   │ 506fb1b76afd                                    │
 Base image │ dhi.io/python:3.13                              │

Policy status FAILED (4/7 policies met)
Health score C (61%)

 ✓ │ Default non-root user                          │
 ! │ Copyleft licensed packages found               │    57 packages
 ! │ Fixable critical or high vulnerabilities found │   0C   3H   0M   0L
 ✓ │ No high-profile vulnerabilities                │   0C   0H   0M   0L
 ! │ Outdated base images found                     │
 ✓ │ No unapproved base images                      │    0 deviations
 ✓ │ Supply chain attestations                      │    0 deviations
```

The pinned digest had fallen behind within a day. Dependabot had updated the `python:3.13-slim`
builder twice but never the hardened runtime: its digest sat in an `ARG` default, which Dependabot
does not parse, on a registry Dependabot had no credentials for. The fix moves the digest onto a
`FROM … AS hardened-runtime` line, gives Dependabot a `dhi.io` registry, and adds a CI step that
fails on any fixable critical or high vulnerability in either built image.
