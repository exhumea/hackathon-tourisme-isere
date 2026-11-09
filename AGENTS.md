# AGENTS.md

Guide destiné aux agents qui travaillent dans ce dépôt. À lire avant toute
modification. Les documents de cadrage sont dans [`context/`](context/) :
commence par [`context/topo_prez.md`](context/topo_prez.md) (le cadre du
hackathon), puis [`context/reglement_hackathon.md`](context/reglement_hackathon.md)
(le règlement) et [`context/ideation_claude_pendant_prez.md`](context/ideation_claude_pendant_prez.md)
(les pistes et conventions techniques).

## 1. Contexte du projet

Hackathon DGE « Gestion des flux touristiques », les 9 et 10 novembre 2026,
avec l'Isère comme territoire d'application.

- **Objectif** : un POC open source qui améliore la mesure, la compréhension ou
  la gestion des flux touristiques, en croisant les données fournies et/ou
  d'autres données ouvertes.
- **Livrables** : code open source documenté (licence MIT ou Apache 2.0), une
  documentation technique et un pitch de 5 à 7 minutes.
- **Critères du jury** : aboutissement et qualité, inventivité, pertinence des
  données utilisées, bénéfices pour la gestion des flux, potentiel de mise à
  l'échelle.
- **Conséquences pour le code** : une démo qui tourne de bout en bout, les jeux
  de données fournis utilisés explicitement, et un code générique paramétré par
  département ou commune plutôt qu'en dur sur l'Isère.

## 2. Organisation du dépôt

| Chemin | Rôle |
|---|---|
| `context/` | Documents de cadrage, règlement, notes d'équipe et pistes de POC. |
| `datasets/sources_py/` | Scripts Python (`isere_tourism`) fournis pour interroger les API et préparer les données. |
| `datasets/sources_r/` | Sous-module des scripts R d'origine. Ne pas modifier sans raison. |
| `data/` | Données locales de travail. **Non versionnées** (sauf les README). |
| `sbx-kits-contrib/` | Sous-module d'outillage Docker sandbox. Ne pas modifier. |
| `.github/workflows/` | CI : revue de PR et contrôles qualité. |
| `Makefile`, `pyproject.toml`, `uv.lock` | Environnement Python et commandes de qualité. |
| `../onyxia-data/` | Données privées du hackathon, montées en lecture seule. Voir §6. |

## 3. Environnement et commandes

