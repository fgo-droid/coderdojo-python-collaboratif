# L’Aquarium connecté — palier 3

Atelier collaboratif : Python déplace les habitants, p5.js les dessine. Aucune installation de paquet : Python 3.8 ou plus récent et un navigateur suffisent. Une connexion Internet est nécessaire pour charger p5.js depuis son CDN.

## Démarrer

Depuis le dossier du dépôt, lancez désormais une seule commande :

```console
python aquarium_dojo/serveur.py
```

Ouvrez ensuite http://localhost:8000 et cliquez dans l’eau pour déposer de la
nourriture. Arrêtez auparavant l’ancien serveur HTTP et l’ancienne simulation
avec Ctrl+C : `serveur.py` fait maintenant les deux. Depuis `aquarium_dojo`,
la commande est simplement `python serveur.py`. Le port est configurable avec
`--port 8001` si nécessaire. Ctrl+C arrête le serveur et sa simulation.

### Ancien lancement sans interactions

Pour utiliser uniquement le pont JSON, ouvrez deux terminaux :

1. Lancez la simulation dans le premier :

   ```console
   python aquarium_dojo/simulation.py
   ```

2. Lancez le serveur dans le second :

   ```console
   python -m http.server 8000 --bind 127.0.0.1 --directory aquarium_dojo
   ```

