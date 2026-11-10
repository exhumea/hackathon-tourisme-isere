# Préparation au jury — « La borne qui écoute »

> **Document interne de préparation. Ne pas projeter tel quel.**
>
> Il sert à tenir les 8 à 10 minutes de questions du jury sans surpromettre, sans
> improviser et sans se contredire. Il distingue systématiquement ce qui est
> **démontré** dans le POC de ce qui reste une **cible**.
>
> Périmètre : le pitch « La borne qui écoute — le livre d'or numérique des sites
> touristiques » (`slidev/slides.md`, branche `origin/slidev-presentation`) et la
> démo vocale (`demo/`, branche `origin/feat/demo-live-avis`).
>
> État du dépôt au 10 novembre 2026 : la démo et les slides **ne sont pas sur
> `main`** ; il n'y a **pas de fichier `LICENSE` à la racine** ; la licence MIT
> n'est déclarée que dans `datasets/sources_py/pyproject.toml`.

## 0. En une page

### La thèse à défendre

> **Les compteurs disent combien de personnes passent. Ils ne disent ni comment
> elles vivent le site, ni ce qui coince, ni pourquoi elles reviendront — ou pas.
> La borne ajoute cette couche de perception, au point de visite, pour alimenter
> la première étape de toute politique de gestion des flux : observer.**

Ce n'est pas un système de gestion des flux. C'est un **capteur de perception**
qui produit des signaux structurés, localisés et comparables dans le temps.

### La phrase de repli, à utiliser dès qu'une question dépasse le POC

> **« Nous ne le démontrons pas encore. Le POC montre que la chaîne technique
> fonctionne de bout en bout ; le pilote devra mesurer l'usage, la représentativité
> et l'impact. »**

Cette phrase n'est pas une dérobade. C'est la seule réponse crédible quand le jury
demande une preuve d'impact, de représentativité ou de coût complet.

### Les trois messages à faire passer

1. **Le ressenti est une donnée de gestion.** Les seuils de fréquentation ne se
   définissent pas seulement avec des comptages : il faut aussi la capacité
   écologique du site et le ressenti des visiteurs.
2. **La borne est complémentaire, pas concurrente.** Elle ne remplace ni les
   éco-compteurs, ni les enquêtes, ni Isère Outdoor. Elle comble le trou entre
   « combien » et « comment ».
3. **Le POC est honnête sur ses limites.** Chaîne STT → classification → SQLite
   → carte, démontrée en live ; croisement éco-compteurs, borne physique, pilote
   terrain et analyse d'impact : cible.

### Les trois corrections à faire avant de monter sur scène

1. **Réunir les branches** : démo + slides sur `main`, sinon le jury qui clique
   sur le dépôt ne voit ni l'une ni l'autre.
2. **Ajouter un `LICENSE` MIT à la racine** : le règlement l'exige, et le dépôt
   ne le contient pas aujourd'hui.
3. **Aligner le discours et la démo** : la « carte de saturation » du slide 5
   n'existe pas dans le POC ; les 5 sites du pitch ne sont pas les 5 ENS de la
   spec ; les « sites pilotes » ne sont pas contractualisés.

## 1. Auto-évaluation honnête face aux sept critères du règlement

| Critère (article 7) | Niveau | Ce qui tient déjà | Ce qui ne tient pas encore | Action avant le jury |
|---|---|---|---|---|
| **Pertinence dans l'utilisation des données** | Moyen | Le concept répond à un angle mort réel : la perception et les motifs. Les critères classifiés sont utiles au pilotage. | La démo n'exploite pas les jeux fournis : pas de série éco-compteurs chargée, pas de croisement avec les 53 sites surfréquentés ni avec les ENS. | Charger au minimum une série éco-compteurs et afficher sa provenance ; à défaut, l'annoncer comme cible. |
| **Qualité de la présentation** | Moyen | Récit clair « on compte → on n'écoute pas » ; objet simple ; démo live prévue. | Le slide 3 est un placeholder ; le pitch et la démo sont sur deux branches ; certaines promesses du deck ne sont pas dans le code. | Fusionner, remplacer le placeholder, répéter deux fois, préparer des captures si le live échoue. |
| **Aboutissement et qualité** | Moyen | Chaîne complète : micro → VAD → STT local → classification → SQLite → Streamlit ; tests présents dans la branche démo. | Pas de borne physique, pas de test terrain, pas d'API, pas de `LICENSE`, pas de CI pour la démo. | Fusionner sur `main`, ajouter `LICENSE`, brancher la démo dans la CI, faire tourner `make check`. |
| **Bénéfices pour la gestion des flux** | Moyen à faible | Les signaux produits (affluence ressentie, irritants, profils, mode de venue) éclairent parking, signalétique, navettes, communication. | Aucun impact démontré ; auto-sélection ; pas de protocole d'évaluation. | Annoncer un pilote avec indicateurs avant/après et site témoin ; ne pas promettre de pourcentage. |
| **Mise à l'échelle et reproductibilité** | Moyen | Code paramétré par sites (`bornes.py`), STT local, stack open source, pas de dépendance à une app propriétaire. | Coût matériel, énergie, connectivité, maintenance, gouvernance et analyse non chiffrés. | Écrire un protocole de pilote à 1 site, avec BOM et scénarios de coût. |
| **Pertinence stratégique** | Solide | S'inscrit dans l'axe 3 de la DGE (« mesurer les flux et leurs impacts »), dans l'« optimum touristique » d'Isère Attractivité et dans le triptyque d'Eco-Compteur. | Positionnement encore flou face aux acteurs en place ; pas de partenariat formalisé. | Formuler « brique d'observation », pas « plateforme » ; proposer une intégration, pas un remplacement. |
| **Inventivité et originalité** | Solide | Open mic vocal + classification contrainte + borne sans compte : combine faible friction, verbatim spontané et données structurées. | La technologie seule n'est pas nouvelle ; la gamification du deck est une idée, pas une preuve. | Insister sur la combinaison et la contrainte terrain, pas sur « l'IA ». |

