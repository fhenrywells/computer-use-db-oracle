SHELL := /bin/zsh

.PHONY: up down fmt

up:
	docker compose up -d

down:
	docker compose down

fmt:
	@echo "Add project-specific formatters as components are implemented."

