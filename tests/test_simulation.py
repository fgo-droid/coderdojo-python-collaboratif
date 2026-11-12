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


class SimulationTests(unittest.TestCase):
    def test_cycle_et_temperature_aux_frontieres(self):
        monde = simulation.creer_monde()
        for temps, moment, temperature in (
            (29.99, "jour", 22), (30, "nuit", 20),
            (59.99, "nuit", 20), (60, "jour", 22), (150, "nuit", 20),
        ):
            simulation.avancer(monde, temps=temps)
            self.assertEqual(monde["monde"]["moment"], moment)
            self.assertEqual(monde["monde"]["temperature"], temperature)

    def test_poissons_ralentissent_sans_ralentissement_cumulatif(self):
        monde = simulation.creer_monde()
        poisson = monde["entites"][0]
        monde["entites"] = [poisson]
        for temps, vitesse in ((0, 2), (30, 1), (31, 1), (60, 2)):
            simulation.avancer(monde, temps=temps)
            self.assertAlmostEqual(math.hypot(poisson["vx"], poisson["vy"]), vitesse)

    def test_fuite_nocturne_et_requin(self):
        monde = simulation.creer_monde()
        poisson, requin = monde["entites"][:2]
        poisson.update(x=300, y=300)
        requin.update(x=400, y=300)
        simulation.avancer(monde, temps=30)
        self.assertEqual(poisson["etat"], "fuite")
        self.assertAlmostEqual(math.hypot(poisson["vx"], poisson["vy"]), 2)
        self.assertAlmostEqual(math.hypot(requin["vx"], requin["vy"]), 4.5)

    def test_algues_repoussent_uniquement_le_jour(self):
        monde = simulation.creer_monde()
        algue = monde["entites"][2]
        monde["entites"] = [algue]
        algue["energie"] = 0
        simulation.avancer(monde, temps=30)
        self.assertEqual(algue["energie"], 0)
        self.assertEqual(algue["etat"], "repos")
        simulation.avancer(monde, temps=60)
        self.assertAlmostEqual(algue["energie"], 0.04)
        self.assertEqual(algue["etat"], "pousse")
        algue["energie"] = 150
        simulation.avancer(monde, temps=61)
        self.assertEqual(algue["energie"], 150)

    def test_rebonds_et_algues(self):
        monde = simulation.creer_monde()
        algue = monde["entites"][2].copy()
        for _ in range(1500):
            simulation.avancer(monde)
            for e in monde["entites"]:
                self.assertTrue(0 <= e["x"] <= simulation.LARGEUR)
                self.assertTrue(0 <= e["y"] <= simulation.HAUTEUR)
        self.assertEqual((algue["x"], algue["y"]),
                         (monde["entites"][2]["x"], monde["entites"][2]["y"]))

    def test_fuite_et_chasse(self):
        monde = simulation.creer_monde()
        poisson, requin = monde["entites"][:2]
        poisson.update(x=300, y=300)
        requin.update(x=400, y=300)
        simulation.avancer(monde)
        self.assertEqual(poisson["etat"], "fuite")
        self.assertLess(poisson["vx"], 0)
        self.assertEqual(requin["etat"], "chasse")
        self.assertAlmostEqual(math.hypot(requin["vx"], requin["vy"]), 4.5)

    def test_poisson_mange_algue(self):
        monde = simulation.creer_monde()
        poisson = monde["entites"][0]
        algue = monde["entites"][2]
        poisson.update(x=400, y=530)
        simulation.avancer(monde)
        self.assertEqual(poisson["etat"], "mange")
        self.assertGreater(poisson["energie"], 80)
        self.assertLess(algue["energie"], 100)

    def test_requin_mange_poisson_et_energie_bornee(self):
        monde = simulation.creer_monde()
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
            simulation.sauvegarder(simulation.creer_monde(), destination)
            erreurs = []

            def ecrire():
                try:
                    monde = simulation.creer_monde()
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
            simulation.sauvegarder(simulation.creer_monde(), destination)
            ancien = destination.read_bytes()
            with patch.object(simulation.os, "replace", side_effect=PermissionError):
                self.assertFalse(simulation.sauvegarder({}, destination))
            self.assertEqual(destination.read_bytes(), ancien)
            self.assertEqual(list(Path(dossier).glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()