**Lecture stratégique.** Les deux critères où le projet est le plus solide sont la
pertinence stratégique et l'inventivité. Les trois critères où il est le plus
fragile sont la pertinence des données *telles que démontrées*, l'impact et
l'aboutissement. C'est cohérent avec le statut de POC : le risque n'est pas le
concept, c'est l'écart entre le récit et la preuve.

## 2. Ce qui est démontré, ce qui est cible

| Élément | Statut | Preuve / réalité | Écart à assumer |
|---|---|---|---|
| Captation vocale push-to-talk | **Démontré** | Micro + VAD + `faster-whisper` CPU, partiels live, arrêt automatique après silence. | Pas de test en conditions réelles (bruit, vent, foule). |
| Transcription locale | **Démontré** | Audio non persisté ; seuls les transcripts sont stockés. | Qualité dépendante de l'accent, de la langue, du micro. |
| Classification structurée | **Démontré** | Jev via OpenRouter, 7 critères (profil, origine, groupe, mode de venue, affluence, retour, note), option « non mentionné », `jev_raw` conservé. | Pas de benchmark sur voix réelle ; la note globale est **toujours inférée**, même si la personne ne l'a pas exprimée. |
| Stockage et interface | **Démontré** | SQLite WAL, Streamlit deux colonnes, carte `pydeck`, navigation par demi-journées, vues notes / profil / volume / venue / saturation. | La carte affiche des **points d'avis**, pas une saturation croisée. |
| Croisement avec les éco-compteurs | **Cible** | Prévu dans la spec (`reference.py`, série mensuelle, badge « simulé »). | **Absent de la démo** : aucun module de référence, aucune série chargée. |
| Carte de saturation | **Cible** | Slide 5 : « affluence ressentie × éco-compteurs ». | La démo ne la produit pas ; la vue « saturation » est un histogramme des mentions. |
| Borne physique | **Cible** | Boîtier, micro, bouton, batterie/solaire, connectivité. | Le POC tourne sur un laptop ; aucun prototype matériel. |
| 5 sites (candidats) | **Cible** | 5 points de démonstration dans `bornes.py` : Chamrousse, Col de Porte, Molière, 7 Laux, Bourg-d'Arud. | Ce sont des **sites candidats**, pas des sites pilotes contractualisés. La spec, elle, liste 5 ENS différents. |
| Application / module Isère Outdoor | **Cible** | Le deck évoque un prolongement dans l'app départementale. | Aucune intégration, aucun accord, aucun code. |
| Gamification | **Idée** | Le deck cite « Catch'em'all » et « Space Invaderz ». | Non implémenté ; risque de marque et risque d'inciter à visiter plus. |
| API ouverte | **Cible** | Slide 5 : données agrégées pour les partenaires. | Pas d'API ; SQLite local. |
| RGPD / IA Act | **Partiel** | Audio non conservé, pas de compte, pas d'identifiant persistant ; avis de l'équipe uniquement. | Pas d'analyse juridique, pas de base légale documentée, pas d'AIPD, pas de mention « IA » à l'écran. |
| Licence open source | **Partiel** | MIT déclarée dans `datasets/sources_py/pyproject.toml`. | Pas de `LICENSE` racine ; les conditions des modèles et de Jev ne sont pas auditées. |
| Dépôt public complet | **Non** | Démo et slides existent sur des branches dédiées. | `main` ne contient ni l'une ni l'autre. |

### 2.1. Ce que fait réellement la démo

- Elle enregistre une conversation, la transcrit localement, la classe, la stocke
  et l'affiche.
- Elle permet de choisir une borne et une source (`borne` ou `app`, avec un point
  aléatoire dans un rayon de 2 km).
- Elle agrège les avis par demi-journée et par critère.
- Elle affiche une carte des avis, pas une carte de charge.
- Elle ne calcule **aucune** fréquentation mesurée : le volume affiché est un
  **nombre d'avis**, pas un nombre de visiteurs.

### 2.2. Les écarts de cohérence à corriger

1. **Sites** : le pitch utilise Chamrousse, Col de Porte, Molière, 7 Laux,
   Bourg-d'Arud ; la spec utilise Bois de la Bâtie, Col du Coq, Écouges, Peuil,
   Montfort. La démo suit le pitch. Il faut soit aligner la spec sur la démo,
   soit expliquer que les ENS sont la cible de déploiement et les trailheads la
   vitrine de démonstration.
2. **Carte de saturation** : le deck la présente comme une réutilisation
   existante ; la démo ne la fait pas. La requalifier en « cible » ou
   l'implémenter.
3. **Modèle Jev** : la spec épingle `typesafe/jev-1.14` ; la démo utilise
   `typesafe/jev-1.13` par défaut. Aligner et documenter le choix.
4. **Carte** : la spec prévoit Folium ; la démo utilise `pydeck`. Ce n'est pas
   grave, mais il faut le dire si le jury compare.
5. **Schéma de base** : la spec prévoit `transcription` + `inference_avis` ; la
   démo utilise une table `avis` plus directe. Là encore, aligner la doc.
6. **« Sites pilotes »** : remplacer par « sites candidats » tant qu'aucune
   convention n'est signée.
7. **Coût** : « quelques centimes par avis » ne couvre que l'inférence. Le coût
   complet est ailleurs (voir R6).

## 3. Les arguments de fond

### 3.1. Pourquoi le ressenti est une donnée de gestion des flux

La gestion des flux ne consiste pas seulement à compter. Elle consiste à décider
quand un site est « plein », pour qui, à quel moment, et avec quels effets. Or un
site peut être saturé pour un visiteur et acceptable pour un autre : la même
fréquentation n'a pas le même sens selon qu'on est venu en famille, à vélo, pour
une randonnée de six heures ou pour une photo au coucher du soleil.

