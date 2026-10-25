# Privacy

Extended Council is a local-first application with no hosted backend, user
accounts, advertising, analytics, crash reporting, or telemetry.

## Data stored locally

The application may store the following under the local `data/` directory:

- tasks, context, criteria, and comparison candidates;
- council presets and role prompts;
- model responses, reviews, syntheses, and errors;
- requested and actual provider/model identity;
- provider-reported latency and usage; and
- artifact paths and lifecycle events.

These runtime files are excluded from git by default. Anyone with filesystem
access to the machine may still be able to read them. Deleting a local run or
clearing the directory is the operator's responsibility.

## Data sent to model providers

When a run uses OpenAI, Anthropic, or OpenRouter, the relevant task, context,
candidates, role instructions, and intermediate council outputs are sent to
that provider. Anonymized peer review hides model names from the review prompt;
it does not make the underlying content anonymous to the provider.

Provider retention, training, residency, and account controls are governed by
the provider and account you configure. Review those terms before submitting
sensitive material.

## Secrets

API keys are read from environment variables or a local `.env` file. They are
not returned by the provider-readiness endpoint and should never be committed.
The application does not include a secrets vault.

## Network boundary

The backend binds to `127.0.0.1` by default. The frontend and backend make no
network calls except normal local application traffic and configured model
provider requests. If you expose the service beyond loopback, you are
responsible for adding authentication, TLS, and network controls.

## Sensitive use

Do not submit credentials, private keys, customer data, health information,
legal material, or other regulated/confidential data unless you have assessed
both local storage and provider handling for that use.
