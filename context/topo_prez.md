# Contexte — Hackathon DGE « Gestion des flux touristiques » (Isère)

> Synthèse des slides de lancement (DGE, 5 novembre 2026) + notes d'équipe.
> À lire avant de contribuer au repo : c'est le cadre qui guide nos choix.

## 1. L'esprit

- Mobiliser et valoriser la donnée touristique au service d'une gestion **« intelligente et raisonnée »** des flux.
- Explorer des **cas d'usage pratiques**, pas produire un produit fini : on livre des **POC**.
  *(Notre parti pris : un POC le plus abouti possible, démontrable en live.)*
- Approche attendue : **novatrice**.
- Cible : l'**écosystème** des acteurs du tourisme : entreprises, collectivités, offices de tourisme, gestionnaires de sites.
- Données et outils fournis, **ou** autres données et outils **open source**.

## 2. Le territoire test : l'Isère

- Le département est jugé la bonne échelle pour gérer les flux.
- **16,7 M de nuitées en 2024** (7,4 M en hiver, 7,2 M en été), soit le 22ᵉ département français.
- Tourisme très varié : nature, sport, urbain, montagne.
- Un travail de longue date sur l'observation et la gestion des flux, porté par **Isère Attractivité**.
- Toutes les données mises à disposition sont **iséroises**.

## 3. Problématiques et cas d'usage proposés

| Problématique | Cas d'usage suggérés |
|---|---|
| **Réorienter les flux** d'une zone à une autre | Éviter une zone saturée et rediriger vers une expérience visiteur proche · Parcours touristique personnalisé |
| **Anticiper les pics** de fréquentation | Prévoir les flux |
| **Qu'est-ce qu'une zone sur- ou sous-fréquentée ?** | Évaluer la surfréquentation de façon multifactorielle · Évaluer le potentiel touristique d'une zone |
| **Développer les mobilités douces** dans les parcours | Identifier les zones où l'offre de transport en commun est insuffisante · MaaS à l'échelle du département |
| **Caractériser et profiler les visiteurs** | Clusteriser les profils (socio-économiques, pratiques) dans les ENS |

### Nos notes sur ces problématiques

- **Réorienter les flux** : un parcours personnalisé, oui, mais il faut **maîtriser les sites mis en avant**. La recommandation ne doit pas créer de nouveaux points de saturation (réguler la recommandation).
- **Anticiper les pics** : un expert d'**Affluences** est disponible.
- **Surfréquentation** : la caractériser avec des signaux **plus objectifs et multiples** (trafic routier, parkings, éco-compteurs…).
- **Mobilités douces** :
  - mettre en place bus, transports et covoiturage (MaaS) ;
  - idée du **« lobby »** (comme dans le gaming) : regrouper les visiteurs qui vont au même endroit pour remplir une navette ou un covoiturage, puis une sorte de « Uber » sur place ;
  - contraindre ces trajets par les enjeux environnementaux ;
  - mesurer le **gain par rapport au coût marginal**.

## 4. Les données mises à disposition