Les compteurs donnent une **pression objective**. La borne donne une **pression
perçue** et ses causes : parking plein, sentier bondé, signalétique absente,
transports insuffisants, conflits d'usage. Croiser les deux permet de distinguer
trois situations que les compteurs seuls confondent :

- **fréquenté mais bien vécu** : pas de priorité d'action, éventuellement de la
  communication ;
- **fréquenté et mal vécu** : priorité, car la qualité de l'expérience se dégrade ;
- **peu fréquenté mais mal vécu** : problème local (accès, entretien, sécurité)
  que le volume ne révèle pas.

C'est exactement le type de distinction qu'une politique de gestion des flux doit
pouvoir faire.

### 3.2. Ce que disent les acteurs externes

#### Eco-Compteur

La page « Gérer les pics de fréquentation » distingue les indicateurs
quantitatifs et qualitatifs. Pour définir un seuil de fréquentation, elle cite
trois entrées :

1. des **données de comptage** (heure, jour, saison) ;
2. la **capacité d'accueil écologique** du site (érosion, biodiversité, taille) ;
3. le **ressenti des visiteurs** (taux de satisfaction, confort).

C'est l'argument le plus utile pour le pitch : un acteur du comptage dit lui-même
que le comptage ne suffit pas. La borne ne concurrence pas Eco-Compteur ; elle
fournit la troisième entrée.

La même page donne un cas documenté : au parc national des Monts tabulaires
(Pologne), un programme de diagnostic et d'action a fait passer l'insatisfaction
liée à la surfréquentation de **53 % à 19 %**. Ce chiffre ne prouve pas l'effet de
notre borne ; il prouve qu'un dispositif d'observation peut être associé à une
réduction de l'insatisfaction. Il faut le citer comme **preuve de plausibilité**,
pas comme preuve d'efficacité de notre outil.

Eco-Compteur indique aussi que sa prédiction de fréquentation fonctionne sur
**quatre jours glissants**, avec un an d'historique, la météo et le calendrier.
C'est une cible réaliste pour la suite : la borne n'a pas besoin de prédire pour
être utile, mais elle peut alimenter un modèle de prévision.

> **Précaution de sourcing** : Eco-Compteur est un fournisseur. Sa page est une
> doctrine produit, pas une évaluation indépendante. Il faut le dire si le jury
> demande la nature de la source.

#### Isère Attractivité

La démarche « optimum touristique » vise un niveau de fréquentation qui concilie
attractivité, qualité de vie et préservation des ressources. La page dit
explicitement que le croisement entre **données objectives et perceptions
locales** permet une lecture plus complète des effets du tourisme. Elle a été
expérimentée sur trois territoires aux profils différents : Les Deux-Alpes,
Saint-Antoine-l'Abbaye et Allevard-les-Bains.

C'est le deuxième argument fort : la borne **opérationnalise la partie
« perceptions »** de l'optimum. Elle ne remplace pas la démarche ; elle fournit
une source de perception continue, là où les concertations sont ponctuelles.

La formule « accueillir mieux, pas forcément plus » est également une bonne
réponse à la crainte de l'effet rebond : le but n'est pas d'attirer plus de
monde, mais de mieux répartir et de mieux vivre les pics.

#### DGE et France Tourisme Durable

La DGE rappelle que **80 % de l'activité touristique se concentrerait sur 20 % du
territoire**. Sa stratégie nationale s'organise en quatre axes : compréhension
commune, sensibilisation, mesure des flux et des impacts, accompagnement des
territoires. France Tourisme Durable détaille quatre étapes pour un gestionnaire
de destination :

1. **Observer** : mesurer les flux et analyser leurs impacts (économie,
   biodiversité, habitants) ;
2. établir une **gouvernance** ;
3. construire une **stratégie** ;
4. **former, sensibiliser, communiquer**.

La borne se situe clairement à l'étape 1. Elle ne prétend pas remplacer les
étapes 2 à 4. C'est une réponse à la question « comment observer ce que les
compteurs ne voient pas ? ».

France Tourisme Durable met aussi en garde contre les **effets de report** : avant
de prendre des mesures, il faut identifier les risques de déplacer les touristes
vers des sites qui ne sont pas dimensionnés pour les accueillir. C'est un
argument décisif contre une recommandation naïve (voir R14).

#### Isère Outdoor

Isère Outdoor est l'application du Département de l'Isère. Elle donne accès à un
catalogue d'itinéraires et de sites (randonnée, vélo, trail, escalade, sports
d'eau, etc.), avec des filtres, des fonds de carte, la géolocalisation, le
téléchargement hors ligne, la signalisation d'un problème via SURICATE, les
services à proximité, les ENS, un tag « arrêt de transport en commun à
proximité », et la possibilité de **noter et commenter les itinéraires**.

C'est un acteur voisin, pas un concurrent direct :

- Isère Outdoor est **centré itinéraire** et **centré pratique** ;
- la borne est **centrée site** et **centrée expérience vécue** ;
- Isère Outdoor est un **canal de diffusion** ; la borne est un **capteur**.

La complémentarité est crédible : un module « avis terrain » dans l'app, ou un
lien depuis la fiche d'un site vers les agrégats de la borne. Mais il ne faut pas
promettre une intégration qui n'existe pas.

### 3.3. Le positionnement en une phrase

> **Nous ne remplaçons ni les compteurs, ni les enquêtes, ni l'app départementale.
> Nous ajoutons la couche « comment les visiteurs vivent le site » qui manque à
> tout dispositif de gestion des flux.**

## 4. Les quinze réserves majeures du jury

Chaque bloc suit le même format : objection probable, contre-argument, limite
honnête, preuve ou source, action avant le jury.

### R1 — « Vous ne mesurez pas les flux, vous collectez des avis. »

