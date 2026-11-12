import http.client
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aquarium_dojo"))
import serveur
import simulation


class InteractionTests(unittest.TestCase):
    def test_nourriture_mangee_et_expiree(self):
        monde = simulation.creer_monde()
        poisson = next(e for e in monde["entites"] if e["type"] == "poisson")
        monde["entites"] = [poisson]
        simulation.ajouter_nourriture(monde, poisson["x"], poisson["y"])
        simulation.avancer(monde, temps=0)
        self.assertEqual(poisson["etat"], "mange")
        self.assertGreater(poisson["energie"], 80)
        simulation.avancer(monde, temps=20)
        self.assertEqual(len(monde["entites"]), 1)

    def test_limite_et_coordonnees(self):
        monde = simulation.creer_monde()
        for x, y in ((float("nan"), 0), (0, float("inf")), (-1, 0), (801, 0)):
            with self.assertRaises(ValueError):
                simulation.ajouter_nourriture(monde, x, y)
        for _ in range(40):
            self.assertTrue(simulation.ajouter_nourriture(monde, 100, 100))
        self.assertFalse(simulation.ajouter_nourriture(monde, 100, 100))
        ids = [e["id"] for e in monde["entites"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_http_clic_et_etat(self):
        aquarium = serveur.Aquarium()
        with ThreadingHTTPServer(("127.0.0.1", 0), partial(serveur.Requetes, aquarium=aquarium)) as serveur_http:
            fil = threading.Thread(target=serveur_http.serve_forever)
            fil.start()
            try:
                client = http.client.HTTPConnection("127.0.0.1", serveur_http.server_port, timeout=5)
                for methode, chemin, statut in (
                    ("GET", "/", 200), ("POST", "/action?x=300&y=200", 201),
                    ("POST", "/action?x=nan&y=0", 400),
                    ("GET", "/action?x=0&y=0", 405), ("GET", "/etat.json", 200),
                ):
                    client.request(methode, chemin)
                    reponse = client.getresponse()
                    self.assertEqual(reponse.status, statut)
                    reponse.read()
                client.close()
                self.assertEqual(aquarium.donnees["entites"][-1]["type"], "nourriture")
            finally:
                serveur_http.shutdown()
                fil.join()