Le projet utilise **Python >= 3.12** et [`uv`](https://docs.astral.sh/uv/).
L'environnement est un workspace uv : le `pyproject.toml` racine porte les
outils de qualité, et `datasets/sources_py` est le projet Python applicatif.

```bash
make setup       # uv sync --all-packages --all-groups
make check       # tous les contrôles : lint, types, tests
make lint        # linters uniquement (sans pytest)
make test        # tests unitaires
make deptry      # dépendances déclarées (deptry)
make import-linter # règles d'import (import-linter)
make format      # ruff check --fix + ruff format
make hooks       # installe les hooks pre-commit
```

`make check` est la commande de référence avant tout commit ou PR. Elle lance :

- `ruff check` et `ruff format --check` (ligne max : **120** caractères) ;
- `mypy` sur `datasets/sources_py/src` et `datasets/sources_py/tests` ;
- `deptry` sur `datasets/sources_py` (dépendances déclarées mais inutilisées,
  imports non déclarés) ;
- `import-linter` sur le package `isere_tourism` (indépendance des modules) ;
- `pytest` (tests unitaires, sans appel réseau) ;
- `yamllint` sur les fichiers YAML (configuration permissive) ;
- `mdlint` sur les fichiers Markdown (configuration permissive) ;
- `shellcheck` sur les scripts shell.

Les commandes Python passent par `uv run --all-packages ...`. Ne pas créer
d'environnement virtuel manuellement : `uv` s'en charge.

## 4. Règles de code

Ces règles sont adaptées du skill [`karpathy-guidelines`](https://x.com/karpathy/status/2015883857489522876)
(voir aussi le skill `karpathy-guidelines` s'il est installé). Elles privilégient
la prudence sur la vitesse ; pour une tâche triviale, fais preuve de jugement.

### 4.1 Réfléchir avant de coder

- Énonce explicitement tes hypothèses. En cas de doute, demande.
- S'il existe plusieurs interprétations, présente-les au lieu d'en choisir une
  en silence.
- Si une approche plus simple existe, dis-le et argumente.
- Si quelque chose n'est pas clair, arrête-toi et nomme ce qui bloque.

### 4.2 Simplicité d'abord

- Le minimum de code qui résout le problème. Rien de spéculatif.
- Pas de fonctionnalité non demandée, pas d'abstraction pour un usage unique.
- Pas de « flexibilité » ou de « configurabilité » qui n'a pas été demandée.
- Pas de gestion d'erreur pour des scénarios impossibles.
- Si tu écris 200 lignes alors que 50 suffisent, réécris.

Demande-toi : « Un ingénieur senior trouverait-il cela trop compliqué ? »

### 4.3 Changements chirurgicaux

- Ne touche que ce qui est nécessaire. Ne « améliore » pas le code, les
  commentaires ou le formatage adjacents.
- Ne refactorise pas ce qui n'est pas cassé.
- Reprends le style existant, même si tu ferais autrement.
- Si tu remarques du code mort sans lien avec ta demande, mentionne-le sans le
  supprimer.
- Supprime uniquement les imports, variables ou fonctions que **tes** changements
  ont rendus inutiles.

Le test : chaque ligne modifiée doit se rattacher directement à la demande.

### 4.4 Exécution guidée par un objectif

Transforme la demande en objectif vérifiable :

- « Ajouter une validation » → « écrire les tests des entrées invalides, puis les
  faire passer » ;
- « Corriger le bug » → « écrire un test qui le reproduit, puis le faire passer » ;
- « Refactoriser X » → « les tests passent avant et après ».

Pour une tâche en plusieurs étapes, donne un plan court avec, pour chaque étape,
le critère de vérification.

## 5. Skills disponibles

- **`karpathy-guidelines`** : les règles ci-dessus, à charger si tu dois écrire,
  relire ou refactoriser du code.
- **`find-skills`** : skill de découverte et d'installation de skills. Utilise-le
  lorsqu'une tâche correspond à une capacité spécialisée qui pourrait déjà
  exister :

  ```bash
  npx skills find <mots-clés>
  npx skills add <owner/repo@skill> -g -y
  ```

  Avant de recommander un skill, vérifie le nombre d'installations, la source et
  la réputation du dépôt (voir <https://skills.sh/>). N'installe rien sans
  l'accord de l'utilisateur.

Les skills sont normalement installés côté humain via `npx skills` puis importés
dans le sandbox avec `sbx skills import`. La configuration du sandbox est
réservée aux humains (voir §10).

## 6. Données privées et secrets

- Le dossier **`../onyxia-data/`** contient les données privées du hackathon
  (classeurs, PDF, présentations, dossiers thématiques). Il est monté en lecture
  seule par `sbxenv.yaml`.
- **Ne jamais versionner ces données** ni les copier dans le dépôt. Elles peuvent
  en revanche être **mentionnées et documentées** dans le dépôt : chemin,
  description, schéma, mode d'accès. Le dépôt ne doit contenir que du code et de
  la documentation.
- `data/` et `.env` ne sont pas versionnés (voir `.gitignore`). Ne force jamais
  leur ajout avec `git add -f`.
- Les données fermées (par exemple Clearance ou les API sous clé) ne doivent pas
  être publiées dans le dépôt. Les clés d'API sont fournies dans le classeur
  Excel du SSP Cloud, jamais dans le code.
- En cas de doute sur une donnée : demande à l'utilisateur avant de l'ajouter.

## 7. Conventions de données

- **Clé pivot** : `code_insee` de la commune × `date`.
- Tables principales : `communes`, `sites`, `flux`, `meteo` (voir
  `datasets/sources_py/src/isere_tourism/`).
- Les données sont lues sur le bucket SSP Cloud du projet ; prévoir un repli sur
  des données fictives en local pour la démo.
- Pièges connus : granularités hétérogènes (commune/jour vs sentier/heure),
  doublons de sites entre DATAtourisme, Apidae et OSM, stations météo à apparier
  par altitude, pannes de compteurs (une absence de mesure n'est pas zéro
  visiteur), lignes de car scolaires absentes le week-end et pendant les
  vacances.

## 8. Tests et qualité

- Les tests unitaires ne font **aucun appel réseau**. Mocke les API ou teste des
  fonctions pures.
- Ajoute un test pour chaque bug corrigé et pour chaque fonctionnalité.
- Les modules de `isere_tourism` sont **indépendants** : ne pas importer un
  module du package depuis un autre. Si un code partagé devient nécessaire,
  crée un module utilitaire dédié et mets à jour le contrat `import-linter`.
- Toute dépendance importée doit être déclarée dans
  `datasets/sources_py/pyproject.toml` (`deptry` vérifie les imports non
  déclarés et les dépendances inutilisées).
- Avant de proposer une PR : `make check` doit passer, et les hooks
  `pre-commit` doivent être installés avec `make hooks`.
- La CI GitHub Actions (`.github/workflows/checks.yaml`) exécute `make check`
  sur Python 3.12.

## 9. Git et pull requests

- Travaille sur une branche dédiée, jamais directement sur `main`.
- Utilise des commits courts et explicites, de préférence au format
  conventionnel : `feat:`, `fix:`, `docs:`, `chore:`, `test:`.
- Ne commite ni données, ni secrets, ni `.venv`, ni caches.
- La description de PR doit rappeler le problème, la solution et les données
  utilisées. `make check` doit être vert.

## 10. Setup sandbox : humains uniquement

La section « Agentic setup with Docker sandboxes » du [`README.md`](README.md)
est **réservée aux humains**. Un agent ne doit pas lancer, modifier ou
contourner les scripts et fichiers de configuration du sandbox
(`sbxenv.yaml`, `new_opencode_sandbox.sh`, `pair_opencode_sandbox.sh`,
`sandbox-persistent.sh`, etc.).

Si une action nécessite l'hôte (publication de port, secret, authentification,
installation de skill), demande à l'utilisateur de l'exécuter.