**Contre-argument.** Les compteurs mesurent un volume ; ils ne mesurent ni la
qualité de l'expérience, ni les causes de mécontentement, ni les motifs de venue.
Or ces éléments déterminent les décisions : faut-il ajouter une navette, revoir
la signalétique, limiter un parking, communiquer sur un autre site ? La borne
produit ces signaux au point de visite, de façon continue et localisée. Elle
alimente l'étape « Observer » de la DGE et la partie « perceptions » de l'optimum
touristique d'Isère Attractivité.

**Limite honnête.** Le POC ne fait pas le croisement avec les éco-compteurs et ne
démontre aucun impact. Il montre seulement que la collecte et la structuration
fonctionnent.

**Preuve / source.** Eco-Compteur : les seuils exigent comptage + capacité
écologique + ressenti. France Tourisme Durable : étape 1 « Observer ». Isère
Attractivité : croisement données objectives / perceptions.

**Action.** Si le temps le permet, charger une série éco-compteurs et afficher un
indicateur de tension avec une formule explicite et un badge « simulé ». Sinon,
dire clairement que le croisement est la cible du pilote.

### R2 — « Vos données ne sont pas représentatives. »

**Contre-argument.** C'est vrai, et nous ne le prétendons pas. Une borne produit
un **signal qualitatif local, auto-sélectionné**, comme un livre d'or : il ne dit
pas « 30 % des visiteurs sont insatisfaits », il dit « voici ce qui revient dans
les verbatims, à cet endroit, à cette demi-journée ». Ce signal est utile pour
détecter des irritants, formuler des hypothèses et orienter des investigations,
pas pour estimer une population.

**Limite honnête.** Auto-sélection, biais de désirabilité, sous-représentation
des personnes qui ne parlent pas français ou qui refusent l'exercice, petits
effectifs par demi-journée. On ne peut pas pondérer sérieusement sans données
auxiliaires.

**Preuve / source.** La nature même du dispositif ; la comparaison avec les avis
en ligne (publics, non structurés, non représentatifs) et avec les enquêtes
(ponctuelles, coûteuses, mais échantillonnées).

**Action.** Afficher systématiquement `n` et le taux de non-réponse ; ne jamais
présenter une valeur comme un pourcentage de la population ; croiser avec une
enquête terrain sur un site pour mesurer l'écart.

### R3 — « Pourquoi une borne vocale plutôt qu'un QR code ou une app ? »

**Contre-argument.** La borne vocale réduit la friction : pas d'app à installer,
pas de compte, pas de clavier, pas de smartphone requis. Elle est plus inclusive
pour les personnes âgées, les visiteurs étrangers et les randonneurs qui ont les
mains occupées. Elle produit un verbatim spontané, multilingue, plus riche qu'un
questionnaire à cases. Et l'objet physique crée une présence, un point de repère,
une raison de s'arrêter.

**Limite honnête.** Le QR code est moins cher, plus facile à déployer et moins
intrusif. La voix peut être gênante en public, difficile à capter avec du vent,
et exclure les personnes sourdes ou malentendantes. Nous n'avons aucune donnée
sur le taux de participation réel.

**Preuve / source.** Isère Outdoor montre la limite d'une approche 100 %
application : elle suppose un smartphone, une installation et un compte. La borne
n'est pas meilleure en absolu ; elle teste une autre hypothèse.

**Action.** Prévoir un test A/B borne vs QR code sur un site : taux de
participation, taux de réponses exploitables, richesse des verbatims, coût par
réponse utile. Ajouter un canal texte/QR en complément, pas en remplacement.

### R4 — « Une borne qui écoute, c'est de la surveillance. »

**Contre-argument.** Le dispositif est un **push-to-talk** : on appuie, on parle,
on appuie. Pas d'écoute permanente, pas de caméra, pas de compte, pas
d'identifiant persistant, pas d'audio conservé. Le traitement vocal est local
dans le POC ; seuls le transcript et des catégories agrégées sont stockés. La
CNIL elle-même recommande de privilégier le traitement local et de construire la
confiance par des frictions explicites (bouton, information, choix).

**Limite honnête.** La voix reste une donnée personnelle. Il faut une base légale,
une information claire, une durée de conservation, une sécurité, un DPO et,
selon l'échelle, une AIPD. Le POC ne fournit aucune de ces pièces. Le nom « La
borne qui écoute » peut aggraver la perception de surveillance.

**Preuve / source.** CNIL, « Assistants vocaux : les bons réflexes pour les
professionnels » : privacy by design, local plutôt que distant, moyens de
contrôle, adaptation au média vocal, finalité, base légale, minimisation, durée,
sécurité, information, droits. AI Act, article 50 : à partir du 2 août 2026, les
personnes doivent être informées qu'elles interagissent avec une IA, sauf si cela
ressort clairement du contexte.

**Action.** Ajouter sur la borne et dans la démo : « Appuyez pour parler. Votre
voix est transformée en texte, l'audio n'est pas conservé. Réponse analysée par
une IA. » Faire relire par un DPO avant tout pilote. Supprimer toute ambiguïté
sur l'absence d'écoute permanente.

### R5 — « L'IA va se tromper. »

**Contre-argument.** La classification est contrainte : chaque question a des
options fermées, une option « non mentionné » et une règle de `NULL` en cas de
doute. Les réponses brutes sont conservées, les avis peuvent être reclassifiés,
et l'équipe vise au moins 8 classifications correctes sur 10. Ce n'est pas un
chatbot qui improvise : c'est un extracteur de signaux, avec une sortie
vérifiable.

**Limite honnête.** Il n'existe pas encore de benchmark sur des voix réelles de
visiteurs. Les accents, le bruit, les phrases implicites et les changements de
langue peuvent produire des erreurs. La note globale est **toujours inférée**,
même quand la personne n'a pas exprimé de note : c'est un risque
d'interprétation à assumer.

**Preuve / source.** `demo/jev.py` : options fermées, `non_mentionne`, `NULL`,
`jev_raw`. `context/demo_live_avis.md` §4 et §13 : règle « missing data »,
objectif 8/10.

