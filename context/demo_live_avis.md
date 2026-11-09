# Spec — Démo live « enquête de satisfaction vocale »

Hackathon gestion des flux touristiques (Isère). Démo jouée en live sur **un laptop**
(micro intégré, CPU seul), projeté sur grand écran en **2 colonnes** : « Backend » et
« Frontend » (mockup téléphone).

## 1. Périmètre

| Dans le périmètre | Hors périmètre |
|---|---|
| STT local, live, sur CPU | Vraie app mobile / vraie PWA installable |
| Classification via Jev (OpenRouter) | Fallback hors-ligne (risque réseau accepté) |
| SQLite locale | Multi-utilisateur, auth, déploiement |
| Géolocalisation fictive (5 bornes) | GPS réel |
| Streamlit 2 colonnes | Texte libre généré (suggestions) : Jev ne génère pas de texte |

## 2. Architecture

Deux processus Python sur le laptop, qui communiquent **uniquement via SQLite** (mode WAL).

```
 ┌──────────────── worker.py ────────────────┐        ┌──────────── app.py (Streamlit) ────────────┐
 │ micro (sounddevice 16 kHz mono)           │        │ Col. gauche « Backend »                    │
 │  → VAD (silero) → chunks                  │        │  - bouton push-to-talk + sélecteur borne   │
 │  → faster-whisper (CPU int8)              │◄──────►│  - transcription live (partiel + validé)   │
 │  → live_state (partiel/validé)            │ SQLite │  - N dernières lignes de `avis`            │
 │ au stop : INSERT avis (pending)           │  WAL   │ Col. droite « Frontend » (mockup tél.)     │
 │  → Jev (OpenRouter) → UPDATE avis (ok)    │        │  - critère + fenêtre demi-journée + carte  │
 └───────────────────────────────────────────┘        └────────────────────────────────────────────┘
```

Pourquoi un worker séparé : Streamlit relance le script à chaque interaction et
par session, donc un thread micro hébergé dans Streamlit est fragile. Le bouton UI
écrit une commande dans la table `control`, que le worker lit environ toutes les 100 ms.

## 3. Speech-to-text (worker)

- **Modèle** : `faster-whisper` `small` **multilingue**, `device="cpu"`, `compute_type="int8"`.
  Repli sur `base` si le benchmark du jour 1 sur le laptop de démo est trop lent
  (critère : partiel affiché moins de 3 s après la parole).
- **Langue** : détection automatique, **verrouillée par enregistrement** dès le premier chunk
  de 3 s ou plus, pour éviter les bascules de langue entre partiels. Stockée dans `avis.langue`.
- **Live** : la VAD découpe l'audio sur les pauses.
  - Chunk terminé : transcrit une fois et ajouté au texte **validé**.
  - Chunk en cours : retranscrit toutes les ~2 s, ce qui donne le texte **partiel** (affiché en gris).
- **Fin d'enregistrement** : transcription finale = concaténation des chunks validés, plus le
  dernier chunk. Pas de seconde passe complète, pour garder une latence courte au stop.
- **Unité** : push-to-talk. 1 enregistrement = 1 conversation en open mic = 1 avis.

## 4. Classification — Jev (`typesafe/jev-1.14`, via OpenRouter)

