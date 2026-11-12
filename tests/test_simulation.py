import importlib.util
import json
import math
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "simulation", Path(__file__).resolve().parents[1] / "aquarium_dojo" / "simulation.py"
)
simulation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(simulation)


def creer_monde_test():
    """Scénario fixe, indépendant des habitants ajoutés/retirés en atelier."""
    monde = simulation.creer_monde()
    poissons = [e for e in monde["entites"] if e["type"] == "poisson"]
    algues = [e for e in monde["entites"] if e["type"] == "algue"]
    requin = {"id": 99, "type": "requin", "x": 600, "y": 150,
              "vx": -3, "vy": 1, "taille": 60, "energie": 90, "etat": "chasse"}
    monde["entites"] = [poissons[0], requin, algues[0], poissons[1], algues[1]]
    return monde


class SimulationTests(unittest.TestCase):
    def test_poisson_quitte_son_repas_et_attend_la_faim(self):
        monde = creer_monde_test()
        poisson, algue = monde["entites"][0], monde["entites"][2]
        monde["entites"] = [poisson, algue]
        poisson.update(x=400, y=530, energie=149.8, cherche_nourriture=True)
        simulation.avancer(monde, temps=0)
        self.assertEqual(poisson["etat"], "mange")
        for _ in range(160):
            simulation.avancer(monde, temps=0)
        self.assertFalse(poisson["cherche_nourriture"])
        self.assertGreater(simulation.distance(poisson, algue), 80)
        poisson["energie"] = 49
        simulation.avancer(monde, temps=0)
        self.assertTrue(poisson["cherche_nourriture"])

    def test_algue_presque_vide_ignoree(self):
        monde = creer_monde_test()
        poisson, algue = monde["entites"][0], monde["entites"][2]
        monde["entites"] = [poisson, algue]
        poisson.update(x=400, y=530, vx=0, vy=-2, energie=30)
        algue["energie"] = 0.1
        simulation.avancer(monde, temps=0)
        self.assertNotEqual(poisson["etat"], "mange")
        self.assertLess(poisson["vy"], 0)
    def test_cycle_et_temperature_aux_frontieres(self):
        monde = creer_monde_test()
        for temps, moment, temperature in (
            (29.99, "jour", 22), (30, "nuit", 20),
            (59.99, "nuit", 20), (60, "jour", 22), (150, "nuit", 20),
        ):
            simulation.avancer(monde, temps=temps)
            self.assertEqual(monde["monde"]["moment"], moment)
            self.assertEqual(monde["monde"]["temperature"], temperature)

    def test_poissons_ralentissent_sans_ralentissement_cumulatif(self):
        monde = creer_monde_test()
        poisson = monde["entites"][0]
        monde["entites"] = [poisson]
        for temps, vitesse in ((0, 2), (30, 1), (31, 1), (60, 2)):
            simulation.avancer(monde, temps=temps)
            self.assertAlmostEqual(math.hypot(poisson["vx"], poisson["vy"]), vitesse)

    def test_fuite_nocturne_et_requin(self):
        monde = creer_monde_test()
        poisson, requin = monde["entites"][:2]
        poisson.update(x=300, y=300)
        requin.update(x=400, y=300)
        simulation.avancer(monde, temps=30)
        self.assertEqual(poisson["etat"], "fuite")
        self.assertAlmostEqual(math.hypot(poisson["vx"], poisson["vy"]), 2)
        self.assertAlmostEqual(math.hypot(requin["vx"], requin["vy"]), 4.5)

    def test_algues_repoussent_uniquement_le_jour(self):
        monde = creer_monde_test()
        algue = monde["entites"][2]
        monde["entites"] = [algue]
        algue["energie"] = 1
        simulation.avancer(monde, temps=30)
        self.assertEqual(algue["energie"], 1)
        self.assertEqual(algue["etat"], "repos")
        simulation.avancer(monde, temps=60)
        self.assertAlmostEqual(algue["energie"], 1.12)
        self.assertEqual(algue["etat"], "pousse")
        algue["energie"] = 149
        simulation.avancer(monde, temps=61)
        self.assertAlmostEqual(algue["energie"], 149.12)

    def test_rebonds_et_algues(self):
        monde = creer_monde_test()
        algue = monde["entites"][2].copy()
        for _ in range(1500):
            simulation.avancer(monde)
            for e in monde["entites"]:
                self.assertTrue(0 <= e["x"] <= simulation.LARGEUR)
                self.assertTrue(0 <= e["y"] <= simulation.HAUTEUR)
        self.assertEqual((algue["x"], algue["y"]),
                         (monde["entites"][2]["x"], monde["entites"][2]["y"]))

    def test_fuite_et_chasse(self):
        monde = creer_monde_test()
        poisson, requin = monde["entites"][:2]
        poisson.update(x=300, y=300)
        requin.update(x=400, y=300)
        simulation.avancer(monde)
        self.assertEqual(poisson["etat"], "fuite")
        self.assertLess(poisson["vx"], 0)
        self.assertEqual(requin["etat"], "chasse")
        self.assertAlmostEqual(math.hypot(requin["vx"], requin["vy"]), 4.5)

    def test_poisson_mange_algue(self):
        monde = creer_monde_test()
        poisson = monde["entites"][0]
        algue = monde["entites"][2]
        poisson.update(x=400, y=530)
        simulation.avancer(monde)
        self.assertEqual(poisson["etat"], "mange")
        self.assertGreater(poisson["energie"], 80)
        self.assertLess(algue["energie"], 100)

    def test_requin_mange_poisson_et_energie_bornee(self):
        monde = creer_monde_test()
        poisson, requin = monde["entites"][:2]
        poisson.update(x=300, y=300, energie=0.2)
        requin.update(x=300, y=300)
        simulation.avancer(monde)
        self.assertEqual(requin["etat"], "mange")
        self.assertEqual(poisson["energie"], 0)
        self.assertGreater(requin["energie"], 90)
        for _ in range(5000):
            simulation.avancer(monde)
        self.assertTrue(all(0 <= e["energie"] <= 150 for e in monde["entites"]))

    def test_lectures_et_ecritures_concurrentes(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as dossier:
            destination = Path(dossier) / "etat.json"
            simulation.sauvegarder(creer_monde_test(), destination)
            erreurs = []

            def ecrire():
                try:
                    monde = creer_monde_test()
                    for _ in range(80):
                        simulation.avancer(monde)
                        simulation.sauvegarder(monde, destination)
                except Exception as erreur:
                    erreurs.append(erreur)

            fils = [threading.Thread(target=ecrire) for _ in range(2)]
            for fil in fils:
                fil.start()
            lectures = 0
            try:
                while any(fil.is_alive() for fil in fils):
                    try:
                        with destination.open(encoding="utf-8") as fichier:
                            self.assertEqual(len(json.load(fichier)["entites"]), 5)
                        lectures += 1
                    except PermissionError:
                        # Windows peut refuser une ouverture pendant os.replace.
                        continue
            finally:
                for fil in fils:
                    fil.join()
            self.assertGreater(lectures, 0)
            self.assertEqual(erreurs, [])
            self.assertEqual(list(Path(dossier).glob("*.tmp")), [])

    def test_fichier_occupe_conserve_ancien_etat(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent) as dossier:
            destination = Path(dossier) / "etat.json"
            simulation.sauvegarder(creer_monde_test(), destination)
            ancien = destination.read_bytes()
            with patch.object(simulation.os, "replace", side_effect=PermissionError):
                self.assertFalse(simulation.sauvegarder({}, destination))
            self.assertEqual(destination.read_bytes(), ancien)
            self.assertEqual(list(Path(dossier).glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