**Action.** Annoter 50 à 100 audios réels, mesurer par critère la précision et
les confusions, ajuster les seuils, et afficher « score inféré » pour la note.
Présenter un exemple d'erreur et la façon dont elle est rattrapée : c'est plus
convaincant qu'une promesse de perfection.

### R6 — « Quelques centimes par avis », c'est faux

**Contre-argument.** « Quelques centimes » désigne le coût marginal de l'appel
de classification. Ce n'est pas le coût du service. Le coût complet inclut le
boîtier, le micro, le bouton, la batterie ou le solaire, l'installation, le
raccordement électrique, la connectivité, la maintenance, le nettoyage, le
vandalisme, les pièces détachées, la supervision, le traitement, l'analyse et la
gouvernance. À faible volume, les coûts fixes dominent.

**Limite honnête.** Nous n'avons ni devis fournisseur, ni modèle de coût, ni
hypothèse de volume. Le deck compare « 24 h d'enquête » à « quelques centimes »,
mais les deux ne mesurent pas la même chose : une enquête achète de la
représentativité, une borne achète de la continuité.

**Preuve / source.** Le deck lui-même liste CAPEX et OPEX, mais sans chiffres.
La comparaison honnête est un **coût par réponse exploitable** et un **coût par
décision**, pas un coût par appel API.

**Action.** Construire trois scénarios (1 site, 5 sites, 50 sites) avec des
hypothèses explicites : matériel, installation, maintenance, volume d'avis,
temps d'analyse. Présenter une fourchette, pas un chiffre précis inventé.

### R7 — « Quel impact avez-vous démontré ? »

**Contre-argument.** Aucun impact causal, et nous ne le prétendons pas. Le POC
démontre la **faisabilité** : une conversation peut être captée, transcrite,
classifiée et restituée en quelques secondes, avec des signaux utiles. La
plausibilité de l'impact vient de la littérature et des cadres existants :
Eco-Compteur documente une baisse d'insatisfaction de 53 % à 19 % dans un parc
après diagnostic et action ; Isère Attractivité utilise les perceptions dans son
optimum touristique.

**Limite honnête.** Ces résultats ne sont pas attribuables à notre borne. Il
manque un protocole avant/après, un site témoin, une baseline et des indicateurs
de décision.

**Preuve / source.** Eco-Compteur, cas des Monts tabulaires ; Isère Attractivité,
optimum touristique.

**Action.** Définir dès maintenant les indicateurs du pilote : taux de
participation, part de réponses exploitables, délai entre collecte et décision,
nombre de décisions modifiées, évolution de l'insatisfaction aux pics, évolution
de la saturation des parkings, report modal. Ne pas promettre de pourcentage.

### R8 — « Vous n'utilisez pas les jeux de données fournis. »

**Contre-argument.** Le concept est pertinent pour les données du hackathon :
les ENS, les éco-compteurs, les parkings, les sites surfréquentés et les
transports sont exactement les données qui permettent de qualifier un site. Mais
la démo actuelle ne les charge pas : elle utilise les coordonnées de cinq
trailheads et des avis enregistrés par l'équipe. C'est une faiblesse réelle sur
le critère « pertinence de l'utilisation des données ».

**Limite honnête.** La série éco-compteurs ENS est mensuelle, couvre 2004–2025
avec de nombreux trous, et ne couvre pas la date de la démo. Le fichier brut
2009–2026 existe, mais il n'est pas branché. Un croisement sérieux demanderait un
appariement site / compteur, un traitement des lacunes et une règle explicite
pour les données manquantes.

**Preuve / source.** `../onyxia-data/Données à disposition - par onglet.xlsx` :
la fiche éco-compteurs ENS mentionne « beaucoup de trous » ; la fiche des données
brutes indique 2009–2026. `Sites sur-fréquentés.xlsx` contient 53 sites
fréquentés et 22 lieux conseillés. `context/demo_live_avis.md` §6 prévoit
`reference.py` et un badge « simulé ».

**Action.** Ajouter `reference.py`, charger les cinq compteurs, afficher la
moyenne mensuelle avec la période source et le badge « simulé ». Ajouter une
slide « données utilisées » avec le nombre de lignes, la granularité et les
limites. Si ce n'est pas fait avant le jury, l'assumer : « la démo montre la
couche qualitative ; le croisement est la prochaine étape. »

### R9 — « Votre carte de saturation n'existe pas dans la démo. »

**Contre-argument.** Exact. Le slide 5 présente la carte de saturation comme une
réutilisation possible ; la démo affiche une carte des avis, colorée par source,
et une vue « saturation » qui compte les mentions. Ce sont deux choses
différentes. La bonne réponse est de ne pas défendre l'ambiguïté : la carte de
saturation est une **cible**, pas un livrable.

**Limite honnête.** Implémenter un vrai croisement en quelques heures est
possible mais risqué : il faut choisir une formule, normaliser des séries
hétérogènes, gérer les trous et éviter de faire passer une moyenne historique
pour une mesure temps réel.

**Preuve / source.** `slidev/slides.md` slide 5 ; `demo/app.py` : carte
`pydeck` des points, vue `saturation` = histogramme.

**Action.** Soit implémenter un indicateur simple et assumé (« affluence
ressentie moyenne × moyenne mensuelle du compteur, badge simulé »), soit
requalifier la slide en « perspectives ». Ne pas laisser le jury découvrir
l'écart tout seul.

### R10 — « Vous parlez de 5 sites pilotes : lesquels, avec qui ? »

**Contre-argument.** Ce sont des **sites candidats**, choisis pour la démo parce
qu'ils sont connus, lisibles sur une carte et représentatifs de massifs
différents. Le déploiement cible, lui, viserait des ENS équipés d'éco-compteurs et
disposant d'un parking, d'une alimentation électrique et d'un gestionnaire
intéressé. La différence est une question de stade, pas de concept.

**Limite honnête.** Aucune convention, aucun accès terrain, aucune installation.
La spec et le pitch ne listent pas les mêmes sites, ce qui peut donner
l'impression d'un flou.

