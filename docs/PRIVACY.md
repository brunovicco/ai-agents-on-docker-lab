# Privacy and data handling

Complete this document before processing personal or regulated data.

## Data inventory

| Data category | Source | Purpose | Legal/contractual basis | Destination | Retention | Deletion method |
|---|---|---|---|---|---|---|
| None documented | | | | | | |

## Controls

- Data minimization:
- Access control:
- Encryption in transit:
- Encryption at rest:
- Masking/tokenization:
- Non-production data strategy:
- Logging and tracing restrictions: the package emits no logs or traces and ships no tracing
  backend. Docker Agent transcripts contain the model's prompts and answers, so they stay on the
  operator's machine. Files under `docs/evidence/` record metadata only: versions, event types
  and counts, durations, token counts, and verdicts. Add and follow a backend-specific policy
  before enabling any content-bearing tracing.
- Data-subject deletion/anonymization:
- External processors:
- Incident-response owner:

## Prohibited logging

Secrets, authentication headers, personal identifiers, full financial identifiers, complete request/response payloads, prompts, and model outputs containing sensitive data.
