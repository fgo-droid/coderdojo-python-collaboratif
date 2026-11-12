// Équipe Designers : le contrat JSON est produit par simulation.py.
let donneesMonde = null;

async function lireEtat() {
  try {
    const reponse = await fetch('etat.json', { cache: 'no-store' });
    if (!reponse.ok) throw new Error(`HTTP ${reponse.status}`);
    const donnees = await reponse.json();
    if (!donnees.monde || !Array.isArray(donnees.entites) ||
        donnees.monde.largeur !== 800 || donnees.monde.hauteur !== 600 ||
        !donnees.entites.every(e => ['x', 'y', 'vx', 'vy', 'taille'].every(cle => Number.isFinite(e[cle])))) {
      throw new Error('Contrat JSON invalide');
    }
    donneesMonde = donnees;
    document.getElementById('statut').textContent =
      `${donnees.entites.length} habitants · ${donnees.monde.moment} · lecture du pont JSON active`;
  } catch (erreur) {
    document.getElementById('statut').textContent =
      `Lecture indisponible (${erreur.message}). Dernier état conservé, nouvelle tentative…`;
  } finally {
    // Une seule lecture à la fois, même si le serveur répond lentement.
    setTimeout(lireEtat, 100);
  }
}

function setup() {
  createCanvas(800, 600).parent('aquarium');
  frameRate(60);
  lireEtat();
}

function draw() {
  background(15, 89, 125);
  noStroke();
  for (let y = 0; y < height; y += 4) {
    fill(12, 45, 70, y / height * 150);
    rect(0, y, width, 4);
  }
  fill(183, 165, 116);
  rect(0, 565, width, 35);
  // Décor animé indépendamment des mises à jour Python.
  noFill();
  stroke(175, 229, 242, 70);
  for (let i = 0; i < 12; i++) {
    const y = height - ((frameCount * 0.7 + i * 59) % height);
    circle((i * 137 + 40) % width + sin(frameCount * 0.02 + i) * 8, y, 5 + i % 4);
  }
  if (!donneesMonde) return;
  for (const e of donneesMonde.entites) {
    push();
    translate(e.x, e.y);
    noStroke();
    if (e.type === 'algue') {
      stroke(66, 182, 132);
      strokeWeight(5);
      noFill();
      for (let i = -1; i <= 1; i++) {
        const ondulation = sin(frameCount * 0.04 + e.id + i) * 6;
        bezier(i * 8, 15, i * 12 - 10, -10, i * 10 + ondulation, -25, i * 8 + ondulation, -e.taille * 3);
      }
    } else if (e.type === 'poisson' || e.type === 'requin') {
      if (e.vx < 0) scale(-1, 1);
      const t = e.taille;
      const requin = e.type === 'requin';
      fill(requin ? '#91aaba' : (e.id % 2 ? '#ffb54c' : '#f57968'));
      triangle(-t * 0.6, 0, -t * 1.25, -t * 0.45, -t * 1.25, t * 0.45);
      if (requin) triangle(-t * 0.3, -t * 0.2, 0, -t * 0.85, t * 0.3, -t * 0.2);
      ellipse(0, 0, t * (requin ? 2 : 1.5), t * (requin ? 0.8 : 1));
      fill('#effbff');
      circle(t * 0.4, -t * 0.12, t * 0.21);
      fill('#102b3a');
      circle(t * 0.44, -t * 0.12, t * 0.1);
    }
    pop();
  }
}