**Preuve / source.** `demo/bornes.py` : cinq trailheads. `context/demo_live_avis.md`
§5 : cinq ENS avec compteurs de référence. Aucun document de partenariat.

**Action.** Dire « sites candidats » ; expliquer les critères de sélection ;
aligner la spec et le pitch ; si possible, obtenir une lettre d'intérêt d'un
gestionnaire avant le jury.

### R11 — « Une borne en montagne : énergie, réseau, vandalisme, maintenance ? »

**Contre-argument.** Ce sont les contraintes normales d'un objet outdoor, et
elles sont prises en compte dans le récit de déploiement : boîtier renforcé,
pièces standard, batterie/solaire, stockage local et synchronisation différée,
supervision, alerte si la borne devient silencieuse. Le POC assume le risque
réseau : le STT est local, seule la classification a besoin d'Internet ; en cas
d'échec, l'avis est conservé en erreur et reclassifiable.

**Limite honnête.** Rien de tout cela n'est testé. Le POC tourne sur un laptop,
avec le réseau de la salle. Il n'y a ni BOM, ni test d'humidité, ni test de
froid, ni estimation de durée de vie.

**Preuve / source.** `context/demo_live_avis.md` §10 (risques, go/no-go) ;
notes du deck sur la robustesse.

**Action.** Pour le pilote : un seul site, un boîtier durci, une alimentation
solaire, une connectivité 4G avec buffer local, une supervision et un contrat de
maintenance. Documenter les coûts et les délais.

### R12 — « Pourquoi ne pas simplement utiliser Isère Outdoor ou les avis Google ? »

**Contre-argument.** Isère Outdoor est un excellent canal de diffusion, mais il
est centré itinéraire et pratique : il ne produit pas un tableau de bord de flux
ni un croisement avec les compteurs. Les avis Google ont l'échelle, mais ils sont
publics, non structurés, dépendants d'une plateforme, non localisés finement et
non représentatifs. La borne produit un signal **local, structuré, possédé par
le gestionnaire**, avec un consentement et une provenance maîtrisés. Les trois
sources sont complémentaires.

**Limite honnête.** Aucune intégration Isère Outdoor n'est faite ; aucun accord
API n'est signé. On ne sait pas si les visiteurs accepteront de parler à une
borne alors qu'ils peuvent déjà noter dans l'app.

**Preuve / source.** Isère Outdoor : notation/commentaires sur les itinéraires,
ENS, tag transport en commun. Google : pas de contrôle, pas de structuration.

**Action.** Proposer un module ou un lien depuis Isère Outdoor, pas une app
concurrente. Comparer sur un site les biais des avis Google et des avis borne.

### R13 — « Le code n'est pas prêt : pas sur `main`, pas de licence. »

**Contre-argument.** Le code existe, il tourne, il est testé dans la branche
démo. Les manques sont des manques de **packaging**, pas de conception : fusion
des branches, licence, README, CI, version du modèle. Ce sont des corrections
rapides.

**Limite honnête.** En l'état, le dépôt `main` ne contient ni la démo ni les
slides ; le règlement exige un code open source Apache 2.0 ou MIT avec
documentation ; le fichier `LICENSE` est absent ; la CI racine ne lance pas les
tests de la démo ; la version Jev par défaut diffère de la spec.

**Preuve / source.** État Git : `origin/feat/demo-live-avis`,
`origin/slidev-presentation`, `main` ; `datasets/sources_py/pyproject.toml`
déclare MIT ; aucun `LICENSE` racine ; `pyproject.toml` racine ne liste que
`datasets/sources_py/tests`.

**Action.** Fusionner sur `main`, ajouter `LICENSE` MIT, aligner Jev, ajouter un
README démo avec architecture, données, limites et commandes, brancher les tests
démo dans la CI, faire tourner `make check`.

### R14 — « Votre recommandation peut créer de nouveaux pics. »

**Contre-argument.** C'est un risque réel, et il est explicitement identifié
dans les documents de cadrage : avant de prendre des mesures, il faut anticiper
les effets de report vers des sites non dimensionnés. La borne ne recommande
rien en elle-même ; elle observe. Si un jour elle alimente une recommandation,
celle-ci devra être **capacity-aware** : ne pas promouvoir un site sans vérifier
sa charge, plafonner les redirections, suivre l'effet sur le site d'accueil, et
ne pas transformer un « spot secret » en nouveau point de saturation.

**Limite honnête.** Le deck évoque une app et une gamification qui pourraient
inciter à visiter plus de sites. Ce n'est pas implémenté, mais c'est un signal
contradictoire avec l'objectif de gestion raisonnée.

**Preuve / source.** France Tourisme Durable : identifier les risques d'effets de
report avant d'agir. `context/topo_prez.md` : « la recommandation ne doit pas
créer de nouveaux points de saturation ».

**Action.** Écrire un principe de conception : « pas de recommandation sans
capacité vérifiée ». Remplacer la gamification par des badges de **comportement
responsable** (partage, respect, transport en commun), pas de badges de visite.

### R15 — « Et le passage à l'échelle ? »

**Contre-argument.** Le code est paramétré par sites (`bornes.py`) et la logique
est agnostique du territoire : un autre département, c'est un autre fichier de
sites et un autre jeu de compteurs. Le STT est local, la stack est open source,
et l'architecture SQLite → API → dashboard peut être déployée progressivement.

**Limite honnête.** Le passage à l'échelle est surtout **organisationnel** :
accords d'installation, alimentation, connectivité, maintenance, gouvernance des
données, capacité d'analyse, conformité RGPD. Le code n'est pas le facteur
limitant.

**Preuve / source.** `context/demo_live_avis.md` §12 : POC → pilote → production.
La spec prévoit un `bornes.yaml` par territoire.

**Action.** Séquence réaliste : 1 site / 1 saison → 5 sites → département. Un
go/no-go à chaque étape, avec des critères explicites (participation, qualité,
coût, impact, conformité).

