# Spec — Démo live « enquête de satisfaction vocale »

Hackathon gestion des flux touristiques (Isère). Démo jouée en live sur **un laptop**
(micro intégré, CPU seul), projeté sur grand écran en **2 colonnes** : « Backend » et
« Frontend » (mockup téléphone). Statut : **POC** (règlement Art. 3.1).

**Récit** : un *capteur de ressenti* vocal, posé sur des sites réels, dont le signal
(« trop de monde », « pas de parking »…) est **confronté aux flux mesurés** des jeux de
données fournis, et déclenche une **décision de gestion** (Plan B officiel, communication).

## 1. Périmètre

| Dans le périmètre | Hors périmètre |
|---|---|
| STT local, live, sur CPU | Vraie app mobile / vraie PWA installable |
| Classification via Jev (OpenRouter), repli local par mots-clés | Multi-utilisateur, auth, déploiement |
| SQLite locale | GPS réel |
| Géolocalisation fictive (5 bornes = sites réels, `code_insee`) | Texte libre généré (suggestions) : Jev ne génère pas de texte |
| Croisement ressenti × fréquentation mesurée (série réelle rejouée, badge « simulé ») | Couverture de tout le département |
| Streamlit 2 colonnes | |

### MVP (chemin critique) vs stretch

Tout ce qui n'est pas MVP est **coupable sans regret** si le MVP n'est pas fini.

| MVP (à faire en premier, bout en bout) | Stretch (dans cet ordre) |
|---|---|
| Push-to-talk → STT → avis en base → classif Jev | 1. Partiels live (VAD + retranscription du chunk en cours) |
| Critères : `note`, `profil`, `affluence`, `provenance` | 2. Critères fins (§4, `services`, `signaletique`, `parking`, `velo`, `nb_personnes`) |
| Vue « demi-journée en cours » + badge saturation | 3. Navigation historique ◀ / ▶ |
| Panneau « ressenti vs mesuré » (statique, 1 borne) | 4. Mini-carte pydeck (option « Carte des ressentis ») |
| Repli Jev local (`JEV_OFFLINE=1`) | 5. Toggle « Tout le passé », source `app` |

## 2. Cas d'usage / décision

Le logiciel ne fait pas qu'**afficher** des avis : il produit un **signal de gestion**.

- **Règle** : sur une borne et une demi-journée, si la part d'avis `affluence=saturee`
  (sur les non-NULL) dépasse **`SEUIL_SATURATION`** (paramètre, défaut 0,5) **et** qu'il y a
  au moins `MIN_AVIS` avis (défaut 3) → badge **« saturation »** sur la borne.
