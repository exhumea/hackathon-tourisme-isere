# Démo live : enquête de satisfaction vocale

Implémentation de la spec [`context/demo_live_avis.md`](../context/demo_live_avis.md).
Le micro du laptop alimente une transcription locale (faster-whisper, CPU). Chaque avis est
enregistré dans SQLite puis classifié par Jev (OpenRouter). L'écran Streamlit affiche deux
colonnes : « Backend » (STT + BDD) et « Frontend » (mockup téléphone).

## Installation (laptop de démo)

```bash
cd demo
uv sync                                   # Python ≥ 3.11
# Linux uniquement : PortAudio pour le micro (déjà inclus dans les wheels macOS/Windows)
sudo apt-get install -y libportaudio2
export OPENROUTER_API_KEY=sk-or-...       # clé OpenRouter (Jev est facturé à l'input)
```

**Avant le jour J, avec du réseau** : lancer une fois le worker ou le bench pour télécharger
le modèle dans `demo/models/` (~480 Mo pour `small`). Ensuite le chargement se fait hors
ligne. Seule la classification Jev a besoin du réseau.

## Lancement (2 terminaux)

```bash
uv run python worker.py                   # micro + STT + Jev   (--model base si le bench est trop lent)
uv run streamlit run app.py               # écran du show       (http://localhost:8501)
```

1. Choisir la **borne** et la **source** (borne = coordonnées exactes, app = point aléatoire ≤ 2 km).
2. **● Enregistrer**, laisser la conversation se dérouler, puis **■ Stop**. 1 enregistrement = 1 avis.
3. L'avis apparaît en base (`⏳ Jev…`), puis il est classifié (`✅ ok`). En cas d'échec réseau
   (`⚠️ erreur`), cliquer sur **Re-classifier #id**.

Côté téléphone :
- choisir un critère ;
- ◀ ▶ pour naviguer entre les demi-journées (matin 6h-13h, après-midi 13h-20h, heure de Paris ;
  hors plage, l'avis est rattaché au même jour) ;
- **● Live** pour revenir à la demi-journée en cours ;
- **Tout le passé** pour l'agrégat global.

## Préparation de la base

Activer **Mode préparation** dans la sidebar, à masquer pendant le show. Les avis enregistrés
sont alors marqués `is_init=1`, et **Date simulée** permet de les placer sur des demi-journées
passées. La base se trouve dans `demo/data/demo.db`. Pour repartir de zéro, supprimer
`demo/data/`.

## Options utiles

| Besoin | Commande |
|---|---|
| Choisir le micro | `uv run python worker.py --list-devices`, puis `--device <index>` |
| Mesurer la latence STT sur le laptop | `uv run python bench.py un_enregistrement.wav --models base small` |
| Répéter sans micro | `uv run python worker.py --simulate a.wav b.wav` (un fichier rejoué par enregistrement) |
| Autre base | `DEMO_DB=/chemin/demo.db` (pour les deux processus) |
| Langues candidates / défaut | `DEMO_LANGS=fr,en,de,it,nl,es`, `DEMO_DEFAULT_LANG=fr`, `DEMO_LANG_MIN_PROB=0.5` |
| Modèle Jev | `JEV_MODEL=typesafe/jev-1.13` (défaut), `JEV_TIMEOUT_S=20` |

## Fonctionnement du STT live

- La **langue** est détectée une seule fois par enregistrement, dès 3 s d'audio, parmi les
  langues candidates. Une langue autre que le français n'est retenue que si sa probabilité
  atteint au moins 0,5 : sans ce garde-fou, un français mal détecté serait *traduit* en anglais
  par Whisper.
- La **VAD** (silero) découpe l'audio sur les pauses (≥ 700 ms). Un chunk clos est transcrit
  une seule fois (texte validé, en noir). Le chunk en cours est retranscrit toutes les ~2 s
  (texte partiel, en gris).
- **Au plus une passe d'encodeur Whisper par tick.** Le décodage est borné
  (`temperature=0`, plafond de tokens proportionnel à la durée), pour qu'une hallucination ne
  puisse pas bloquer le live.
- Au **stop**, seul le dernier chunk est transcrit. Le transcript final est la concaténation des
  chunks.

## Tests

```bash
uv run pytest -q
```

Les tests couvrent les demi-journées (fuseau, heure d'été), les bornes et le jitter, le mapping
Jev (NULL, refus, score → note), la base et les agrégats, le worker de bout en bout (faux STT et
faux Jev : chunks, partiels, silence, erreur puis re-classification), ainsi qu'un smoke test de
l'app (`AppTest`) sur tous les critères et la navigation.

## Checklist jour 1

- [ ] `bench.py` sur le laptop avec une vraie voix. Viser un chunk de 5 s en ≤ 1,5 s ; sinon `--model base`.
- [ ] Premier appel Jev réel : vérifier `jev_raw` (toggle « Afficher la réponse brute Jev ») et le modèle effectivement servi.
- [ ] Micro : `--list-devices`, puis tester en salle (bruit, distance).
- [ ] Modèle déjà téléchargé ; tester avec le Wi-Fi coupé (le STT doit marcher, Jev passe en erreur).
- [ ] Partage de connexion 4G prêt.