## 5. Questions secondaires et réponses courtes

| Question probable | Réponse courte |
|---|---|
| Combien de personnes ont parlé ? | Dans le POC, uniquement l'équipe. Le taux de participation réel est inconnu : c'est un des objets du pilote. |
| Quelles langues ? | Whisper multilingue, français par défaut, détection verrouillée par enregistrement. Les accents et le code-switching restent à tester. |
| Et les personnes sourdes ou malentendantes ? | La voix seule les exclut. Il faut un canal texte/QR alternatif ; c'est une condition d'accessibilité, pas une option. |
| Combien de temps conservez-vous les données ? | À définir avec le DPO. Principe : pas d'audio, minimisation des transcripts, agrégation, durée limitée et documentée. |
| Qui est responsable de traitement ? | L'autorité qui déploie la borne (collectivité, gestionnaire de site). Pas l'équipe du POC. À clarifier avant le pilote. |
| Où sont hébergées les données ? | Dans le POC, SQLite local. En production, à définir : hébergement UE, sous-traitant, sécurité, sauvegarde. |
| OpenRouter / Jev est-il un sous-traitant ? | Techniquement, un appel API à un fournisseur de modèle. Il faut un contrat, une base légale, une analyse de transfert et une politique de rétention. |
| Et si l'API tombe ? | Le STT local continue ; l'avis est stocké en erreur et reclassifiable. La démo doit être répétée avec le réseau coupé. |
| Et si le micro est sale, exposé au vent ? | Risque réel. Boîtier, bonnette, seuil VAD, test en conditions de salle puis en extérieur. |
| Comment éviter les faux avis ? | Présence physique, une conversation par enregistrement, limitation de débit, modération, pas d'incitation à la note positive. |
| La note 1–5 est-elle une échelle validée ? | Non. C'est un score inféré, utile pour trier, pas une mesure psychométrique. À trianguler. |
| Pourquoi Jev et pas un LLM généraliste ? | Sorties contraintes, options fermées, confiance, coût et reproductibilité. Contrepartie : dépendance à un fournisseur. |
| Quel est le ROI ? | Pas de ROI démontré. La valeur est de mieux cibler les investissements (parking, signalétique, navettes) et d'éviter des crises. À mesurer. |
| Pourquoi pas un questionnaire de 3 questions ? | C'est moins cher et plus facile à échantillonner. La borne teste l'hypothèse du verbatim spontané et de la faible friction ; il faut comparer. |
| Quel lien avec la capacité de charge ? | Le ressenti est une des trois entrées (comptage, capacité écologique, ressenti). La borne ne calcule pas la capacité de charge. |
| Avez-vous parlé à Eco-Compteur / Isère Attractivité ? | Les experts étaient présents au hackathon ; aucun partenariat formel n'est signé. Le projet s'appuie sur leurs cadres. |
| Pourquoi le nom « La borne qui écoute » ? | Il est mémorable mais peut évoquer la surveillance. Le sous-titre « livre d'or numérique » et la signalétique push-to-talk corrigent le cadrage. |
| Et si on vous demande une démo maintenant ? | Démo live sur le laptop ; captures et vidéo de secours ; scénario de repli sans réseau. |
| Le code est-il vraiment open source ? | Intention MIT, mais `LICENSE` manquant et branches non fusionnées. À corriger avant soumission. |
| Les données sont-elles ouvertes ? | Le code peut l'être ; les données du hackathon ne sont pas toutes publiables. Les données personnelles ne doivent jamais l'être. |

## 6. Ce qu'il ne faut pas dire

| Ne pas dire | Dire plutôt |
|---|---|
| « On remplace les enquêtes de satisfaction. » | « On complète les enquêtes avec un signal continu, local et non représentatif. » |
| « C'est représentatif. » | « C'est un signal qualitatif auto-sélectionné ; on affiche `n` et on ne généralise pas. » |
| « On croise en temps réel avec les éco-compteurs. » | « Le croisement est la cible ; la démo montre la couche ressenti. » |
| « Ça coûte quelques centimes par avis. » | « Le coût marginal de l'IA est faible ; le coût complet reste à modéliser. » |
| « On a 5 sites pilotes. » | « On a 5 sites candidats pour la démo. » |
| « C'est anonyme, donc il n'y a pas de RGPD. » | « La voix reste une donnée personnelle ; on minimise, on informe et on documente. » |
| « L'IA comprend tout. » | « La classification est contrainte, avec `NULL` si incertain ; on mesure l'erreur. » |
| « On va réduire la fréquentation de X %. » | « On veut outiller la décision ; l'impact reste à mesurer. » |
| « C'est prêt pour la production. » | « C'est un POC bout en bout, pas un produit. » |
| « Toutes les données sont ouvertes. » | « Le code est open source ; les données du hackathon ne sont pas toutes publiables. » |
| « C'est comme Catch'em'all. » | « Une mécanique de contribution, sans marque tierce. » |
| « On a une carte de saturation. » | « On a une carte des avis ; la saturation croisée est une cible. » |
| « Le code est sur `main`. » | « Il est sur des branches ; on fusionne avant soumission. » |
| « On a une licence. » | « MIT est déclarée ; le fichier `LICENSE` doit être ajouté. » |
| « La borne est accessible à tous. » | « On vise l'accessibilité ; il faut un canal texte alternatif. » |

## 7. Check-list avant le jury

### Priorité 0 — à faire avant de monter sur scène

- [ ] Fusionner `origin/feat/demo-live-avis` et `origin/slidev-presentation` dans
      `main` ; vérifier que le dépôt public montre la démo et le pitch.
- [ ] Ajouter un `LICENSE` MIT à la racine ; aligner la mention dans les
      `pyproject.toml`.