- Clé : variable d'environnement `OPENROUTER_API_KEY`. Modèle épinglé `typesafe/jev-1.14`
  (pas l'alias `latest`, pour que la démo reste reproductible).
- **Un seul appel** `POST /api/alpha/decisions` par avis, avec toutes les questions
  ci-dessous. ⚠️ À vérifier au jour 1 : forme exacte de la requête et de la réponse, et
  possibilité de mettre plusieurs questions dans un appel. Si ce n'est pas possible :
  appels en parallèle.
- **State** envoyé : le transcript final, plus le contexte (borne, langue).
- **Règle « missing data »** : chaque Choice contient l'option `non_mentionne`. Si elle gagne,
  la colonne vaut **NULL**. Pas de seuil de confiance. La réponse brute de Jev (probabilités
  et confiance) est toujours stockée dans `jev_raw`.

| Colonne | Primitive | Options / échelle | Définition donnée à Jev |
|---|---|---|---|
| `profil` | Choice | touriste, excursionniste, local, non_mentionne | touriste = ≥ 1 nuit hors domicile ; excursionniste = venu à la journée sans nuitée ; local = habite à proximité |
| `origine` | Choice | isere, autre_france, etranger, non_mentionne | lieu de résidence |
| `groupe` | Choice | seul, couple, famille, amis, groupe_organise, non_mentionne | composition du groupe |
| `mode_venue` | Choice | voiture, transport_en_commun, velo, a_pied, autre, non_mentionne | mode d'accès au départ de la rando |
| `affluence` | Choice | faible, normale, saturee, non_mentionne | ressenti sur le nombre de personnes ; `saturee` = « trop de monde » |
| `revenir` | Choice | oui, non, non_mentionne | intention de revenir |
| `note` | Score | 1 → 5 | satisfaction globale **inférée** de la conversation. Toujours renseignée, sans option NULL. Valeur continue (position pondérée) |

- **Statut** : l'avis est inséré `classif_status='pending'` dès le stop (il s'affiche
  immédiatement), puis passe à `ok` ou `error`. Si `error` : bouton « Re-classifier »
  dans la colonne Backend. Pas de fallback local.

## 5. Géolocalisation fictive

Avant chaque enregistrement, on choisit dans l'UI :
- **borne** (1 parmi 5) ;
- **source** : `borne` (coordonnées exactes de la borne) ou `app` (point aléatoire
  uniforme dans un disque de **2 km** autour de la borne, qui simule un passage par l'app sur une
  rando voisine).

| id | Départ | Massif | lat ≈ | lon ≈ |
|---|---|---|---|---|
| `chamrousse` | Lac Blanc / Chamrousse 1750 | Belledonne | 45.11 | 5.88 |
| `col_porte` | Col de Porte | Chartreuse | 45.29 | 5.77 |
| `moliere` | Plateau de la Molière | Vercors | 45.17 | 5.58 |
| `sept_laux` | Les 7 Laux (Prapoutel) | Belledonne | 45.25 | 5.99 |
| `bourg_arud` | Bourg-d'Arud → Lac de la Muzelle | Oisans | 44.96 | 6.13 |

⚠️ Coordonnées **approximatives** : à vérifier sur OpenStreetMap avant de les figer dans
`bornes.py`.

## 6. Base de données (SQLite, `data/demo.db`, gitignorée)

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
  source         TEXT NOT NULL CHECK (source IN ('borne','app')),
  lat            REAL NOT NULL,
  lon            REAL NOT NULL,
  profil         TEXT, origine TEXT, groupe TEXT, mode_venue TEXT,
  affluence      TEXT, revenir TEXT,
  note           REAL CHECK (note BETWEEN 1 AND 5),
  classif_status TEXT NOT NULL CHECK (classif_status IN ('pending','ok','error')),
  jev_model      TEXT,
  jev_raw        TEXT,                   -- JSON brut de la réponse Jev
  is_init        INTEGER NOT NULL DEFAULT 0  -- avis d'initialisation enregistré par l'équipe
);
CREATE INDEX idx_avis_dj ON avis(demi_journee);

CREATE TABLE live_state (               -- 1 seule ligne, id = 1
  id INTEGER PRIMARY KEY CHECK (id = 1),
  status TEXT,                          -- idle | recording | transcribing | classifying
  committed_text TEXT, partial_text TEXT, langue TEXT, updated_at TEXT
);