| Type | Exemples |
|---|---|
| Communes | Liste des communes, distances routières entre communes |
| Sites et équipements | DATAtourisme, OSM (instance privée [Clearance](https://www.teritorio.fr/fr/blogs/clearance-sameliore-pour-un-controle-simplifie-des-donnees-osm/)), Apidae, Base ES, Base Mérimée, **liste de sites surfréquentés** |
| Activités | Activités sportives, fêtes et manifestations |
| Fréquentation | ~~Orange Flux Vision~~, **éco-compteurs**, fréquentation des parkings, comptages routiers |
| Hébergements | Par commune (nombre d'établissements, types, nombre de lits), labels |
| Commerces | Par commune, commerces et services utiles à la clientèle touristique |
| Transports | Réseaux de transports publics, véloroutes |
| Randonnées | Itinéraires de promenade et de randonnée (PDIPR), OutdoorVision |
| Ski | Domaines skiables et VTT, données d'enneigement |
| Météo | Historique **1950–2024** |
| Biodiversité | Système d'information sur la biodiversité, piétinement de la végétation, habitats naturels |
| Ressources et déchets | Consommation et pollution de l'eau, traitement des déchets, consommation d'électricité et de gaz |
| Emploi | Emplois par commune |

## 5. Les outils

| Outil | Usage |
|---|---|
| Fonds de carte | BD TOPO (IGN), zonages, limites de l'Isère |
| Codes | Aide à l'utilisation des API (parfois avec une clé hackathon) |
| API | DATAtourisme, Apidae, OSM/Clearance, transports en commun (Loopi, transport.data.gouv.fr), itinéraires vélo (GéoVélo), Biodiv'Sports, ~~Orange Flux Vision~~ |
| Plateforme | **Murmuration** : évaluation de la capacité de charge touristique d'un territoire fictif |
| Cas d'usage | Liste d'exemples plus précis (cf. §3) |
| **SSP Cloud** | Accès à toutes les données. Projet : `projet-hackathon-gestion-flux-isere` |
| **GitHub** | Codes fournis. Dépôt : `hackathon_dge_gestion_des_flux` |
| WhatsApp | Salon d'échange entre équipes et avec les experts |

> **À faire : créer son compte SSP Cloud** (avec son adresse e-mail) pour accéder aux données.

## 6. Les experts

**Sur place** : Virginie Jacob (Isère Attractivité, tourisme en Isère) · Fabien Ferdinandy (Loopi, mobilité touristique) · Nicolas Hafner (Eco-Compteur, données éco-compteurs) · Gwenaëlle Carfantan (UrbanThink, valorisation des données, cartographie) · Morgane Pfefferlé (Travelise, parcours touristiques surprises) · Stéphane Branquart (Teritorio, écosystème OSM) · Charles-Henri Boisseau (ADN Tourisme, DATAtourisme) · Céline Tritz (Université Grenoble Alpes, tourisme durable) · Jonathan Huffstutler (EONA-X, data et IA, données touristiques) · Gautier Hauser (Affluences, observation des flux) · Ines Hiverlet (Insee, SSP Cloud).

**À distance (via WhatsApp)** : Murmuration (Hugo Poupard, appui technique ; Jeremy Moisan, appui fonctionnel ; Cathy Sahuc, appui général) · GéoVélo (Jean-Rémy Ricordel, données, calculateur et API) · Loopi (Cyrille Cebrand, données, calculateur et API).

*(Numéros de téléphone volontairement non repris ici : voir les slides ou le salon WhatsApp.)*

Note : les données éco-compteurs sont en cours de finalisation par Nicolas Hafner.

## 7. Déroulé

- Lieu : 41 boulevard Vincent Auriol, Paris 13ᵉ (locaux du CISIRH), métro ligne 6 (Chevaleret) ou ligne 14 (BnF). Horaires : 8h30–20h les deux jours.
- **Lundi 8h30–10h** : présentation et introduction.
- **Lundi 10h → mardi 17h** : travail en équipe. **Un livrable intermédiaire est à rendre lundi soir.**
- **Mardi 17h–20h** : passage devant le jury, délibération et remise des prix.
- À prévoir : carte d'identité, ordinateur et chargeur, connexion de secours (clé 4G, partage de connexion), gourde. Café et déjeuner sont fournis.

## 8. Livrables et jury

**Livrables** : (1) un code ou autre POC, (2) une documentation, (3) une présentation PowerPoint.

**Pitch** : 10 minutes pour présenter la solution et le POC, avec un support PowerPoint. **Répéter avant.** Au plus **2 équipes lauréates**, dont les solutions seront privilégiées dans la valorisation après le hackathon.

### Critères d'évaluation (chacun noté sur 10)

1. **Aboutissement et qualité** de la réponse produite (code, outil…).
2. **Inventivité et originalité** de la démarche.
3. **Pertinence de l'utilisation** des données et outils mis à disposition.
4. **Bénéfices potentiels** pour une gestion plus raisonnée des flux touristiques.
5. **Potentiel de mise à l'échelle et reproductibilité**.

Conséquences pour le repo :

- démo qui tourne de bout en bout (critère 1) ;
- utiliser explicitement les jeux fournis (critère 3) ;
- code générique, paramétré par département ou commune plutôt qu'en dur sur l'Isère (critère 5).

## 9. Questions et réponses

- **Le code est-il ouvert ? Quel est le statut des données issues des API ?**
  Le code est ouvert. Les données fermées (Clearance, API sous clé…) ne doivent **pas être publiées** dans le repo. En pratique, on garde `data/` et `.env` hors de Git, et on ne versionne que les scripts.
