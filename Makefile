.DEFAULT_GOAL := help

UV := uv
UV_RUN := $(UV) run --all-packages

# Fichiers suivis et nouveaux fichiers non ignorés (les sous-modules ne sont
# pas parcourus par `git ls-files`).
GIT_FILES := git ls-files -z --cached --others --exclude-standard

# Ne garde que les fichiers réellement présents (un fichier supprimé mais encore
# suivi ne doit pas être passé aux linters).
YAML_FILES := $(shell $(GIT_FILES) '*.yaml' '*.yml' | xargs -0 sh -c 'for f do [ -f "$$f" ] && printf "%s\n" "$$f"; done' sh)
MARKDOWN_FILES := $(shell $(GIT_FILES) '*.md' ':!slidev/' | xargs -0 sh -c 'for f do [ -f "$$f" ] && printf "%s\n" "$$f"; done' sh)
SHELL_FILES := $(shell $(GIT_FILES) '*.sh' | xargs -0 sh -c 'for f do [ -f "$$f" ] && printf "%s\n" "$$f"; done' sh)

# diff-cover : branche de référence et seuil de couverture des lignes modifiées.
# Le seuil est à 0 pour l'instant (baseline) ; le remonter progressivement.
DIFF_COVER_BASE ?= origin/main
DIFF_COVER_FAIL_UNDER ?= 0

.PHONY: help setup check lint test format hooks pre-commit clean \
	check-ruff check-mypy check-pytest check-yamllint check-markdown check-shell check-shfmt \
	check-deptry check-import-linter check-complexipy check-actionlint \
	check-validate-pyproject check-jscpd check-licensecheck check-diff-cover check-lychee \
	mdlint deptry import-linter complexipy actionlint validate-pyproject jscpd \
	licensecheck diff-cover lychee shfmt

help: ## Affiche cette aide
	@echo "Cibles disponibles :"
	@echo "  make setup        Installe l'environnement Python (uv, >= 3.12)"
	@echo "  make check        Lance tous les contrôles (lint, types, tests)"
	@echo "  make lint         Lance les linters (sans les tests)"
	@echo "  make test         Lance les tests unitaires"
	@echo "  make mdlint       Lint des fichiers Markdown (mdlint)"
	@echo "  make shfmt        Formatage des scripts shell (shfmt)"
	@echo "  make deptry       Vérifie les dépendances déclarées (deptry)"
	@echo "  make import-linter Vérifie les règles d'import (import-linter)"
	@echo "  make complexipy   Complexité cognitive (complexipy)"
	@echo "  make actionlint   Lint des workflows GitHub Actions"
	@echo "  make validate-pyproject Valide les pyproject.toml"
	@echo "  make jscpd        Détection de code dupliqué (jscpd)"
	@echo "  make licensecheck Licences des dépendances (licensecheck)"
	@echo "  make diff-cover   Couverture des lignes modifiées (diff-cover)"
	@echo "  make lychee       Vérification des liens (lychee)"
	@echo "  make format       Formate le code Python avec ruff"
	@echo "  make hooks        Installe les hooks pre-commit"
	@echo "  make pre-commit   Lance pre-commit sur tous les fichiers"
	@echo "  make clean        Supprime les caches et l'environnement virtuel"

setup: ## Installe l'environnement Python
	$(UV) sync --all-packages --all-groups

check: check-ruff check-mypy check-yamllint check-markdown check-shell check-shfmt check-deptry check-import-linter check-complexipy check-actionlint check-validate-pyproject check-jscpd check-licensecheck check-pytest check-diff-cover check-lychee ## Tous les contrôles

lint: check-ruff check-mypy check-yamllint check-markdown check-shell check-shfmt check-deptry check-import-linter check-complexipy check-actionlint check-validate-pyproject check-jscpd check-licensecheck check-lychee ## Linters uniquement

check-ruff: ## Ruff (lint + format)
	$(UV_RUN) ruff check .
	$(UV_RUN) ruff format --check .

check-mypy: ## Vérification des types
	$(UV_RUN) mypy .

check-yamllint: ## Lint des fichiers YAML
	$(UV_RUN) yamllint -c .yamllint.yaml $(YAML_FILES)

check-markdown: ## Lint des fichiers Markdown
	$(UV_RUN) mdlint check --config .mdlint.toml $(MARKDOWN_FILES)

mdlint: check-markdown ## Alias de check-markdown (mdlint)

check-shell: ## Lint des scripts shell
	$(UV_RUN) shellcheck $(SHELL_FILES)

check-shfmt: ## Formatage des scripts shell
	$(UV_RUN) shfmt -d -i 4 -kp -ci $(SHELL_FILES)

shfmt: check-shfmt ## Alias de check-shfmt

check-deptry: ## Vérifie les dépendances déclarées
	cd datasets/sources_py && $(UV_RUN) deptry .

deptry: check-deptry ## Alias de check-deptry

check-import-linter: ## Vérifie les règles d'import
	cd datasets/sources_py && PYTHONPATH=src $(UV_RUN) lint-imports

import-linter: check-import-linter ## Alias de check-import-linter

check-complexipy: ## Complexité cognitive
	$(UV_RUN) complexipy

complexipy: check-complexipy ## Alias de check-complexipy

check-actionlint: ## Lint des workflows GitHub Actions
	$(UV_RUN) actionlint

actionlint: check-actionlint ## Alias de check-actionlint

check-validate-pyproject: ## Validation des fichiers pyproject.toml
	$(UV_RUN) validate-pyproject pyproject.toml datasets/sources_py/pyproject.toml

validate-pyproject: check-validate-pyproject ## Alias de check-validate-pyproject

check-jscpd: ## Détection de code dupliqué
	$(UV_RUN) jscpd datasets/sources_py/src

jscpd: check-jscpd ## Alias de check-jscpd

check-licensecheck: ## Compatibilité des licences des dépendances
	cd datasets/sources_py && $(UV_RUN) licensecheck

licensecheck: check-licensecheck ## Alias de check-licensecheck

check-diff-cover: ## Couverture des lignes modifiées
	@test -f coverage.xml || (echo "coverage.xml absent : lancez 'make test' d'abord" && exit 1)
	$(UV_RUN) diff-cover coverage.xml --compare-branch=$(DIFF_COVER_BASE) --fail-under=$(DIFF_COVER_FAIL_UNDER)

diff-cover: check-diff-cover ## Alias de check-diff-cover

check-lychee: ## Vérification des liens
	$(UV_RUN) lychee -vv --no-progress $(MARKDOWN_FILES)

lychee: check-lychee ## Alias de check-lychee

check-pytest: ## Tests unitaires
	$(UV_RUN) pytest

test: check-pytest ## Alias de check-pytest

format: ## Formate le code Python
	$(UV_RUN) ruff check --fix .
	$(UV_RUN) ruff format .

hooks: ## Installe les hooks pre-commit
	$(UV_RUN) pre-commit install --install-hooks

pre-commit: ## Lance pre-commit sur tous les fichiers
	$(UV_RUN) pre-commit run --all-files

clean: ## Nettoie les caches et l'environnement virtuel
	rm -rf .venv .mypy_cache .pytest_cache .ruff_cache .complexipy_cache
	rm -rf coverage.xml .coverage htmlcov .lycheecache jscpd-report
	find . -type d -name __pycache__ -not -path './.git/*' -not -path './sbx-kits-contrib/*' -prune -exec rm -rf {} +