CREATE TABLE control (                  -- commandes UI → worker
  id INTEGER PRIMARY KEY, cmd TEXT CHECK (cmd IN ('start','stop')),
  borne_id TEXT, source TEXT, event_ts_override TEXT,
  created_at TEXT, consumed INTEGER DEFAULT 0
);
```

## 7. Demi-journées

- Fuseau **Europe/Paris** (calcul fait en heure locale, puis stocké).
- Plages nominales : **matin 6h–13h**, **après-midi 13h–20h**. Un avis hors plage est
  rattaché à la plage du **même jour** la plus proche : 0h–6h → matin, 20h–24h → après-midi.
  En pratique : `heure < 13 → matin`, sinon `après-midi`.
- **Initialisation** : avant la démo, l'équipe enregistre quelques avis réels (`is_init=1`).
  En **mode préparation** (toggle dans la sidebar, masqué pendant le show), un champ
  « date simulée » remplit `event_ts` pour peupler des demi-journées passées. Il n'y a pas de
  données synthétiques générées.

## 8. Front-end (Streamlit, page unique `layout="wide"`)

**Rafraîchissement** : `st.fragment(run_every=1s)` sur les zones live (transcription,
dernières lignes, viz si la fenêtre est la demi-journée en cours).

### Colonne gauche — « Backend »
1. Sélecteur borne + source, bouton **● Enregistrer / ■ Stop**.
2. Transcription live : statut du worker, texte validé (noir) + partiel (gris), langue détectée.
3. **Dernières lignes** de `avis` (10 par défaut) : heure, borne, source, transcript tronqué,
   colonnes de classif (NULL affichés `—`), statut, `jev_raw` dépliable.

### Colonne droite — « Frontend » (mockup téléphone)
Conteneur Streamlit à clé (`st.container(key="phone")`), mis en forme en CSS (classe
`.st-key-phone`) comme un cadre de téléphone d'environ 390 px. Contenu :
1. **Sélecteur de critère** :
   - Distribution des notes : histogramme de `round(note)` sur 1–5, avec la moyenne calculée
     sur la valeur continue.
   - Touriste / excursionniste / local : proportions calculées sur les non-NULL, avec le nombre
     de « non mentionné » affiché à part.
   - Volume d'avis : total, par borne, par source.
   - Mode de venue et affluence : répartition des modes de venue ; affluence par borne
     (faible = 1, normale = 2, saturée = 3, moyenne sur les non-NULL).
   - Mention de saturation : saturée / non saturée (faible ou normale) / non mentionné.
2. **Fenêtre temporelle** :
   - par défaut : **demi-journée en cours, en live** (les nouveaux avis apparaissent) ;
   - ◀ / ▶ : navigue d'une demi-journée, vue figée (badge « Historique ») ; bouton « Live »
     pour revenir à la demi-journée en cours ;
   - toggle **« Tout le passé »** : agrégat sur tous les avis.
3. **Mini-carte** (pydeck) : les 5 bornes et les points des avis de la fenêtre.

## 9. Arborescence

```
demo/
  worker.py      # micro + VAD + STT + Jev
  app.py         # Streamlit
  db.py          # schéma, connexion WAL, requêtes d'agrégat
  jev.py         # client Decisions API + mapping questions → colonnes
  bornes.py      # 5 bornes + tirage du jitter « app »
  periods.py     # calcul demi_journee + navigation
  tests/         # periods, mapping Jev (réponse mockée), agrégats
```
Lancement : `python demo/worker.py` et `streamlit run demo/app.py`.
Dépendances : `faster-whisper`, `sounddevice`, `numpy`, `streamlit`, `pydeck`,
`altair`, `httpx`.

## 10. Risques et vérifications au jour 1

| Risque | Action |
|---|---|
| Format exact de l'API Jev, multi-questions | Premier appel curl réel, puis figer `jev.py` |
| Latence STT `small` sur le CPU du laptop de démo | Benchmark sur 30 s d'audio ; repli `base` |
| Réseau de la salle (risque accepté) | Partage 4G prêt ; avis conservé en `error` + bouton re-classifier |
| Bascule de langue auto sur des extraits courts | Langue verrouillée par enregistrement |
| Permission micro / mauvais périphérique | `sounddevice.query_devices()` au lancement, device configurable |
| Coordonnées des bornes | Vérifier sur OSM |