- **Action proposée** (texte fixe, pas généré) : « Activer le Plan B » → l'itinéraire bis
  officiel de la borne (colonne `Itinéraire Bis` de la liste des sites surfréquentés), ou
  « Communiquer » (message vers l'office de tourisme).
- Même logique pour les irritants d'infrastructure : part d'avis `parking=negatif` ou
  `signaletique=negatif` > seuil → signal « infra » (stretch).
- Ce sont des **seuils de POC**, pas une promesse de calibration.

## 3. Architecture

Deux processus Python sur le laptop, qui communiquent **uniquement via SQLite** (mode WAL).

```
 ┌──────────────── worker.py ────────────────┐        ┌──────────── app.py (Streamlit) ────────────┐
 │ micro (sounddevice 16 kHz mono)           │        │ Col. gauche « Backend »                    │
 │  → VAD (silero) → chunks                  │        │  - bouton push-to-talk + sélecteur borne   │
 │  → faster-whisper (CPU int8)              │◄──────►│  - transcription live (partiel + validé)   │
 │  → live_state (partiel/validé)            │ SQLite │  - N dernières lignes de `avis`            │
 │ au stop : INSERT avis (pending)           │  WAL   │ Col. droite « Frontend » (mockup tél.)     │
 │  → Jev (OpenRouter) → UPDATE avis (ok)    │        │  - critère + demi-journée + ressenti/mesuré│
 └───────────────────────────────────────────┘        └────────────────────────────────────────────┘
```

Pourquoi un worker séparé : Streamlit relance le script à chaque interaction et
par session, donc un thread micro hébergé dans Streamlit est fragile. Le bouton UI
écrit une commande dans la table `control`, que le worker lit environ toutes les 100 ms.

**Invariants du couplage UI ↔ worker** (testés) :
1. Le worker consomme les commandes **dans l'ordre d'`id`** et les marque `consumed=1`
   immédiatement. Un `start` reçu pendant un enregistrement est consommé et ignoré ; un
   `stop` reçu hors enregistrement aussi.
2. `live_state.status` suit le cycle `idle → recording → transcribing → classifying → idle`,
   sans saut en arrière au sein d'un enregistrement.
3. **Au démarrage**, le worker remet `live_state` à `idle`, marque toutes les commandes
   non consommées comme consommées (commandes périmées), et passe les avis `pending`
   restés orphelins en `error` (re-classifiables).
4. `live_state.updated_at` est rafraîchi au moins toutes les 2 s par le worker
   (heartbeat). Si l'UI voit un heartbeat de plus de 5 s → bandeau « worker arrêté ».
   Plus de blocage silencieux.

## 4. Speech-to-text (worker)

- **Modèle** : `faster-whisper` `small` **multilingue**, `device="cpu"`, `compute_type="int8"`.
  Repli sur `base` selon le benchmark du jour 1 (voir §12) : critère **mesurable** =
  temps de transcription d'un chunk de 3 s < 3 s sur le laptop de démo, chiffres
  `small` et `base` notés dans `demo/BENCH.md`.
- **Langue** : détection automatique, **verrouillée par enregistrement** dès le premier chunk
  de 3 s ou plus, pour éviter les bascules de langue entre partiels. Stockée dans `avis.langue`.
- **Live** (stretch 1) : la VAD découpe l'audio sur les pauses.
  - Chunk terminé : transcrit une fois et ajouté au texte **validé**.
  - Chunk en cours : retranscrit toutes les ~2 s, ce qui donne le texte **partiel** (affiché en gris).
  - Sans le stretch : enregistrement borné (max 60 s) transcrit une fois au stop.
- **Fin d'enregistrement** : transcription finale = concaténation des chunks validés, plus le
  dernier chunk. Pas de seconde passe complète, pour garder une latence courte au stop.
- **Unité** : push-to-talk. 1 enregistrement = 1 conversation en open mic = 1 avis.
- **Audio** : jamais écrit sur disque (buffers en mémoire, libérés après transcription).

## 5. Classification — Jev (`typesafe/jev-1.14`, via OpenRouter)

- Clé : variable d'environnement `OPENROUTER_API_KEY`. Modèle épinglé `typesafe/jev-1.14`
  (pas l'alias `latest`, pour que la démo reste reproductible).
- **Un seul appel** `POST /api/alpha/decisions` par avis, avec toutes les questions
  ci-dessous. ⚠️ À vérifier au jour 1 : forme exacte de la requête et de la réponse, et
  possibilité de mettre plusieurs questions dans un appel. Si ce n'est pas possible :
  appels en parallèle (go/no-go §12).
- **State** envoyé : le transcript final, plus le contexte (borne, langue).
- **Règle « missing data »** — s'applique à **toutes** les colonnes, `note` comprise :
  - chaque Choice contient l'option `non_mentionne` ; si elle gagne, la colonne vaut **NULL** ;
  - `note` est un Score, qui ne peut pas porter `non_mentionne` : elle est donc **conditionnée**
    par la Choice `satisfaction_exprimee`. Si `non`, `note` vaut **NULL** (on ne fabrique pas
    de note quand le visiteur n'a rien dit de sa satisfaction) ;
  - pas de seuil de confiance. La réponse brute de Jev (probabilités et confiance) est
    toujours stockée dans `jev_raw`.

### Critères MVP

| Colonne | Primitive | Options / échelle | Définition donnée à Jev |
|---|---|---|---|
| `profil` | Choice | touriste, excursionniste, local, non_mentionne | touriste = ≥ 1 nuit hors domicile ; excursionniste = venu à la journée sans nuitée ; local = habite à proximité |
| `origine` | Choice | isere, autre_france, etranger, non_mentionne | lieu de résidence (agrégat, utilisé si `provenance_*` est NULL) |
| `affluence` | Choice | faible, normale, saturee, non_mentionne | ressenti sur le nombre de personnes ; `saturee` = « trop de monde » |
| `satisfaction_exprimee` | Choice | oui, non | le visiteur exprime-t-il une satisfaction globale (positive ou négative) ? |
| `note` | Score | 1 → 5 | satisfaction globale, **uniquement si** `satisfaction_exprimee=oui`, sinon NULL. Valeur continue (position pondérée) |

**Provenance (code postal / ville)** — Jev ne génère pas de texte, donc ce n'est pas une
question Jev : `provenance_ville` et `provenance_cp` sont extraites du transcript par
**correspondance avec un référentiel de communes** (nom normalisé, code postal à 5 chiffres
si prononcé). Référentiel : liste des communes françaises (nom, CP, INSEE). Pas de
correspondance → NULL. `origine` (Jev) sert de repli agrégé.

### Critères fins (stretch 2)

| Colonne | Primitive | Options | Définition donnée à Jev |
|---|---|---|---|
| `nb_personnes` | Choice | 1, 2, 3_5, 6_plus, non_mentionne | taille du groupe |
| `groupe` | Choice | seul, couple, famille, amis, groupe_organise, non_mentionne | composition du groupe |
| `mode_venue` | Choice | voiture, transport_en_commun, velo, a_pied, autre, non_mentionne | mode d'accès au départ de la rando |
| `services` | Choice | positif, negatif, non_mentionne | services / état des infrastructures (toilettes, poubelles, entretien) |
| `signaletique` | Choice | positif, negatif, non_mentionne | balisage, panneaux, orientation |
| `parking` | Choice | positif, negatif, non_mentionne | parking : disponibilité, saturation, coût |
| `velo` | Choice | positif, negatif, non_mentionne | infrastructures vélo : pistes, stationnement |
| `revenir` | Choice | oui, non, non_mentionne | intention de revenir |

**v2 (hors démo)** : motivations de la visite (quali) ; lieu d'hébergement (nom d'hôtel) ;
autres sites visités et temps passé sur chaque site, y compris celui-ci. Ces champs
supposent de l'extraction de texte libre, que Jev ne fait pas.

### Statut et repli

- L'avis est inséré `classif_status='pending'` dès le stop (il s'affiche immédiatement),
  puis passe à `ok` ou `error`. Si `error` : bouton « Re-classifier » dans la colonne Backend.
- **Repli local** : `JEV_OFFLINE=1` (ou réseau en échec après 1 retry) → `classify_offline()`
  par **dictionnaire de mots-clés** (~20 lignes : « trop de monde » → `saturee`, « en train »,
  « bus » → `transport_en_commun`…). `jev_model='offline-keywords'`. Le but : que la démo
  tourne de bout en bout même sans réseau, pas de concurrencer Jev.

## 6. Géolocalisation fictive

Avant chaque enregistrement, on choisit dans l'UI :
- **borne** (1 parmi 5) ;
- **source** (stretch 5) : `borne` (coordonnées exactes de la borne) ou `app` (point
  aléatoire uniforme dans un disque de **2 km** autour de la borne, qui simule un passage par
  l'app sur une rando voisine).

Les bornes sont des **paramètres de démo** (données, pas logique), lus au démarrage depuis
`demo/bornes.yaml`. La logique (périodes, agrégats, classification, seuils) est
**agnostique du territoire** : changer de département = changer ce fichier.

| id | Départ | Massif | Commune (`code_insee`) | lat ≈ | lon ≈ |
|---|---|---|---|---|---|
| `chamrousse` | Lac Blanc / Chamrousse 1750 | Belledonne | Chamrousse (38567) | 45.11 | 5.88 |
| `col_porte` | Col de Porte | Chartreuse | Sarcenas (38472) | 45.29 | 5.77 |
| `moliere` | Plateau de la Molière | Vercors | Autrans-Méaudre en Vercors (38225) | 45.17 | 5.58 |
| `sept_laux` | Les 7 Laux (Prapoutel) | Belledonne | Les Adrets (38002) | 45.25 | 5.99 |
| `bourg_arud` | Bourg-d'Arud → Lac de la Muzelle | Oisans | Les Deux Alpes (38253) | 44.96 | 6.13 |

⚠️ Coordonnées et rattachement communal **approximatifs** (sites en limite de communes) : à
vérifier sur OpenStreetMap avant de les figer. `code_insee` vient de
`data/ssp/Communes/Communes d'Isere.xlsx`.

Chaque borne porte aussi dans `bornes.yaml` : `sat_officiel` (site de la liste des sites
surfréquentés), `plan_b` (itinéraire bis officiel), et `ref_frequentation` (série source
pour le panneau §9, ou `null`).

## 7. Données de référence (croisement ressenti × mesuré)

Constat : **aucune série quantitative fournie ne couvre la date de la démo** (9–10 nov.).
On ne fabrique pas de chiffres. On **rejoue la forme temporelle d'une série réelle** sur la
date du jour : profil horaire + jour de semaine, mis à l'échelle de la borne
(`pandas.resample` + facteur d'échelle, ~30 lignes, `demo/reference.py`).

| Usage | Source (`data/ssp/…`) | Nature | Traitement |
|---|---|---|---|
| « Fréquentation mesurée » par demi-journée | `Fréquentation/Freq parking des égauds.csv` (30 min, 2024–25, météo jointe) | réelle | profil journalier **rejoué** sur la date, ré-échelonné |
| Accès routier `sept_laux` | `Fréquentation/Comptage véhicules en stations 2023 Le Gresivaudan.xlsx` (postes D281 Prapoutel / D281A Pipay, horaire) | échantillon 9 jours | courbe type « montée en station », ré-échelonnée |
| Repère saisonnier (stretch) | lacs Murmuration (hebdo, piétinement) | réelle | **pas** de synthèse live ; repère statique |
| Plan B / site surfréquenté | liste des sites surfréquentés (`Itinéraire Bis`) | officielle | aucune synthèse, c'est la référence |

- **Règle d'honnêteté** : toute valeur rejouée porte un badge **« simulé »** et cite sa série
  source. Le jury doit voir que la *forme* est réelle, seules l'échelle et la date sont
  ré-ancrées.
- **Zone test MVP** : 1 borne avec référence (`chamrousse`). Les autres bornes ont
  `ref_frequentation: null` → le panneau affiche « pas de mesure de référence ».
- Le chargement passe par un module partagé (`reference.py`) plutôt que de recopier les
  séries dans le code de démo, pour que le futur worker de production lise la même source.

## 8. Base de données (SQLite, `data/demo.db`, gitignorée)

```sql
PRAGMA journal_mode = WAL;

CREATE TABLE avis (
  id             INTEGER PRIMARY KEY,
  created_at     TEXT NOT NULL,          -- ISO 8601, horloge réelle (UTC)
  event_ts       TEXT NOT NULL,          -- = created_at, ou date simulée (mode préparation)
  demi_journee   TEXT NOT NULL,          -- ex. '2026-11-09_matin', calculée depuis event_ts
  transcript     TEXT NOT NULL,
  langue         TEXT,
  duree_s        REAL,
  borne_id       TEXT NOT NULL,
  code_insee     TEXT NOT NULL,          -- recopié depuis bornes.yaml
  source         TEXT NOT NULL CHECK (source IN ('borne','app')),
  lat            REAL NOT NULL,
  lon            REAL NOT NULL,
  provenance_ville TEXT, provenance_cp TEXT,
  profil         TEXT, origine TEXT, affluence TEXT,
  satisfaction_exprimee TEXT,
  note           REAL CHECK (note BETWEEN 1 AND 5),   -- NULL si satisfaction_exprimee <> 'oui'
  nb_personnes   TEXT, groupe TEXT, mode_venue TEXT,
  services       TEXT, signaletique TEXT, parking TEXT, velo TEXT,
  revenir        TEXT,
  classif_status TEXT NOT NULL CHECK (classif_status IN ('pending','ok','error')),
  jev_model      TEXT,                   -- 'typesafe/jev-1.14' ou 'offline-keywords'
  jev_raw        TEXT,                   -- JSON brut de la réponse Jev
  is_init        INTEGER NOT NULL DEFAULT 0  -- avis d'initialisation enregistré par l'équipe
);
CREATE INDEX idx_avis_dj ON avis(demi_journee);

CREATE TABLE live_state (               -- 1 seule ligne, id = 1
  id INTEGER PRIMARY KEY CHECK (id = 1),
  status TEXT,                          -- idle | recording | transcribing | classifying
  committed_text TEXT, partial_text TEXT, langue TEXT,
  updated_at TEXT                       -- heartbeat worker (§3, invariant 4)
);

CREATE TABLE control (                  -- commandes UI → worker
  id INTEGER PRIMARY KEY, cmd TEXT CHECK (cmd IN ('start','stop')),
  borne_id TEXT, source TEXT, event_ts_override TEXT,
  created_at TEXT, consumed INTEGER DEFAULT 0
);
```

## 9. Demi-journées

- Fuseau **Europe/Paris** (calcul fait en heure locale, puis stocké).
- Plages nominales : **matin 6h–13h**, **après-midi 13h–20h**. Un avis hors plage est
  rattaché à la plage du **même jour** la plus proche : 0h–6h → matin, 20h–24h → après-midi.
  En pratique : `heure < 13 → matin`, sinon `après-midi`.
- `periods.demi_journee(ts) -> str` est **totale** (toute date valide a une demi-journée, y
  compris passée ou future), ce qui garantit le `NOT NULL`. Cas de test figés :
  `00:00 → matin`, `05:59 → matin`, `12:59 → matin`, `13:00 → après-midi`,
  `19:59 → après-midi`, `20:00 → après-midi`, `23:59 → après-midi`, plus un passage
  heure d'été / heure d'hiver (`ts` UTC converti en Europe/Paris).
- Un `event_ts` **dans le futur** est refusé à l'insertion (erreur explicite), car la vue
  « en cours » ne doit jamais afficher un avis à venir.
- **Initialisation** : avant la démo, l'équipe enregistre quelques avis réels (`is_init=1`).
  Le **mode préparation** n'est **pas** un toggle UI : il n'existe que si l'app est lancée
  avec `DEMO_PREP=1`. Il ajoute alors un champ « date simulée » qui remplit `event_ts` pour
  peupler des demi-journées passées. Impossible à déclencher par erreur pendant le show. Il
  n'y a pas de données synthétiques d'avis.

## 10. Front-end (Streamlit, page unique `layout="wide"`)

**Rafraîchissement** : `st.fragment(run_every=1s)` sur les zones live (transcription,
dernières lignes, viz si la fenêtre est la demi-journée en cours).

### Colonne gauche — « Backend »
1. Sélecteur borne (+ source en stretch), bouton **● Enregistrer / ■ Stop**.
2. Transcription live : statut du worker (bandeau si heartbeat perdu), texte validé (noir)
   + partiel (gris), langue détectée.
3. **Dernières lignes** de `avis` (10 par défaut) : heure, borne, transcript tronqué,
   colonnes de classif (NULL affichés `—`), statut, `jev_model`, `jev_raw` dépliable,
   bouton supprimer.

### Colonne droite — « Frontend » (mockup téléphone)
Conteneur Streamlit à clé (`st.container(key="phone")`), mis en forme en CSS (classe
`.st-key-phone`) comme un cadre de téléphone d'environ 390 px. Deux vues seulement :
**« Demi-journée en cours »** (live, défaut) et **« Historique »** (figée, stretch 3).

1. **Badge saturation** de la borne (§2) + action « Activer le Plan B » si déclenché.
2. **Panneau « ressenti vs mesuré »** : à gauche, part d'avis `saturee` (voix) ; à droite,
   fréquentation de référence de la même demi-journée (§7), badge « simulé » + source.
3. **Sélecteur de critère** :
   - Distribution des notes : histogramme de `round(note)` sur 1–5, moyenne sur la valeur
     continue, et nombre d'avis **sans note exprimée** affiché à part.
   - Touriste / excursionniste / local : proportions sur les non-NULL, « non mentionné » à part.
   - Provenance : top villes / départements (depuis `provenance_cp`), sinon `origine`.
   - Volume d'avis : total, par borne.
   - Stretch 2 — Infrastructures : `services`, `signaletique`, `parking`, `velo` en barres
     positif / négatif ; mode de venue.
4. **Navigation** (stretch 3) : ◀ / ▶ d'une demi-journée, badge « Historique », bouton « Live ».
   Toggle « Tout le passé » (stretch 5).
5. **Mini-carte** (stretch 4, pydeck) : option « Carte des ressentis » des maquettes de la
   PR — bornes, points des avis colorés par catégorie (saturé / irritant infra / positif).
6. Pied de mockup, texte fixe : *« Démo POC — avis anonymisés, enregistrement audio non
   conservé. »*

## 11. Éthique & données (RGPD)

- **Voix de l'équipe uniquement** pendant la démo. Pas de captation de tiers (salle, jury)
  sans consentement explicite affiché à l'écran au préalable.
- **Audio brut jamais persisté** : seul le `transcript` est stocké.
- **Minimisation** : `provenance` au niveau commune / CP, jamais d'adresse ; pas de nom.
  `profil` et `origine` sont des inférences : affichées uniquement en **agrégat**, jamais par
  personne dans le Frontend.
- `data/demo.db` **gitignorée**. Avis supprimables (bouton dans la colonne Backend), et
  **suppression du fichier en fin de hackathon** (`rm data/demo.db`, noté dans la checklist
  de clôture).
- Argument de pitch : voix agrégée et anonymisée = conformité by design, condition de la
  mise à l'échelle (§13).

## 12. Risques, vérifications au jour 1 et go/no-go

| Risque | Vérification | Go/no-go |
|---|---|---|
| Format exact de l'API Jev, multi-questions | Premier appel curl réel, puis figer `jev.py` | Multi-questions non dispo à **J1 15h** → appels parallèles, 1 par critère |
| Jev indisponible / réseau de salle | Partage 4G prêt ; `JEV_OFFLINE=1` testé | Jev KO à **J2 matin** → démo en `offline-keywords`, dit au jury |
| Latence STT `small` sur le CPU du laptop de démo | Benchmark chunk 3 s, `small` et `base`, chiffres dans `BENCH.md` | > 3 s → `base` ; `base` > 3 s → abandon des partiels (enregistrement borné) |
| Partiels live non stables à **J1 soir** | — | Coupe du stretch 1 |
| Bascule de langue auto sur des extraits courts | Langue verrouillée par enregistrement | — |
| Permission micro / mauvais périphérique | `sounddevice.query_devices()` au lancement, device configurable | — |
| Coordonnées / communes des bornes | Vérifier sur OSM | — |
| Série de référence illisible / mal datée | Charger Égauds dans `reference.py` à J1 | Échec à **J1 18h** → panneau mesuré statique (1 chiffre, badge « simulé ») |

**Répétitions** : deux dry runs complets à J2, un sur le laptop de démo, un en conditions
de salle (projecteur, réseau de la salle), chacun contre la Définition de fait (§14).

## 13. Chemin de mise à l'échelle (récit de pitch, pas de code)

1. **POC** (cette démo) : 1 laptop = 1 borne simulée, 5 sites paramétrés dans `bornes.yaml`.
2. **Pilote** : 1 borne physique sur un site surfréquenté (QR code / NFC vers une page web),
   un worker par borne, même schéma de base ; ou captation via l'app mobile (source `app`).
3. **Production** : bornes sur les sites de la liste des sites surfréquentés de l'Isère,
   croisement en continu avec Flux Vision / éco-compteurs, signal transmis aux gestionnaires.
   La logique étant agnostique du territoire, un autre département = un autre `bornes.yaml`
   et un autre référentiel de séries.

## 14. Définition de fait

| Critère | Vérifiable |
|---|---|
| Latence bout en bout | énoncé de 20 s → avis visible, classé, en < 10 s après le stop |
| Partiels live (si stretch 1) | premier partiel affiché < 3 s après le début de la parole |
| Classification | ≥ 8 avis sur 10 classés `ok`, valeurs jugées correctes par l'équipe |
| Missing data | un avis sans mention de satisfaction → `note` NULL, affiché `—` |
| Demi-journées | ≥ 2 demi-journées peuplées (matin + après-midi), dont 1 historique |
| Croisement | le panneau affiche ressenti voix vs. fréquentation de référence, badge « simulé » |
| Décision | un scénario « trop de monde » répété fait apparaître le badge saturation + Plan B |
| Repli | démo complète jouable avec `JEV_OFFLINE=1`, réseau coupé |

## 15. Arborescence

```
demo/
  worker.py      # micro + VAD + STT + appel classification
  app.py         # Streamlit
  db.py          # schéma, connexion WAL, requêtes d'agrégat
  jev.py         # client HTTP Decisions API (effets de bord, mockable) + classify_offline()
  mapping.py     # pur : questions Jev ↔ colonnes, réponse Jev → valeurs, règle missing data
  provenance.py  # pur : transcript → (ville, CP) via référentiel de communes
  bornes.yaml    # paramètres de démo : 5 bornes, code_insee, plan_b, ref_frequentation
  bornes.py      # chargement de bornes.yaml + tirage du jitter « app »
  periods.py     # calcul demi_journee + navigation
  reference.py   # séries de référence rejouées (§7)
  decision.py    # pur : règle de saturation (§2)
  tests/         # periods (cas §9), mapping (réponse mockée), provenance, decision,
                 # agrégats, invariants control/live_state (§3)
```
Lancement : `python demo/worker.py` et `streamlit run demo/app.py`
(`DEMO_PREP=1 streamlit run demo/app.py` pour la préparation).
Dépendances : `faster-whisper`, `sounddevice`, `numpy`, `pandas`, `pyyaml`, `streamlit`,
`pydeck`, `altair`, `httpx`.
