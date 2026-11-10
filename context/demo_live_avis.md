# Spec — Démo live « enquête de satisfaction vocale »

Hackathon gestion des flux touristiques (Isère). Démo jouée en live sur **un laptop**
(micro intégré, CPU seul), projeté sur grand écran en **2 colonnes** : « Backend » et
« Frontend » (mockup téléphone). Statut : **POC** (règlement Art. 3.1).

**Récit** : une *borne de captation du ressenti* des visiteurs, par leur expression vocale
directe, posée près de zones d'intérêt touristique en Isère : espaces naturels plus ou moins
sensibles, idéalement avec une source d'alimentation électrique pour l'autonomie de la borne
(par exemple à côté d'un parking), et près d'éco-compteurs existants, pour croiser la donnée
qualitative recueillie avec les données quantitatives de fréquentation. Pas de décision de
gestion à ce stade : de l'information pour les visiteurs et les décideurs publics.

## 1. Périmètre

| Dans le périmètre | Hors périmètre |
|---|---|
| STT local, live, sur CPU | Vraie app mobile / vraie PWA installable |
| Classification via Jev (OpenRouter) | Fallback hors-ligne (risque réseau accepté) |
| SQLite locale | Multi-utilisateur, auth, déploiement |
| Géolocalisation fictive : 5 bornes près des parkings d'ENS équipés d'éco-compteurs (§5) | GPS réel |
| Streamlit 2 colonnes | Texte libre généré (suggestions) : Jev ne génère pas de texte |
| | Signal / décision de gestion (v2) |

### MVP (chemin critique) vs stretch

Tout ce qui n'est pas MVP est **coupable sans regret** si le MVP n'est pas fini.

| MVP (à faire en premier, bout en bout) | Stretch (dans cet ordre) |
|---|---|
| Push-to-talk → STT → avis en base → classif Jev | 1. Partiels live (VAD + retranscription du chunk en cours) |
| Critères (§4) : satisfaction globale 0..100, affluence ressentie 0..100, provenance (département / hors département), moyen de transport si mention explicite, profil si explicite | 2. Navigation historique ◀ / ▶ |
| Vue carte « demi-journée en cours » : 1 point par borne | 3. Toggle « Tout le passé » |
| Fréquentation mesurée = éco-compteur proche de la borne (§6) | 4. Source `app` (jitter autour de la borne) |

## 2. Architecture

Deux processus Python sur le laptop, qui communiquent **uniquement via SQLite** (mode WAL).

```
 ┌──────────────── worker.py ────────────────┐        ┌──────────── app.py (Streamlit) ────────────┐
 │ micro (sounddevice 16 kHz mono)           │        │ Col. gauche « Backend »                    │
 │  → VAD (silero) → chunks                  │        │  - bouton push-to-talk + sélecteur borne   │
 │  → faster-whisper (CPU int8)              │◄──────►│  - transcription live (partiel + validé)   │
 │  → live_state (partiel/validé)            │ SQLite │  - N dernières lignes de `avis`            │
 │ au stop : INSERT avis (pending)           │  WAL   │ Col. droite « Frontend » (mockup tél.)     │
 │  → Jev (OpenRouter) → UPDATE avis (ok)    │        │  - carte des bornes :                      │
 │                                           │        │    taille = fréquentation (éco-compteur)   │
 │                                           │        │    couleur = score du critère choisi       │
 └───────────────────────────────────────────┘        └────────────────────────────────────────────┘
```

Pourquoi un worker séparé : Streamlit relance le script à chaque interaction et
par session, donc un thread micro hébergé dans Streamlit est fragile. Le bouton UI
écrit une commande dans la table `control`, que le worker lit environ toutes les 100 ms.

**Invariants du couplage UI ↔ worker** (testés) :
1. Le worker consomme les commandes **dans l'ordre d'`id`** et les marque `consumed=1`
   immédiatement. Un `start` reçu pendant un enregistrement est consommé et ignoré ; un
   `stop` reçu hors enregistrement aussi.
2. **Arrêt automatique** : sans parole détectée par la VAD pendant **`SILENCE_STOP_S` = 15 s**,
   le worker termine l'enregistrement comme sur un `stop` (oubli du bouton, visiteur parti).
   Durée maximale d'un enregistrement : `MAX_DUREE_S` = 120 s.
3. `live_state.status` suit le cycle `idle → recording → transcribing → classifying → idle`,
   sans saut en arrière au sein d'un enregistrement.
4. **Au démarrage**, le worker remet `live_state` à `idle`, marque toutes les commandes
   non consommées comme consommées (commandes périmées), et passe les avis `pending`
   restés orphelins en `error` (re-classifiables).
5. `live_state.updated_at` est rafraîchi au moins toutes les 2 s par le worker
   (heartbeat). Si l'UI voit un heartbeat de plus de 5 s → bandeau « worker arrêté ».

## 3. Speech-to-text (worker)

- **Modèle** : `faster-whisper` `small` **multilingue**, `device="cpu"`, `compute_type="int8"`.
  Repli sur `base` selon le benchmark du jour 1 (voir §10) : critère **mesurable** =
  temps de transcription d'un chunk de 3 s < 3 s sur le laptop de démo, chiffres
  `small` et `base` notés dans `demo/BENCH.md`.
- **Langue** : détection automatique, **verrouillée par enregistrement** dès le premier chunk
  de 3 s ou plus, pour éviter les bascules de langue entre partiels. Stockée dans `avis.langue`.
- **Live** (stretch 1) : la VAD découpe l'audio sur les pauses.
  - Chunk terminé : transcrit une fois et ajouté au texte **validé**.
  - Chunk en cours : retranscrit toutes les ~2 s, ce qui donne le texte **partiel** (affiché en gris).
  - Sans le stretch : l'enregistrement est transcrit une fois au stop.
- **Fin d'enregistrement** : bouton stop, ou arrêt automatique après 15 s de silence (§2).
  Transcription finale = concaténation des chunks validés, plus le dernier chunk. Pas de
  seconde passe complète, pour garder une latence courte au stop.
- **Unité** : push-to-talk. 1 enregistrement = 1 conversation en open mic = 1 avis.
- **Audio** : jamais écrit sur disque (buffers en mémoire, libérés après transcription).

## 4. Classification — Jev (`typesafe/jev-1.14`, via OpenRouter)

- Clé : variable d'environnement `OPENROUTER_API_KEY`. Modèle épinglé `typesafe/jev-1.14`
  (pas l'alias `latest`, pour que la démo reste reproductible).
- **Un seul appel** `POST /api/alpha/decisions` par avis, avec toutes les questions
  ci-dessous. ⚠️ À vérifier au jour 1 : forme exacte de la requête et de la réponse, et
  possibilité de mettre plusieurs questions dans un appel. Si ce n'est pas possible :
  appels en parallèle (go/no-go §10).
- **State** envoyé : le transcript final, plus le contexte (borne, langue).
- **Règle « missing data »** — s'applique à **toutes** les colonnes, `satisfaction` comprise :
  - dès qu'une variable a un score de confiance trop faible (< `SEUIL_CONFIANCE`, paramètre
    fixé au jour 1 sur quelques avis réels) → donnée **NULL** ;
  - la réponse brute de Jev (probabilités et confiance) est toujours stockée dans `jev_raw`.

| Colonne | Primitive | Options / échelle | Définition donnée à Jev |
|---|---|---|---|
| `satisfaction` | Score | 0 → 100 (float) | satisfaction globale exprimée dans la conversation |
| `affluence` | Score | 0 → 100 (float) | affluence ressentie : 0 = personne, 100 = « beaucoup trop de monde » |
| `provenance` | Choice | departement, hors_departement | le visiteur habite-t-il dans le département (Isère) ou en dehors ? |
| `transport` | Choice | voiture, transport_en_commun, velo | moyen de transport, **uniquement si mention explicite, pas de déduction**. Exemples : « le parking est plein » → voiture ; « pas pratique pour les vélos » → velo ; « les horaires des bus ne sont pas pratiques » → transport_en_commun |
| `profil` | Choice | groupe_amis, famille, seul, couple | composition du groupe, **uniquement si explicite** |

- **Statut** : l'avis est inséré `classif_status='pending'` dès le stop (il s'affiche
  immédiatement), puis passe à `ok` ou `error`. Si `error` : bouton « Re-classifier » dans la
  colonne Backend.

