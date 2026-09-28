.PHONY: up down

RELEASE := integration-aggregator
CHART := ./chart/integration-aggregator

ifeq ($(OS),Windows_NT)
	BASH := C:/Program Files/Git/bin/bash.exe
	NULL := NUL
else
	BASH := bash
	NULL := /dev/null
endif

up:
	@echo "Starting Minikube..."
	@minikube status >$(NULL) 2>&1 || minikube start --driver=docker

	@echo "Adding OpenBao Helm repository..."
	@helm repo add openbao https://openbao.github.io/openbao-helm --force-update
	@helm repo update

	@echo "Installing/upgrading OpenBao..."
	@helm upgrade --install openbao openbao/openbao \
		-f ./deploy/openbao-values.yaml

	@echo "Waiting for OpenBao..."
	@kubectl wait --for=condition=Ready pod/openbao-0 --timeout=180s

	@echo "Configuring OpenBao..."
	@"$(BASH)" ./scripts/setup-openbao.sh

	@echo "Installing/upgrading Integration Aggregator..."
	@helm upgrade --install $(RELEASE) $(CHART)

	@echo "Waiting for Integration Aggregator..."
	@kubectl rollout status deployment/$(RELEASE) --timeout=180s

	@echo "Application is ready."

down:
	@echo "Removing Integration Aggregator..."
	@helm uninstall $(RELEASE) >$(NULL) 2>&1 || true

	@echo "Removing OpenBao..."
	@helm uninstall openbao >$(NULL) 2>&1 || true

	@echo "Done."