- [ ] Remplacer le placeholder du slide 3 par des captures ou le direct.
- [ ] Aligner les sites : pitch, spec et démo doivent raconter la même histoire.
- [ ] Remplacer « sites pilotes » par « sites candidats ».
- [ ] Requalifier la « carte de saturation » en cible, ou l'implémenter.
- [ ] Remplacer « quelques centimes par avis » par une formulation TCO.
- [ ] Ajouter la mention « réponse analysée par IA » et l'information push-to-talk.
- [ ] Épingler la version de Jev et documenter le fallback réseau.
- [ ] Préparer des captures et une vidéo de secours ; répéter deux fois, dont une
      avec le réseau coupé.
- [ ] Vérifier le livrable écrit exigé par l'article 3.1 : README détaillé ou
      rapport de synthèse présentant la démarche, les données utilisées et la
      technique.

### Priorité 1 — si le temps le permet

- [ ] Ajouter `reference.py`, charger les cinq séries éco-compteurs, afficher la
      période source et le badge « simulé ».
- [ ] Ajouter une slide « données utilisées » : ENS, éco-compteurs, sites
      surfréquentés, transports, avec granularité et limites.
- [ ] Ajouter un canal texte/QR de repli pour l'accessibilité.
- [ ] Ajouter une slide « limites » : ce que le POC ne prouve pas.
- [ ] Brancher les tests de la démo dans la CI racine.
- [ ] Vérifier les licences des modèles et du fournisseur Jev.

### Priorité 2 — après le hackathon

- [ ] Pilote sur un site, avec convention, alimentation, connectivité et
      maintenance.
- [ ] AIPD / revue DPO, base légale, durée de conservation, information.
- [ ] Protocole d'évaluation d'impact avec site témoin.
- [ ] Intégration Isère Outdoor ou API d'agrégats.
- [ ] Modèle de coût complet et scénarios de déploiement.
- [ ] Documentation technique reproductible : architecture, schéma de données,
      procédure d'installation, guide de contribution.

## 8. Sources

### Documents internes

- `context/reglement_hackathon.md`, articles 3.1, 7 et 11 : livrables, critères
  du jury, licence Apache 2.0 ou MIT, propriété intellectuelle.
- `context/topo_prez.md`, sections 2 à 8 : chiffres Isère, problématiques,
  données, experts, critères.
- `context/demo_live_avis.md`, sections 1 à 14 : spec de la démo, sites ENS,
  éco-compteurs, Jev, RGPD, définition de fait.
- `context/ideation_claude_pendant_prez.md`, section 10 : pistes, conventions,
  pièges connus (granularités, doublons, pannes de compteurs, cars scolaires).
- `slidev/slides.md`, branche `origin/slidev-presentation` : pitch, notes orales,
  slide 5 « carte de saturation », annexes RGPD et architecture.
- `demo/`, branche `origin/feat/demo-live-avis` : `app.py`, `worker.py`,
  `jev.py`, `stats.py`, `bornes.py`, `tests/`, `README.md`.
- `datasets/sources_py/pyproject.toml` : déclaration de la licence MIT.
- `pyproject.toml` racine : workspace, `testpaths`, `make check`.
- `../onyxia-data/Données à disposition - par onglet.xlsx` : inventaire,
  granularité, qualité, lacunes.
- `../onyxia-data/Sites et équipements/Sites sur-fréquentés.xlsx` : 53 sites
  fréquentés, 22 lieux conseillés.
- `../onyxia-data/Fréquentation/données_eco_compteurs_ENS.xlsx` : série mensuelle
  2004–2025, nombreux trous ; fichier brut 2009–2026 signalé dans l'inventaire.

### Sources externes

- DGE, « Gestion des flux touristiques : entre attractivité locale et protection
  du patrimoine », 80 % de l'activité sur 20 % du territoire, quatre axes :
  <https://www.entreprises.gouv.fr/priorites-et-actions/proximite-et-territoires/renforcer-le-secteur-du-tourisme/gestion-des-flux>
- France Tourisme Durable, « Gestion des flux touristiques », quatre étapes
  (Observer, gouvernance, stratégie, former/sensibiliser/communiquer) et
  avertissement sur les effets de report :
  <https://www.francetourismedurable.gouv.fr/fr/gestion-des-flux-touristiques>
- Eco-Compteur, « Gérer les pics de fréquentation », indicateurs quantitatifs et
  qualitatifs, seuils à trois entrées, prédiction à quatre jours glissants, cas
  des Monts tabulaires (53 % → 19 %) :
  <https://www.eco-compteur.com/espaces-naturels/gerer-pics-frequentation>
- Isère Attractivité, « L'optimum : repenser la fréquentation touristique des
  territoires », croisement données objectives / perceptions, pilotes
  Les Deux-Alpes, Saint-Antoine-l'Abbaye, Allevard-les-Bains :
  <https://isere-attractivite.com/observatoire/optimum-touristique/>
- Isère Outdoor, accueil et page application, itinéraires, ENS, notation et
  commentaires, tag transport en commun :
  <https://isereoutdoor.fr/> et <https://isereoutdoor.fr/fr/page/84>
- CNIL, « Assistants vocaux : les bons réflexes pour les professionnels »,
  privacy by design, local plutôt que distant, moyens de contrôle, règles RGPD :
  <https://www.cnil.fr/fr/assistants-vocaux-les-bons-reflexes-pour-les-professionnels>
- CNIL, dossier « Assistants vocaux » :
  <https://www.cnil.fr/fr/dossier-assistants-vocaux>
- AI Act, article 50, obligations de transparence, entrée en application le
  2 août 2026 :
  <https://artificialintelligenceact.eu/fr/article/50/>
- Règlement (UE) 2024/1689, texte officiel :
  <https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32024R1689>

---

**Rappel final.** Le jury peut pardonner un POC incomplet. Il pardonnera
difficilement une promesse non tenue. La meilleure défense n'est pas d'avoir
raison sur tout : c'est de savoir exactement ce qui est démontré, ce qui ne l'est
pas, et ce qu'il faudrait faire pour le démontrer.