## 5. Géolocalisation fictive

Les bornes sont placées **d'après les données** : sur des Espaces Naturels Sensibles (ENS)
dont un **éco-compteur de parking** existe dans `données_eco_compteurs_ENS.xlsx`. Un parking
est aussi le lieu le plus probable d'une alimentation électrique pour la borne.

Avant chaque enregistrement, on choisit dans l'UI la **borne** (1 parmi 5). En stretch 4,
la **source** `app` tire un point aléatoire uniforme dans un disque de 2 km autour de la
borne (passage par l'app sur une rando voisine) ; par défaut, source `borne`.

Les bornes sont des **paramètres de démo** (données, pas logique), lus au démarrage depuis
`demo/bornes.yaml`. La logique est agnostique du territoire.

| id | Site ENS (`ID_ENS`) | Commune (`code_insee`) | Éco-compteur de référence | lat ≈ | lon ≈ |
|---|---|---|---|---|---|
| `bois_batie` | Bois de la Bâtie (SD11) | Saint-Ismier (38397) | `Bois de la Bâtie parking` | 45.2286 | 5.8422 |
| `col_coq` | Col du Coq (SD26) | Saint-Pierre-de-Chartreuse (38442) | `col du coq parking (chemin forestier)` | 45.3136 | 5.8322 |
| `ecouges` | Les Écouges (SD28) | Saint-Gervais (38390) | `ecouges pont chabert voiture` | 45.1880 | 5.5123 |
| `peuil` | Peuil (SD09) | Claix (38111) | `tourbière du peuil sentier parking` | 45.1221 | 5.6418 |
| `montfort` | Montfort (SD15) | Crolles (38140) | `Montfort voitures` | 45.2900 | 5.9021 |

- Coordonnées = **centroïde du site ENS** calculé depuis `Biodiversité/Habitats_naturels_ENS.gpkg`.
  ⚠️ À recaler sur le parking (OpenStreetMap) avant de les figer, et à vérifier : présence
  d'électricité, commune de rattachement (Écouges : Saint-Gervais / Rencurel ; Montfort :
  Crolles / Lumbin).
