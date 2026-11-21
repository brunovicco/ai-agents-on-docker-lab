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
`FROM … AS hardened-runtime` line and gives Dependabot a `dhi.io` registry.

## The newest hardened base, 2026-11-21

Moving the pin to the current `dhi.io/python:3.13` (`sha256:e1469187…`) did not clear the findings.
CI scanned both built images on it, linux/amd64:

| Package | Fixable high | Fixed in |
| --- | --- | --- |
| glibc 2.41-12+deb13u4+dhi1 | CVE-2026-19499, CVE-2026-5435 | 2.41-12+deb13u5, not yet in a DHI build |
| setuptools 70.3.0, in the base | CVE-2025-47273 | 78.1.1 |

`docker scout quickview dhi.io/python:3.13` on linux/arm64 counted 2 fixable high for the base
alone, with 42 DHI VEX exceptions applied; the scan of the built image counted 3.

A gate on every fixable vulnerability would stay red until DHI ships the glibc fix. CI therefore
reports each image's fixable critical and high vulnerabilities, base included, in the job summary,
and fails only on CVE IDs that an image has and its pinned hardened base does not. The base is
pulled and scanned from the local store like the images, so both sides get the same VEX treatment.
The CI run on 2026-11-21 printed `solar-dispatch:ci adds none; 3 come from the hardened base` and
the same for the MCP image.

Three earlier designs failed, each for a reason worth knowing:

- `--ignore-base` stopped with `no base image could be identified`: Scout cannot attribute layers
  of an image built with `docker build`, which carries no provenance.
- `docker/scout-action` downloads its 187 MB binary from the GitHub API asset URL without a token,
  once per step. The anonymous request returned HTTP 403 on two runs. CI now runs the
  `docker/scout-cli` image, pinned by digest, which also needs a writable Docker config directory
  and `/tmp`.
- `docker scout compare --exit-on vulnerability` reported two vulnerabilities added where none
  were. It moved the glibc CVEs between the `glibc` and `libc6` packages, and the base, read from
  the registry, got DHI VEX statements that the local image did not. Its policy table, below, shows
  no change.

```text
                     │ Analyzed Image             │ Comparison Image
   Target            │ local://solar-dispatch:ci  │ registry://dhi.io/python:3.13
     platform        │ linux/amd64                │ linux/amd64
     size            │ 23 MB (+21 kB)             │ 23 MB
     packages        │ 89 (+1)                    │ 88
    Policy                                       Analyzed  Comparison  Change
    No fixable critical or high vulnerabilities  ! 3       ! 3         No Change
```
