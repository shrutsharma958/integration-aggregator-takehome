# Integration Aggregator — Design

## 1. Architecture

The service is a single FastAPI HTTP service deployed on Kubernetes using Helm.

The main components are:

* **Integration Aggregator** — FastAPI service providing the provider registration, OAuth connection, callback, and asynchronous credential retrieval APIs.
* **OpenBao** — the only persistent backing store for provider client secrets and OAuth credentials/tokens.
* **OpenBao OAuth plugin** — manages OAuth provider interactions and token freshness/refresh behavior.
* **Kubernetes / Minikube** — runs the service and OpenBao.
* **Helm** — packages and deploys the application.
* **GHCR** — stores the published container image and Helm chart.

No application database is used.

## 2. OAuth Flow

A provider is registered through:

`POST /providers`

The provider's client ID and client secret are stored in OpenBao.

When a user connects:

`POST /providers/{provider}/users/{user}/connect`

the service generates a random OAuth `state` value and stores the temporary state in memory. It then asks the OpenBao OAuth plugin to generate the provider authorization URL.

The provider redirects back to:

`GET /callback`

The service validates the OAuth state, then sends the authorization code to the OpenBao OAuth plugin. The plugin exchanges the code and stores the resulting OAuth credential in OpenBao.

OAuth tokens are therefore never persisted by the application itself.

## 3. Asynchronous Credential Retrieval

Credential retrieval uses:

`GET /{provider}/{user}`

The endpoint immediately creates a request ID and returns:

* HTTP `202`
* request ID
* `Location: /requests/{id}`

The actual credential retrieval runs as a background task.

The caller polls:

`GET /requests/{id}`

The background task asks OpenBao for the credential and stores the request status in application memory.

This keeps the HTTP request asynchronous while allowing the caller to retrieve the result later.

## 4. Secret Handling

OpenBao is the source of truth for:

* provider client secrets
* OAuth access tokens
* OAuth credential data

The application does not write these secrets to disk or a database.

The service token used to access OpenBao is provided to the Kubernetes deployment through a Kubernetes Secret.

Secrets and tokens are not intentionally logged or returned by the health/status endpoints.

## 5. Scaling Considerations

The current implementation uses in-memory dictionaries for:

* OAuth state
* asynchronous request status

Therefore the deployment is intentionally configured with a single replica.

With multiple replicas, a request could be created on one pod and its polling request could reach another pod. The second pod would not have the request state because the state is stored only in the first pod's memory. OAuth callbacks could have the same problem if the callback reaches a different replica from the one holding the OAuth state.

To support multiple replicas, the transient state would need to be moved to a shared store such as Redis, or the application would need another shared state mechanism. Kubernetes service routing alone does not solve this problem.

OpenBao remains the persistent credential store regardless of the number of application replicas.

## 6. Deployment

`make up` performs the deployment workflow:

1. Starts Minikube when required.
2. Adds/updates the OpenBao Helm repository.
3. Installs or upgrades OpenBao.
4. Waits for OpenBao to become ready.
5. Installs and registers the OAuth plugin.
6. Enables the OAuth secrets engine.
7. Applies the least-privilege policy.
8. Creates or reuses the application OpenBao service token.
9. Installs or upgrades the Integration Aggregator Helm release.
10. Waits for the application deployment to become ready.

`make down` removes the application and OpenBao Helm releases.

The setup operations are designed to be repeatable so running `make up` again does not require manual OpenBao configuration.

## 7. CI/CD

GitHub Actions runs on every push.

The pipeline:

1. Runs unit tests.
2. Builds the container image.
3. Publishes the image to GHCR.
4. Starts Minikube.
5. Deploys the application and OpenBao using `make up`.
6. Runs health/readiness smoke tests.
7. Runs the performance benchmark at multiple concurrency levels.
8. Uploads the performance report as a CI artifact.
9. Packages and publishes the Helm chart to GHCR.

The published container image and Helm chart allow the deployment to be reproduced from CI artifacts rather than relying on local Docker images.

## 8. Performance

The benchmark exercises the health endpoint using concurrency levels of 1, 5, and 10.

For each level it records:

* p50 latency
* p95 latency
* throughput in requests per second

The resulting Markdown report is uploaded as a GitHub Actions artifact for the CI run.
