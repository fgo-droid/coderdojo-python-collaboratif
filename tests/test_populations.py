import unittest
from test_simulation import simulation


class PopulationsTests(unittest.TestCase):
    def test_division_conserve_energie_et_identifiants(self):
        for type_ in simulation.LIMITES:
            monde = simulation.creer_monde()
            parent = next(e for e in monde["entites"] if e["type"] == type_)
            monde["entites"] = [parent]
            parent["energie"] = 151
            simulation.renouveler_populations(monde)
            self.assertEqual(len(monde["entites"]), 2)
            self.assertEqual(sum(e["energie"] for e in monde["entites"]), 151)
            self.assertEqual(len({e["id"] for e in monde["entites"]}), 2)
            self.assertEqual(monde["populations"][type_], 2)

    def test_seuil_strict_et_plafond(self):
        monde = simulation.creer_monde()
        parent = monde["entites"][0]
        monde["entites"] = [parent]
        parent["energie"] = 150
        simulation.renouveler_populations(monde)
        self.assertEqual(len(monde["entites"]), 1)
        monde["entites"] = [{**parent, "id": i + 1, "energie": 200} for i in range(30)]
        simulation.renouveler_populations(monde)
        self.assertEqual(len(monde["entites"]), 30)

    def test_morts_ne_revivent_pas_et_historique_borne(self):
        monde = simulation.creer_monde()
        for e in monde["entites"]:
            e["energie"] = 0
        for _ in range(120):
            simulation.avancer(monde)
        self.assertEqual(monde["entites"], [])
        self.assertEqual(monde["populations"], {"algue": 0, "poisson": 0, "requin": 0})
        self.assertEqual(len(monde["historique"]), 100)
        self.assertEqual(monde["historique"][0]["cycle"], 21)
        self.assertTrue(simulation.ajouter_nourriture(monde, 100, 100))

    def test_reproduction_accessible_par_repas(self):
        monde = simulation.creer_monde()
        poisson = monde["entites"][0]
        monde["entites"] = [poisson]
        poisson["energie"] = 149.8
        simulation.ajouter_nourriture(monde, poisson["x"], poisson["y"])
        simulation.avancer(monde)
        self.assertEqual(monde["populations"]["poisson"], 2)

    def test_dix_minutes_sans_depassement(self):
        monde = simulation.creer_monde()
        for _ in range(12000):
            simulation.avancer(monde)
        for type_, limite in simulation.LIMITES.items():
            self.assertLessEqual(monde["populations"][type_], limite)
        self.assertTrue(all(0 < e["energie"] <= simulation.ENERGIE_MAX for e in monde["entites"]))
        self.assertEqual(len({e["id"] for e in monde["entites"]}), len(monde["entites"]))
