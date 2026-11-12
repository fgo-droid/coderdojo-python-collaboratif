# L’Aquarium connecté — projet initial

Atelier collaboratif : Python déplace les habitants, p5.js les dessine. Aucune installation de paquet : Python 3.8 ou plus récent et un navigateur suffisent. Une connexion Internet est nécessaire pour charger p5.js depuis son CDN.

## Démarrer

Depuis le dossier du dépôt, ouvrez deux terminaux.

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
- **Contrat commun** : `etat.json`, objet `monde` (`largeur`, `hauteur`, `moment`) et liste `entites`. Chaque entité possède `id`, `type`, `x`, `y`, `vx`, `vy`, `taille`, `energie`, `etat`. Les vitesses sont exprimées en pixels par cycle Python ; le monde mesure 800 × 600 pixels.

Gardez ce contrat stable pendant les 20 premières minutes. Les types initiaux sont `poisson`, `requin`, `algue` ; les états initiaux sont `nage`, `chasse`, `pousse`. L’énergie reste constante dans cette version et le requin se déplace sans poursuivre les poissons.

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

Ces paliers ne sont pas implémentés dans le socle initial.

## Versions de l’atelier

La branche principale contient la dernière version du projet. Chaque étape terminée
est conservée par un tag Git permanent ; les tags des paliers futurs seront créés
uniquement lorsque leur réalisation sera terminée et vérifiée.

| Étape | Tag | Contenu | Statut |
| --- | --- | --- | --- |
| 0 | `aquarium-etape-0` | Pont JSON, déplacements, rebonds et affichage p5.js | Réalisée |
| 1 | `aquarium-palier-1` | Chaîne alimentaire : logique de distance et esthétique | À réaliser |
| 2 | `aquarium-palier-2` | Cycle jour/nuit et environnement | À réaliser |
| 3 | `aquarium-palier-3` | Interaction humaine : boucle retour front → back | À réaliser |
| 4 | `aquarium-palier-4` | Dynamique des populations et équilibrage | À réaliser |

Pour consulter l’étape zéro dans un dossier séparé depuis le dépôt :

```console
git worktree add --detach ../aquarium-etape-0 aquarium-etape-0
```

Ce dossier contient tout le dépôt à cette étape. Lancez les commandes de démarrage
depuis ce dossier. Les développements suivants continuent dans le dossier d’origine.
Sur GitHub, le sélecteur de branches et de tags permet aussi de consulter ou de
télécharger chaque version sans installer Git.