3. Ouvrez [l’aquarium](http://localhost:8000). Arrêtez chaque terminal avec `Ctrl+C`.

Le fichier `etat.json` fourni permet de commencer le dessin sans lancer Python. Dans ce cas, les habitants restent immobiles, tandis que le décor s’anime. Ouvrir directement `index.html` via `file://` ne permet pas de lire le JSON : utilisez le serveur HTTP.

## Répartition des équipes

- **Codeurs** : `aquarium_dojo/simulation.py`, déplacements et rebonds à 20 cycles/s.
- **Designers** : `aquarium_dojo/index.html` et `sketch.js`, dessin à 60 images/s et lecture toutes les 100 ms environ.
- **Contrat commun** : `etat.json`, objet `monde` (`largeur`, `hauteur`, `moment`, `temperature`, `temps`) et liste `entites`. Chaque entité possède `id`, `type`, `x`, `y`, `vx`, `vy`, `taille`, `energie`, `etat`. Les vitesses sont exprimées en pixels par cycle Python ; le monde mesure 800 × 600 pixels.

Les types sont `poisson`, `requin`, `algue`. Les états sont `nage`, `chasse`, `pousse`, `repos`, `fuite`, `affame` et `mange`.

Les poissons fuient un requin à moins de 170 pixels et cherchent des algues si leur énergie est inférieure à 100. Le requin poursuit un poisson à moins de 260 pixels. À moins de 45 pixels, manger transfère jusqu’à 0,8 point d’énergie par cycle. Les animaux dépensent 0,015 point par cycle et leur énergie reste entre 0 et 150. Les algues épuisées restent visibles en gris. Manger retire de l’énergie sans supprimer la proie : la mort et la reproduction restent au palier 4. Relancez Python pour réinitialiser le monde lorsque les ressources sont épuisées.

Une barre indique l’énergie de chaque habitant sur une échelle de 150. Son état est affiché au-dessus ; les poissons en fuite rougissent et leurs yeux s’agrandissent, le requin ouvre la bouche pendant la chasse et les repas.

Après un repas, les poissons rassasiés reprennent leur nage et ne recherchent de
nouveau de la nourriture que sous 50 points d’énergie. Le booléen
`cherche_nourriture` mémorise ce comportement dans chaque poisson (au premier
cycle, un poisson sous 100 points commence par chercher un repas). Les algues
avec moins de 10 points sont ignorées pour leur laisser le temps de repousser.
Ces deux règles évitent que les poissons restent à brouter au même endroit.

Python écrit un temporaire unique dans le même dossier puis utilise `os.replace` : les lecteurs voient un fichier complet. Les conflits temporaires d’accès Windows sont réessayés ; si le fichier reste occupé, l’ancien instantané est conservé. Plusieurs écrivains ne partagent pas leur temporaire, mais le dernier remplacement gagne : utilisez une seule simulation pour un monde cohérent. Le navigateur conserve son dernier état en cas d’erreur et réessaie sans superposer les requêtes.

## Vérifier

```console
python -m unittest discover -s tests -v
python aquarium_dojo/simulation.py --cycles 10
```

À l’écran : les poissons et le requin rebondissent, les algues restent ancrées. Arrêter puis relancer Python doit figer puis reprendre les déplacements sans recharger la page.

## Paliers suivants

1. Chaîne alimentaire : distances, énergie, fuite et alimentation.
2. Jour/nuit : alternance, température et effet sur la simulation.
3. Interaction : serveur Python recevant les clics pour nourrir les poissons.
4. Populations : reproduction, mort et courbes d’évolution.

Les paliers 1 à 3 sont réalisés. Le palier 4 reste à réaliser.

### Interaction humaine

Un clic envoie `POST /action?x=300&y=200`. Le serveur valide les coordonnées
et ajoute une entité `nourriture` : taille 6, énergie 30, état `disponible`,
champ `expiration` en secondes du monde. Chaque paquet reste au maximum 20 s ;
40 paquets peuvent être présents. Les identifiants sont uniques grâce au champ
`monde.prochain_id`. Les poissons sous 100 points privilégient ces paquets aux
algues ; fuir un requin reste prioritaire. Les poissons rassasiés continuent de
nager. Un paquet consommé disparaît au cycle suivant.

Un verrou protège les actions, la simulation et la lecture HTTP de l’état.
Le fichier JSON est toujours publié atomiquement pour les autres lecteurs.
L’interaction de ce palier sert à nourrir ; les clics ne font pas fuir le requin.

### Cycle jour/nuit

Le monde démarre de jour et alterne toutes les 30 secondes réelles grâce à une
horloge monotone. Le contrat `monde` ajoute `temperature` (22 °C le jour,
20 °C la nuit) et `temps` (secondes écoulées depuis le lancement). La température
est indicative et ne modifie pas les comportements.

La nuit, toutes les vitesses des poissons sont divisées par deux, y compris la
fuite ; les requins gardent leur vitesse. Les algues passent à l’état `repos`
et cessent de repousser. Le jour, elles récupèrent 0,04 point d’énergie par cycle,
jusqu’à 150, même après épuisement ; elles peuvent toujours être mangées la nuit.
La taille des algues reste constante : la croissance recharge leur énergie.

L’eau et le sable s’assombrissent progressivement. Les poissons dont l’identifiant
est pair émettent un halo nocturne. Les bulles et les ondulations restent animées.
Le statut affiche le moment et la température. Pour vérifier un cycle complet,
laissez tourner Python au moins 60 secondes : jour, nuit à 30 s, jour à 60 s.

## Versions de l’atelier

La branche principale contient la dernière version du projet. Chaque étape terminée
est conservée par un tag Git permanent ; les tags des paliers futurs seront créés
uniquement lorsque leur réalisation sera terminée et vérifiée.

| Étape | Tag | Contenu | Statut |
| --- | --- | --- | --- |
| 0 | `aquarium-etape-0` | Pont JSON, déplacements, rebonds et affichage p5.js | Réalisée |
| 1 | `aquarium-palier-1` | Chaîne alimentaire : logique de distance et esthétique | Réalisée |
| 2 | `aquarium-palier-2` | Cycle jour/nuit et environnement | Réalisée |
| 3 | `aquarium-palier-3` | Interaction humaine : boucle retour front → back | Réalisée |
| 4 | `aquarium-palier-4` | Dynamique des populations et équilibrage | À réaliser |

Pour consulter l’étape zéro dans un dossier séparé depuis le dépôt :

```console
git worktree add --detach ../aquarium-etape-0 aquarium-etape-0
```

Ce dossier contient tout le dépôt à cette étape. Lancez les commandes de démarrage
depuis ce dossier. Les développements suivants continuent dans le dossier d’origine.
Sur GitHub, le sélecteur de branches et de tags permet aussi de consulter ou de
télécharger chaque version sans installer Git.
