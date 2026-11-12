"""Serveur local et simulation : python aquarium_dojo/serveur.py."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import time
from urllib.parse import parse_qs, urlsplit

import simulation


class Aquarium:
    def __init__(self):
        self.donnees = simulation.creer_monde()
        self.verrou = threading.Lock()
        self.arret = threading.Event()

    def tourner(self):
        origine = time.monotonic()
        while not self.arret.is_set():
            debut = time.monotonic()
            with self.verrou:
                simulation.avancer(self.donnees, temps=debut - origine)
                simulation.sauvegarder(self.donnees, simulation.DOSSIER / "etat.json")
            self.arret.wait(max(0, 0.05 - (time.monotonic() - debut)))


class Requetes(SimpleHTTPRequestHandler):
    def __init__(self, *args, aquarium, **kwargs):
        self.aquarium = aquarium
        super().__init__(*args, directory=str(simulation.DOSSIER), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def repondre(self, code, contenu):
        corps = json.dumps(contenu, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self):
        chemin = urlsplit(self.path).path
        if chemin == "/action":
            self.repondre(405, {"erreur": "Utilisez POST"})
        elif chemin in ("/", "/index.html", "/sketch.js", "/etat.json"):
            # Le navigateur lit réellement le fichier publié atomiquement.
            super().do_GET()
        else:
            self.send_error(404)

    def do_POST(self):
        url = urlsplit(self.path)
        if url.path != "/action":
            self.send_error(404)
            return
        try:
            params = parse_qs(url.query)
            x, y = float(params["x"][0]), float(params["y"][0])
            with self.aquarium.verrou:
                accepte = simulation.ajouter_nourriture(self.aquarium.donnees, x, y)
            self.repondre(201 if accepte else 429, {"accepte": accepte})
        except (ValueError, KeyError, IndexError):
            self.repondre(400, {"erreur": "Coordonnées invalides"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    aquarium = Aquarium()
    if not simulation.sauvegarder(aquarium.donnees, simulation.DOSSIER / "etat.json"):
        raise SystemExit("Impossible de publier l'état initial : etat.json est occupé.")
    with ThreadingHTTPServer(("127.0.0.1", args.port), partial(Requetes, aquarium=aquarium)) as serveur:
        fil = threading.Thread(target=aquarium.tourner)
        fil.start()
        print(f"Aquarium : http://localhost:{args.port} — Ctrl+C pour arrêter")
        try:
            serveur.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            aquarium.arret.set()
            fil.join()


if __name__ == "__main__":
    main()