- `code_insee` vient de `Communes/Communes d'Isere.xlsx`.

## 6. Données de référence (fréquentation mesurée)

- **Source** : `data/ssp/` ou `../onyxia-data/`, selon le dossier présent (résolu au
  démarrage par `reference.py`, erreur explicite si aucun n'existe).
- **Série** : éco-compteur de parking de chaque borne (`Fréquentation/données_eco_compteurs_ENS.xlsx`),
  **mensuelle, 2004–2016**. Aucune série ne couvre la date de la démo : on ne fabrique pas
  de chiffres, on prend la **moyenne du même mois calendaire** sur les années disponibles,
  ramenée à une demi-journée (÷ jours du mois ÷ 2). Respecter les colonnes « à diviser par 2 ».
- **Règle d'honnêteté** : la valeur affichée porte un badge **« simulé »** et cite le compteur
  et la période source.
- Le chargement passe par un module partagé (`reference.py`) plutôt que de recopier les
  séries dans le code de démo.

## 7. Base de données (SQLite, `data/demo.db`, gitignorée)

```sql
PRAGMA journal_mode = WAL;

CREATE TABLE avis (
  id             INTEGER PRIMARY KEY,
  event_ts       TEXT NOT NULL,          -- ISO 8601 UTC ; horloge réelle ou date simulée (DEMO_PREP)
  demi_journee   TEXT NOT NULL,          -- ex. '2026-11-09_matin'
  borne_id       TEXT NOT NULL,
  lat            REAL NOT NULL,
  lon            REAL NOT NULL,
  transcript     TEXT NOT NULL,
  langue         TEXT,
  satisfaction   REAL CHECK (satisfaction BETWEEN 0 AND 100),  -- NULL si confiance faible
  affluence      REAL CHECK (affluence BETWEEN 0 AND 100),
  provenance     TEXT,                   -- departement | hors_departement | NULL
  transport      TEXT,                   -- voiture | transport_en_commun | velo | NULL
  profil         TEXT,                   -- groupe_amis | famille | seul | couple | NULL
  classif_status TEXT NOT NULL CHECK (classif_status IN ('pending','ok','error')),
  jev_raw        TEXT,                   -- JSON brut de la réponse Jev
  is_init        INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE live_state (               -- 1 seule ligne, id = 1
  id INTEGER PRIMARY KEY CHECK (id = 1),
  status TEXT,                          -- idle | recording | transcribing | classifying
  committed_text TEXT, partial_text TEXT,
  updated_at TEXT                       -- heartbeat worker
);

CREATE TABLE control (                  -- commandes UI → worker
  id INTEGER PRIMARY KEY,
  cmd TEXT CHECK (cmd IN ('start','stop')),
  borne_id TEXT, event_ts_override TEXT,
  consumed INTEGER DEFAULT 0
);
```

## 8. Demi-journées

- Fuseau **Europe/Paris** (calcul fait en heure locale, puis stocké).
- `heure < 13 → matin`, sinon `après-midi` (0h–6h rattaché au matin, 20h–24h à l'après-midi).
- `periods.demi_journee(ts) -> str` est **totale**, ce qui garantit le `NOT NULL`. Cas de test
  figés : `00:00`, `05:59`, `12:59 → matin` ; `13:00`, `19:59`, `20:00`, `23:59 → après-midi` ;
  plus un passage heure d'été / heure d'hiver.
- Un `event_ts` **dans le futur** est refusé à l'insertion (erreur explicite).
- **Initialisation** : avant la démo, l'équipe enregistre quelques avis réels (`is_init=1`).
  Le **mode préparation** n'existe que si l'app est lancée avec `DEMO_PREP=1` : il ajoute un
  champ « date simulée » qui remplit `event_ts` pour peupler des demi-journées passées.
  Impossible à déclencher par erreur pendant le show. Pas de données synthétiques d'avis.

## 9. Front-end (Streamlit, page unique `layout="wide"`)

**Rafraîchissement** : `st.fragment(run_every=1s)` sur les zones live.

### Colonne gauche — « Backend »
1. Sélecteur borne, bouton **● Enregistrer / ■ Stop**.
2. Transcription live : statut du worker (bandeau si heartbeat perdu, indication de l'arrêt
   automatique), texte validé (noir) + partiel (gris), langue détectée.
3. **Dernières lignes** de `avis` (10 par défaut) : heure, borne, transcript tronqué,
   colonnes de classif (NULL affichés `—`), statut, `jev_raw` dépliable, bouton supprimer.

### Colonne droite — « Frontend » (mockup téléphone)
Conteneur Streamlit à clé (`st.container(key="phone")`), mis en forme en CSS (classe
`.st-key-phone`) comme un cadre de téléphone d'environ 390 px.

1. **Carte (pydeck)** : un point par borne.
   - **Taille** = fréquentation quantitative de la demi-journée (éco-compteur, §6, badge « simulé »).
   - **Couleur** = score du critère choisi, sur les avis non-NULL de la fenêtre :
     satisfaction globale moyenne, affluence ressentie moyenne, ou part de visiteurs
     hors département (vs. dans le département). Borne sans avis → gris.
   - Clic / survol : nombre d'avis, valeur du critère, fréquentation et sa source.
2. **Sélecteur de critère** (satisfaction / affluence / provenance), avec légende de couleur.
3. **Fenêtre** : demi-journée en cours, live (défaut). Stretch 2 : ◀ / ▶ et badge
   « Historique ». Stretch 3 : « Tout le passé ».
4. Pied de mockup, texte fixe : *« Démo POC — avis anonymisés, enregistrement audio non
   conservé. »*

## 10. Risques, vérifications au jour 1 et go/no-go

| Risque | Vérification | Go/no-go |
|---|---|---|
| Format exact de l'API Jev, multi-questions | Premier appel curl réel, puis figer `jev.py` | Multi-questions non dispo à **J1 15h** → appels parallèles, 1 par critère |
| Confiance Jev non exploitable pour le seuil NULL | Lire `jev_raw` sur 10 avis réels | Pas de confiance utilisable → NULL seulement si la valeur est absente de la réponse |
| Réseau de la salle (risque accepté) | Partage 4G prêt | Avis conservé en `error` + bouton « Re-classifier » |
| Latence STT `small` sur le CPU du laptop de démo | Benchmark chunk 3 s, `small` et `base`, chiffres dans `BENCH.md` | > 3 s → `base` ; `base` > 3 s → abandon des partiels |
| Partiels live non stables à **J1 soir** | — | Coupe du stretch 1 |
| Arrêt auto déclenché à tort (bruit de salle) | Test en salle | Ajuster le seuil VAD / `SILENCE_STOP_S` |
| Permission micro / mauvais périphérique | `sounddevice.query_devices()` au lancement, device configurable | — |
| Coordonnées / électricité des bornes | Vérifier sur OSM | — |
| Colonnes éco-compteurs mal lues | Charger les 5 compteurs dans `reference.py` à J1 | Échec à **J1 18h** → valeur fixe par borne, badge « simulé » |

**Répétitions** : deux dry runs complets à J2, un sur le laptop de démo, un en conditions
de salle (projecteur, réseau de la salle), chacun contre la Définition de fait (§13).

## 11. Éthique & données (RGPD)

- **Voix de l'équipe uniquement** pendant la démo. Pas de captation de tiers (salle, jury)
  sans consentement explicite affiché à l'écran au préalable.
- **Audio brut jamais persisté** : seul le `transcript` est stocké.
- **Minimisation** : `provenance` binaire département ou hors département.
  `profil` est une inférence : affiché uniquement en **agrégat**, jamais par personne dans
  le Frontend.
- `data/demo.db` **gitignorée**. Avis supprimables (bouton dans la colonne Backend), et
  **suppression du fichier en fin de hackathon** (`rm data/demo.db`).

## 12. Chemin de mise à l'échelle (récit de pitch, pas de code)

1. **POC** (cette démo) : 1 laptop = 1 borne simulée, 5 sites ENS paramétrés dans `bornes.yaml`.
2. **Pilote** : 1 borne physique sur un parking d'ENS équipé d'un éco-compteur et alimenté
   électriquement, même schéma de base.
3. **Production** : bornes sur les ENS équipés d'éco-compteurs, croisement en continu avec
   les comptages, information diffusée aux visiteurs et aux décideurs publics. Un autre
   département = un autre `bornes.yaml` et un autre jeu de compteurs.

## 13. Définition de fait

| Critère | Vérifiable |
|---|---|
| Latence bout en bout | énoncé de 20 s → avis visible, classé, en < 10 s après le stop |
| Arrêt automatique | 15 s de silence → enregistrement terminé et avis créé |
| Partiels live (si stretch 1) | premier partiel affiché < 3 s après le début de la parole |
| Classification | ≥ 8 avis sur 10 classés `ok`, valeurs jugées correctes par l'équipe |
| No guess | un avis sans mention de transport → `transport` NULL, affiché `—` |
| Demi-journées | ≥ 2 demi-journées peuplées (matin + après-midi), dont 1 historique |
| Carte | les 5 bornes affichées, taille = éco-compteur (badge « simulé »), couleur = critère choisi |

## 14. Arborescence

```
demo/
  worker.py      # micro + VAD + STT + arrêt auto + appel Jev
  app.py         # Streamlit
  db.py          # schéma, connexion WAL, requêtes d'agrégat
  jev.py         # client HTTP Decisions API (effets de bord, mockable)
  mapping.py     # pur : questions Jev ↔ colonnes, réponse Jev → valeurs, seuil de confiance
  bornes.yaml    # paramètres de démo : 5 bornes ENS, code_insee, compteur de référence
  bornes.py      # chargement de bornes.yaml (+ jitter « app » en stretch)
  periods.py     # calcul demi_journee + navigation
  reference.py   # résolution data/ssp ou ../onyxia-data, fréquentation éco-compteurs (§6)
  tests/         # periods, mapping (réponse mockée), reference, agrégats, invariants §2
```
Lancement : `python demo/worker.py` et `streamlit run demo/app.py`
(`DEMO_PREP=1 streamlit run demo/app.py` pour la préparation).
Dépendances : `faster-whisper`, `sounddevice`, `numpy`, `pandas`, `openpyxl`, `pyyaml`,
`streamlit`, `pydeck`, `httpx`.
