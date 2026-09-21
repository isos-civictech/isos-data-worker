"""Welcome page."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["home"])

_PAGE = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>isos-data-worker</title>
<style>
  :root { color-scheme: light dark; }
  body { font-family: ui-sans-serif, system-ui, sans-serif; line-height: 1.6;
         max-width: 46rem; margin: 3rem auto; padding: 0 1.25rem; }
  h1 { margin-bottom: .25rem; }
  .sub { color: #6b7280; margin-top: 0; }
  h2 { margin-top: 2.5rem; font-size: 1.05rem; color: #6b7280;
       text-transform: uppercase; letter-spacing: .05em; }
  code { background: rgba(127,127,127,.15); padding: .1rem .35rem; border-radius: .25rem; }
  table { border-collapse: collapse; width: 100%; }
  td { padding: .4rem .6rem .4rem 0; vertical-align: top; }
  td:first-child { white-space: nowrap; font-family: ui-monospace, monospace; }
  .flow { background: rgba(127,127,127,.08); padding: 1rem; border-radius: .5rem;
          font-family: ui-monospace, monospace; font-size: .85rem;
          white-space: pre; overflow-x: auto; }
</style>
</head>
<body>
  <h1>isos-data-worker</h1>
  <p class="sub">Collecte des données ouvertes de l'Assemblée nationale.</p>

  <h2>Le flux</h2>
  <div class="flow">Assemblée nationale
      │  collecte  (réseau, lent)
      ▼
  schéma raw      les faits, tels que publiés
      │  projection  (SQL seul, aucun réseau)
      ▼
  schéma public   ce que le front affiche</div>

  <h2>État</h2>
  <table>
    <tr><td><a href="/health">GET /health</a></td><td>le service répond</td></tr>
    <tr><td><a href="/health/db">GET /health/db</a></td><td>la base répond</td></tr>
    <tr><td><a href="/jobs">GET /jobs</a></td><td>historique des collectes</td></tr>
    <tr><td><a href="/jobs/summary">GET /jobs/summary</a></td><td>résumé par entité</td></tr>
  </table>

  <h2>Déclencher</h2>
  <table>
    <tr><td>POST /sync/deputies</td><td><b>tout d'un coup</b> : Assemblée → raw → public.
        Ajoute ou met à jour, c'est la même chose.</td></tr>
    <tr><td>POST /sync/deputies/{uid}</td><td>un seul député, jusqu'à public</td></tr>
    <tr><td>POST /collect/deputies</td><td>Assemblée → raw seulement — options
        <code>legislature</code>, <code>limit</code>, <code>dry_run</code></td></tr>
    <tr><td>POST /collect/deputies/{uid}</td><td>un seul, raw seulement</td></tr>
    <tr><td>POST /project/deputies</td><td>raw → public seulement, sans réseau —
        à relancer après une correction de projection</td></tr>
    <tr><td>POST /sync/debates</td><td>les comptes rendus de séance — options
        <code>since</code>, <code>until</code> (YYYY-MM-DD)</td></tr>
    <tr><td>POST /sync/agenda</td><td>l'ordre du jour : séances passées, annulées et
        <b>à venir</b> — mêmes options</td></tr>
    <tr><td>GET /agenda/today</td><td>ce qui est à l'ordre du jour aujourd'hui</td></tr>
    <tr><td>GET /agenda/upcoming</td><td>les prochaines séances</td></tr>
    <tr><td>POST /sync/laws</td><td>les dossiers législatifs : projets et propositions de
        loi, leurs lectures, et le lien <code>debate_law</code> vers les séances —
        à lancer <b>après</b> l'agenda</td></tr>
    <tr><td>GET /laws/{uid}</td><td>un dossier (DLR…) et ses étapes, tel que collecté</td></tr>
    <tr><td>POST /sync/amendments</td><td>les amendements, séance et commission — archive de
        340 Mo, comptez quelques minutes ; options <code>dossier</code>, <code>since</code>.
        À lancer <b>après</b> les lois et les députés</td></tr>
    <tr><td>GET /laws/{uid}/amendments</td><td>les amendements d'un dossier</td></tr>
  </table>

  <h2>En ligne de commande</h2>
  <div class="flow">python -m src.interfaces.cli collect-deputies --limit 5 --dry-run
python -m src.interfaces.cli collect-deputies --legislature 17
python -m src.interfaces.cli project-deputies</div>

  <h2>Documentation</h2>
  <p><a href="/docs">/docs</a> — référence OpenAPI interactive.</p>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
async def home() -> str:
    return _PAGE
