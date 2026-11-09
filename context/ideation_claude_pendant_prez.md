## 10. Pistes complémentaires (nos recherches)

### Sources et références à explorer

- **Flux Vision Tourisme** : la source de référence d'Isère Attractivité (nuitées par commune et par jour, avec l'origine des visiteurs).
- Guidelines Alpine Space pour les gestionnaires d'aires protégées et de destinations (protocole d'analyse de l'impact des activités de nature sur la biodiversité) : https://www.alpine-space.eu/wp-content/uploads/2026/11/LAN_O1.1.pdf
- Cour des comptes (février 2024), « Les stations de montagne face au changement climatique » (synthèse Vie publique) : https://www.conseil-cac.com/photos/vie-publique-fr-240213-stations-de-sports-d-hiver-_-une-activite---trop-axe--e-sur-le-ski-_-vie-publique-fr.pdf
- **Zuugle** : moteur de randonnées accessibles en transport en commun, avec horaires aller et retour (projet de la Convention alpine). Une référence directe pour l'idée « rando × horaires ».
- **Murmuration** (https://murmuration.earth/fr/) : entreprise spécialisée surtourisme et surfréquentation, fournisseuse de l'outil de capacité de charge.
- meduse.acri : à explorer.
- Autres sources ouvertes utiles :
  - prévisions Météo-France AROME par commune (meteo.data.gouv.fr) ;
  - vacances scolaires (zone A) et jours fériés ;
  - VigiEau (restrictions sécheresse par code INSEE) ;
  - indicateurs Copernicus C3S pour le tourisme de montagne (passé et projections) ;
  - Wikipedia pageviews (indicateur avancé d'intérêt pour un site) ;
  - Camptocamp (sorties datées par itinéraire) ;
  - capacités d'hébergement INSEE et Base permanente des équipements ;
  - GTFS sur transport.data.gouv.fr.

### Idées de POC envisagées

1. **Indice de pression** par site et par commune : fréquentation ÷ capacité × sensibilité environnementale, validé sur la liste des sites surfréquentés.
2. **Prévision des pics** à J+1 / J+7 (météo + calendrier + événements).
3. **Redirection « Plan B »** vers un site proche, similaire et non saturé, accessible sans voiture.
4. **Rando × transports** : pour une randonnée donnée, savoir si l'aller et le retour en bus ou en train tiennent dans la journée, compte tenu de la durée de marche ; carte des zones blanches de l'offre de transport en commun.
5. **Projection climatique** des flux (chaleur → lacs et altitude ; enneigement → stations).

Fil conducteur proposé : **mesurer → anticiper → agir**, en couvrant les problématiques 1, 2, 3 et 4 de la DGE.

### Conventions techniques du repo

- **Clé de jointure pivot** : `code_insee` de la commune × `date`.
- Tables communes : `communes`, `sites`, `flux`, `meteo` (cf. `src/isere_tourisme/data/schemas.py`).
- Les données sont lues sur le bucket SSP Cloud du projet, avec un repli sur des données fictives en local (`make demo`).

### Pièges connus

- **Granularités hétérogènes** : la commune et le jour pour Flux Vision, le sentier et l'heure pour les éco-compteurs.
- **Doublons** de sites entre DATAtourisme, Apidae et OSM.
- **Stations météo** à apparier par altitude, pas seulement par distance.
- **Pannes de compteurs** : une absence de mesure n'est pas zéro visiteur.
- **Lignes de car scolaires** : elles ne circulent ni le week-end ni pendant les vacances.
