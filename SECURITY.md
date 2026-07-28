# Security policy

## Supported versions

Security fixes are provided for the latest release of `veritas-leakage`.

## Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability. Use GitHub's
[private vulnerability reporting](https://github.com/shreyjain11/veritas/security/advisories/new)
to share reproduction details and impact privately. You should receive an initial
response within five business days.

Never include API keys, private benchmark contents, or other secrets in a report.

## Secret handling

The hosted browser audit accepts bring-your-own provider credentials for a single
request. Veritas application code keeps the credential in request memory only and
does not serialize it into reports, caches, cookies, browser storage, or application
logs. Provider prompts and credentials are still transferred over HTTPS to the
selected provider and remain subject to that provider's policies.
