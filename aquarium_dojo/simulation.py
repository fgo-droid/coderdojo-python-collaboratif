"""Pont JSON de l'aquarium : bibliothèque standard uniquement."""

import argparse
import json
import math
import os
from pathlib import Path
import tempfile
import time

LARGEUR, HAUTEUR = 800, 600
DOSSIER = Path(__file__).resolve().parent


def creer_monde():
    return {
        "monde": {"largeur": LARGEUR, "hauteur": HAUTEUR, "moment": "jour",
                  "temperature": 22, "temps": 0},
        "entites": [
            {"id": 1, "type": "poisson", "x": 250, "y": 300, "vx": 2, "vy": -1, "taille": 25, "energie": 80, "etat": "nage"},
            {"id": 2, "type": "requin", "x": 600, "y": 150, "vx": -3, "vy": 1, "taille": 60, "energie": 90, "etat": "chasse"},
            {"id": 3, "type": "algue", "x": 400, "y": 550, "vx": 0, "vy": 0, "taille": 15, "energie": 100, "etat": "pousse"},
            {"id": 4, "type": "poisson", "x": 140, "y": 180, "vx": 1.5, "vy": 0.8, "taille": 20, "energie": 80, "etat": "nage"},
            {"id": 5, "type": "algue", "x": 160, "y": 550, "vx": 0, "vy": 0, "taille": 20, "energie": 100, "etat": "pousse"},
        ],
    }


def distance(a, b):
    return math.hypot(b["x"] - a["x"], b["y"] - a["y"])


def orienter(entite, cible, vitesse, fuite=False):
    dx, dy = cible["x"] - entite["x"], cible["y"] - entite["y"]
    longueur = math.hypot(dx, dy)
    if longueur == 0:
        dx, dy, longueur = 1, 0, 1
    sens = -1 if fuite else 1
    entite["vx"] = sens * vitesse * dx / longueur
    entite["vy"] = sens * vitesse * dy / longueur


def nourrir(predateur, proie):
    quantite = min(0.8, proie["energie"], 150 - predateur["energie"])
    if quantite > 0:
        proie["energie"] -= quantite
        predateur["energie"] += quantite
        predateur["etat"] = "mange"


def ajouter_nourriture(donnees, x, y):
    if not (math.isfinite(x) and math.isfinite(y) and
            0 <= x <= LARGEUR and 0 <= y <= HAUTEUR):
        raise ValueError("Coordonnées hors de l'aquarium")
    if sum(e["type"] == "nourriture" for e in donnees["entites"]) >= 40:
        return False
    prochain = max(donnees["monde"].get("prochain_id", 1),
                   max((e["id"] for e in donnees["entites"]), default=0) + 1)
    donnees["monde"]["prochain_id"] = prochain + 1
    donnees["entites"].append({"id": prochain, "type": "nourriture", "x": x, "y": y,
                              "vx": 0, "vy": 0, "taille": 6, "energie": 30,
                              "etat": "disponible", "expiration": donnees["monde"]["temps"] + 20})
    return True


