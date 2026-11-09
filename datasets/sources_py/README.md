# hackathon_dge_gestion_des_flux

Répertoire GitHub du hackathon de la DGE pour le hackathon Gestion des flux touristiques des 9 et 10 novembre 2026.

Les bouts de codes présents dans le canal principal sont fournis comme des aides à destination des participants pour l'utilisation d'outils fournis, notamment d'API. Certaines clés d'accès aux API sont indiqués dans le document Excel mis à disposition sur le SSP Cloud avec les données disponibles, dans la rubrique "Codes".

Pour déposer un code, chaque équipe peut se créer un canal au sein de ce répertoire.

## Version Python

La branche `python` contient la traduction des scripts R en scripts Python, avec la même organisation de fichiers et de sections, organisée dans le package `src/isere_tourism`.

Installation des dépendances et de l'environnement virtuel, depuis la racine du dépôt :

```bash
make setup
```

Lancer le lint, le tri des imports, le formatage, la vérification des types et les tests :

```bash
make check
```

Le contrôle de types est assuré par mypy, configuré dans le `pyproject.toml` racine. Les modules du package peuvent ensuite être exécutés avec `uv run --all-packages python -m isere_tourism.<module>`.

Lancer uniquement les tests unitaires (aucun test n'appelle une API) :

```bash
make test
```

## Description des scripts

Chaque module du package est autonome et peut être exécuté directement avec Python. Les clés d'accès aux API à renseigner sont indiquées dans les modules et dans le document Excel mis à disposition sur le SSP Cloud.

| Fichier                       | API / services interrogés                                                                                                                                                                                               | Données récupérées                                                                                                                                                                    | Authentification                                                   | Sorties                                                                               |
|-------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|---------------------------------------------------------------------------------------|
| `src/isere_tourism/apidae.py`                   | API Apidae Tourisme (`https://api.apidae-tourisme.com/api/v002/`) : `referentiel/selections/`, `recherche/list-objets-touristiques/`                                                                                    | Sélections du projet, puis objets touristiques (fiches Apidae, 100 premiers résultats)                                                                                                | Clé `apiKey`                                                       | Affichage console                                                                     |
| `src/isere_tourism/biodiv_sports.py`            | API Biodiv'Sports (`https://biodiv-sports.fr/api/v2/sensitivearea/`) ; contours administratifs Etalab (`https://etalab-datasets.geo.data.gouv.fr/contours-administratifs/2025/geojson/departements-100m.geojson`)       | Zones sensibles en français, contours des départements, puis zones intersectant l'Isère (INSEE 38)                                                                                    | Aucune                                                             | Carte matplotlib et nombre de zones                                                   |
| `src/isere_tourism/geovelo_route_calculator.py` | API Geovelo (`https://backend.geovelo.fr/api/v2/computedroutes`)                                                                                                                                                        | Itinéraire vélo entre deux points (coordonnées, profil, type de vélo, vitesse), avec options d'instructions, de dénivelé, de géométrie et de résultat unique                          | En-tête `Api-Key`                                                  | Statut HTTP et JSON dans la console                                                   |
| `src/isere_tourism/datatourisme.py`             | API DATAtourisme v1 (`https://api.datatourisme.fr/v1`) : `placeOfInterest`, `catalog`, `entertainmentAndEvent`, `tour`, `product`, thésaurus ; API geo.api.gouv.fr (`https://geo.api.gouv.fr`)                          | POI et objets touristiques, avec filtres (département 38, type, recherche, zone géographique), pagination et colonnes (nom, type, commune, adresse, coordonnées, date de mise à jour) | En-tête `X-API-Key`                                                | DataFrame, carte Folium (`poi_map.html`), graphiques matplotlib, export CSV optionnel |
| `src/isere_tourism/commune_road_distances.py`   | Stockage S3 du SSP Cloud (MinIO, `minio.lab.sspcloud.fr`) pour `maximehautin/Communes-d_Isere.csv` ; API geo.api.gouv.fr (`/communes/{code}?fields=centre`) ; API OSRM (`https://router.project-osrm.org/table/v1/car`) | Liste des communes d'Isère, coordonnées de leur centre, puis matrice des distances routières (calcul par blocs de 50)                                                                 | Profil AWS `default` pour S3 ; aucune pour geo.api.gouv.fr et OSRM | `isere_road_distances.xlsx`                                                           |
| `src/isere_tourism/weather_data.py`             | Stockage S3 du SSP Cloud (MinIO, `minio.lab.sspcloud.fr`) pour `maximehautin/Q_38_previous-1950-2024_RR-T-Vent.csv.gz`                                                                                                  | Données quotidiennes Météo-France des stations d'Isère (RR, TN, TX, TM, etc.), sur les périodes 1986-2024 et 1950-1985                                                                | Profil AWS `default`                                               | `weather_1986_2024.csv`, `weather_1950_1985.csv`                                      |
| `src/isere_tourism/loopi.py`                    | Téléchargement du GTFS Loopi (`https://transport.loopi.fr/api/v1/datas/loopi/gtfs.zip`) ; API Loopi (`https://api.loopi.fr/1.0`) : `/user/login`, `/route/recommande`                                                   | Arrêts GTFS Loopi (`stops.txt`) et itinéraire vélo recommandé entre deux points (JSON)                                                                                                | Bearer token pour le GTFS ; email et mot de passe pour l'API Loopi | `loopi.zip`, `loopi_gtfs/`, `itineraire.json`                                         |
| `src/isere_tourism/osm.py`                      | OpenStreetMap via Overpass, à travers `osmnx` (zone : Isère, Auvergne-Rhône-Alpes, France)                                                                                                                              | Objets OSM correspondant à un tag `clé=valeur` (par défaut `amenity=restaurant`) : points, lignes, multilignes, polygones et multipolygones                                           | Aucune ; service public Overpass                                   | Graphiques matplotlib et `resultat_Isere.xlsx`                                        |
| `src/isere_tourism/transport_data_gouv.py`      | API transport.data.gouv.fr (`https://transport.data.gouv.fr/api/datasets`)                                                                                                                                              | Catalogue des jeux de données de transport couvrant l'Isère (INSEE 38) : identifiant, titre, type, URL de page et nombre de ressources                                                | Aucune                                                             | `catalogue_transports_isere.csv`                                                      |

## Glossaire

- **Apidae Tourisme** : système d'information touristique (SIT) partagé par les acteurs du tourisme français ; il permet de gérer, mutualiser et diffuser des données touristiques (hébergements, restaurants, sites, événements, etc.).
- **Biodiv'Sports** : dispositif porté par la LPO (Ligue pour la protection des oiseaux) qui cartographie les zones naturelles sensibles pour les sports de nature, afin de concilier pratique sportive et protection de la biodiversité.
- **DATAtourisme** : plateforme nationale et API open data qui agrège les données touristiques produites par les SIT territoriaux et les diffuse sous forme de POI, événements, itinéraires et produits.
- **EPCI** : Établissement public de coopération intercommunale, c'est-à-dire une intercommunalité (communauté de communes, d'agglomération, etc.).
- **Etalab** : mission de l'État chargée de l'ouverture des données publiques ; elle publie notamment les contours administratifs utilisés pour filtrer l'Isère.
- **Geovelo** : service français de calcul d'itinéraires vélo, avec des profils adaptés aux différents cyclistes et des options de sécurité et de confort.
- **GTFS** (General Transit Feed Specification) : standard ouvert de description des réseaux de transport public (lignes, arrêts, horaires) sous forme de fichiers texte.
- **INSEE** : Institut national de la statistique et des études économiques ; ses codes identifient notamment les communes et les départements.
- **Loopi** : service de mobilité douce et de calcul d'itinéraires (vélo, marche, transports) ; son API expose notamment des données GTFS et des itinéraires recommandés.
- **Météo-France** : service météorologique national qui produit les données quotidiennes de température et de précipitations utilisées dans le script météo.
- **OpenStreetMap / Overpass** : base cartographique collaborative libre ; Overpass est l'API de requête qui permet d'extraire des objets OSM par tags.
- **OSRM** (Open Source Routing Machine) : moteur de calcul d'itinéraires open source utilisé ici pour produire des matrices de distances routières entre communes.
- **POI** (Point of Interest) : point d'intérêt touristique, c'est-à-dire un lieu ou un objet référencé (musée, restaurant, site, événement, etc.).
- **SSP Cloud / MinIO / S3** : plateforme de datalab de l'Insee ; MinIO est le stockage objet compatible S3 qui héberge les fichiers de données utilisés par les scripts.
