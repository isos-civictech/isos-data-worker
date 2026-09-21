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
    <tr><td>POST /sync/all</td><td><b>tout, dans l'ordre</b> : députés, agenda, débats, lois,
        amendements, textes, scrutins — puis projection. <code>?debates=5</code> se limite aux
        5 dernières séances et à ce qu'elles touchent (les députés sont toujours tous pris)</td></tr>
    <tr><td>POST /sync/{dataset}</td><td>un jeu, collecte puis projection —
        <code>deputies laws agenda debates amendments ballots law-texts</code></td></tr>
    <tr><td>POST /collect/{dataset}</td><td>Assemblée → raw seulement. Options
        <code>limit</code>, <code>uid</code>, <code>dossier</code>, <code>since</code>,
        <code>until</code>, <code>dry_run</code>. L'archive vient de <b>notre S3</b> quand elle y
        est ; <code>refresh=true</code> force le téléchargement</td></tr>
    <tr><td>POST /project/{dataset}</td><td>raw → public seulement, sans réseau —
        à relancer après une correction de projection</td></tr>
    <tr><td>POST /refresh</td><td>re-télécharge les archives dans S3, sans toucher la base —
        <code>?datasets=laws&amp;datasets=agenda</code> pour choisir</td></tr>
  </table>

  <h2>Lire (brut)</h2>
  <table>
    <tr><td>GET /agenda/today</td><td>ce qui est à l'ordre du jour aujourd'hui</td></tr>
    <tr><td>GET /agenda/upcoming</td><td>les prochaines séances</td></tr>
    <tr><td>GET /laws/{uid}</td><td>un dossier (DLR…) et ses étapes</td></tr>
    <tr><td>GET /laws/{uid}/amendments</td><td>les amendements d'un dossier</td></tr>
    <tr><td>GET /laws/{uid}/articles/{article_ref}</td><td>un article au fil des versions,
        avec les amendements qui l'ont visé — ex. <code>Article 2</code></td></tr>
    <tr><td>GET /deputies/{uid}/votes</td><td>les derniers votes d'un député</td></tr>
    <tr><td>GET /jobs</td><td>les dernières exécutions</td></tr>
  </table>

  <h2>En ligne de commande</h2>
  <div class="flow">make sync DEBATES=5        # les 5 dernières séances et ce qu'elles touchent
make sync                  # toute la législature
make collect DS=laws       # un jeu, Assemblée → raw
make project DS=laws       # un jeu, raw → public
make refresh               # les archives, vers S3</div>

  <h2>Documentation</h2>
  <p><a href="/docs">/docs</a> — référence OpenAPI interactive.</p>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
async def home() -> str:
    return _PAGE