def avancer(donnees, temps=None):
    # Le programme utilise une horloge monotone ; les tests peuvent avancer
    # directement le temps sans attendre trente secondes.
    monde = donnees["monde"]
    monde["temps"] = round(monde.get("temps", 0) + 0.05, 6) if temps is None else temps
    nuit = int(monde["temps"] // 30) % 2 == 1
    monde["moment"] = "nuit" if nuit else "jour"
    monde["temperature"] = 20 if nuit else 22
    rythme = 0.5 if nuit else 1
    entites = donnees["entites"]
    entites[:] = [e for e in entites if e["type"] != "nourriture" or
                 (e["energie"] > 0 and e["expiration"] > monde["temps"])]
    # Toutes les décisions utilisent les positions du début du cycle.
    poissons = [e for e in entites if e["type"] == "poisson"]
    requins = [e for e in entites if e["type"] == "requin"]
    algues = [e for e in entites if e["type"] == "algue"]
    granules = [e for e in entites if e["type"] == "nourriture"]
    for e in entites:
        if e["type"] == "nourriture":
            continue
        if e["type"] == "algue":
            e["etat"] = "repos" if nuit else "pousse"
            if not nuit:
                e["energie"] = min(150, e["energie"] + 0.04)
            continue
        e["energie"] = max(0, e["energie"] - 0.015)
        e["etat"] = "affame" if e["energie"] < 50 else "nage"
        if e["type"] == "poisson":
            # Deux seuils évitent de revenir manger dès que l'énergie passe
            # de 100 à 99,985 au cycle suivant.
            cherche = e.get("cherche_nourriture", e["energie"] < 100)
            if e["energie"] < 50:
                cherche = True
            elif e["energie"] >= 99.9:
                cherche = False
            e["cherche_nourriture"] = cherche
            danger = min(requins, key=lambda r: distance(e, r), default=None)
            # Une algue presque vide doit repousser avant un nouveau repas.
            nourriture = min((a for a in algues if a["energie"] >= 10),
                             key=lambda a: distance(e, a), default=None)
            granule = min((g for g in granules if g["energie"] > 0),
                          key=lambda g: distance(e, g), default=None)
            if granule is not None:
                nourriture = granule
            if danger is not None and distance(e, danger) < 170:
                orienter(e, danger, 4 * rythme, fuite=True)
                e["etat"] = "fuite"
            elif nourriture is not None and (cherche or (granule is not None and e["energie"] < 100)):
                orienter(e, nourriture, 2 * rythme)
                if distance(e, nourriture) < 45:
                    nourrir(e, nourriture)
            else:
                orienter(e, {"x": e["x"] + e["vx"], "y": e["y"] + e["vy"]}, 2 * rythme)
        elif e["type"] == "requin":
            proie = min((p for p in poissons if p["energie"] > 0),
                        key=lambda p: distance(e, p), default=None)
            if proie is not None and distance(e, proie) < 260:
                orienter(e, proie, 4.5)
                e["etat"] = "chasse"
                if distance(e, proie) < 45:
                    nourrir(e, proie)
            else:
                orienter(e, {"x": e["x"] + e["vx"], "y": e["y"] + e["vy"]}, 2.5)
    for entite in donnees["entites"]:
        if entite["type"] in ("algue", "nourriture"):
            continue
        # Les marges gardent aussi les nageoires dans le cadre.
        for axe, vitesse, limite, marge in (
            ("x", "vx", LARGEUR, entite["taille"] * 1.5),
            ("y", "vy", HAUTEUR, entite["taille"]),
        ):
            entite[axe] += entite[vitesse]
            if entite[axe] < marge:
                entite[axe] = marge
                entite[vitesse] = abs(entite[vitesse])
            elif entite[axe] > limite - marge:
                entite[axe] = limite - marge
                entite[vitesse] = -abs(entite[vitesse])


def sauvegarder(donnees, destination):
    """Remplace un instantané complet, sans exposer de JSON partiel.

    Chaque écrivain utilise son propre temporaire dans le même dossier.
    Sous Windows, un lecteur peut brièvement empêcher le remplacement :
    on réessaie puis conserve le dernier état valide si le fichier reste occupé.
    """
    destination = Path(destination)
    temporaire = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=destination.parent,
            prefix=".etat-", suffix=".tmp", delete=False,
        ) as fichier:
            temporaire = Path(fichier.name)
            json.dump(donnees, fichier, ensure_ascii=False, indent=2)
            fichier.write("\n")
        for tentative in range(5):
            try:
                os.replace(temporaire, destination)
                return True
            except PermissionError:
                if tentative == 4:
                    return False
                time.sleep(0.005)
    finally:
        if temporaire is not None:
            temporaire.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cycles", type=int, help="Nombre de cycles (sinon : continu).")
    arguments = parser.parse_args()
    if arguments.cycles is not None and arguments.cycles < 0:
        parser.error("--cycles doit être positif ou nul")
    donnees = creer_monde()
    destination = DOSSIER / "etat.json"
    if not sauvegarder(donnees, destination):
        raise SystemExit("Impossible de publier l'état initial : etat.json est occupé.")
    print("Simulation active — Ctrl+C pour arrêter.")
    cycle = 0
    origine = time.monotonic()
    try:
        while arguments.cycles is None or cycle < arguments.cycles:
            debut = time.monotonic()
            avancer(donnees, temps=debut - origine)
            sauvegarder(donnees, destination)
            cycle += 1
            time.sleep(max(0, 0.05 - (time.monotonic() - debut)))
    except KeyboardInterrupt:
        print("\nSimulation arrêtée.")


if __name__ == "__main__":
    main()
