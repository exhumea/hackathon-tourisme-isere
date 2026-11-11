# Hackathon

## Qualité et développement

Le dépôt utilise Python >= 3.12 et [`uv`](https://docs.astral.sh/uv/). Les
contrôles de lint, de types et les tests se lancent depuis la racine :

```bash
make setup
make check
```

Les conventions de code, les commandes détaillées et les règles sur les données
privées sont dans [`AGENTS.md`](AGENTS.md). Les données du hackathon sont dans
`../onyxia-data/` (lecture seule, jamais versionnées).

## Agentic setup with Docker sandboxes (humans-only)

> [!IMPORTANT]
> The agentic setup below is **humans only**: an agent must not run it, change it,
> or any config file or script involved in this setup.
> Only a human operator provisions sandboxes and authenticates accounts.

Before starting you need to `sudo apt install ssh-agent-filter`

1. [Install `sbx`](https://docs.docker.com/ai/sandboxes/install/) and run `sbx login`

2. Install some skills with [`npx skills`](https://www.skills.sh/) and import them with `sbx skills import`

3. Store your secrets (API keys for model providers) with
[`sbx secret import` and/or `sbx secret set[-custom]`](https://docs.docker.com/ai/sandboxes/configuration/credentials/).
Some nice token providers are:
   - <https://lbrouter.com/#ref=GTXQQRLK> (nice free tier, per day)
   - <https://opencode.ai/console/login> (nice free tier, per day)
   - <https://tokenharbor.ai> (good free tier, 7d rolling)
   - <https://developer.amd.com.cn/radeon/tokenfactory> (free tier ~ OK, complex signup)
   - <https://openrouter.ai/> (free tier ~ OK)
   - <https://engy.ai/pricing> (very low cost)
   - <https://agentrouter.org> (175$ signup bonus, GPT 6.1 Sol)
   - <https://freepi.ai/?ref=q5jyhxvg> (free tier, complex setup)

4. [Authenticate with `gh` CLI](https://docs.github.com/github-cli/github-cli/quickstart)
for your human and agentic accounts, and `export GH_AGENT=<agent-username>` in your `~/.bashrc`
(note: you MUST have an SSH key for both
[authentication](https://docs.github.com/authentication/connecting-to-github-with-ssh)
and [signing](https://docs.github.com/authentication/managing-commit-signature-verification/telling-git-about-your-signing-key#telling-git-about-your-ssh-key), for both accounts)

5. `git submodule update --init`

6. Launch new OpenCode sandbox(es) with `./new_opencode_sandbox.sh`

7. Pair your sandbox with your OpenCode {[desktop](https://opencode.ai/desktop), [mobile](https://getopencode.app/), web} apps
**(beware pairing link is valid only once, run `./pair_opencode_sandbox.sh` to pair to another app)**

8. Start new _sessions_ in your OpenCode app **(beware to change the working directory before starting a _session_)**
