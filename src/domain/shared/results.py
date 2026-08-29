"""
Résultats d'exécution — le vocabulaire commun des cas d'usage.

Ces objets appartiennent au domaine parce qu'ils décrivent ce qui s'est passé en
termes métier ("42 députés traités, 2 en échec"), sans rien savoir de HTTP, de
SQL ni de la ligne de commande. C'est ce qui permet à une route FastAPI et à une
commande CLI de renvoyer exactement la même chose sans se connaître.

Ce sont des dataclasses et non des modèles Pydantic : aucune donnée extérieure
n'entre ici, il n'y a donc rien à valider.
"""
from dataclasses import dataclass, field
from datetime import UTC, datetime

# Au-delà de ce taux d'échec, un run est considéré comme raté même s'il est allé
# au bout. C'est l'alarme « l'Assemblée a changé son format » : sans elle, un
# parseur cassé produit des runs verts et une base qui se vide en silence.
FAILURE_RATE_THRESHOLD = 0.2


def _now() -> datetime:
    return datetime.now(tz=UTC)


@dataclass(frozen=True)
class SaveOutcome:
    """
    Ce qu'un dépôt renvoie après avoir écrit une entité.

    `created` distingue une insertion d'une mise à jour. C'est la seule
    information dont le cas d'usage a besoin pour tenir ses compteurs, et c'est
    aussi ce qui rend le contrôle d'idempotence lisible : au deuxième run,
    `created` doit être faux partout.
    """

    entity_id: int | str
    created: bool


@dataclass
class SyncReport:
    """
    Compte-rendu d'un run, renvoyé tel quel par le CLI et par l'API.

    Les compteurs sont volontairement séparés :
        processed  vu dans la source
        created    inséré
        updated    déjà présent, mis à jour
        skipped    ignoré volontairement (dry-run, type sans destination)
        failed     erreur inattendue, journalisée, run poursuivi
    """

    entity: str
    started_at: datetime = field(default_factory=_now)
    finished_at: datetime | None = None

    processed: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0

    # Identifiants des entités en échec, pour pouvoir les rejouer à la main.
    # Volontairement borné : une liste de 600 uid dans une réponse HTTP n'aide
    # personne, les traces complètes sont dans les logs.
    errors: list[str] = field(default_factory=list)

    ERROR_SAMPLE_SIZE = 20

    def record_failure(self, uid: str) -> None:
        self.failed += 1
        if len(self.errors) < self.ERROR_SAMPLE_SIZE:
            self.errors.append(uid)

    def finish(self) -> "SyncReport":
        self.finished_at = _now()
        return self

    @property
    def duration_s(self) -> float | None:
        if self.finished_at is None:
            return None
        return (self.finished_at - self.started_at).total_seconds()

    @property
    def ok(self) -> bool:
        """
        Un run reste acceptable tant que les échecs restent marginaux.

        Zéro traité n'est pas un succès : c'est le symptôme d'une source vide ou
        d'un filtre trop strict, et ça doit sortir en code de retour non nul.
        """
        if self.processed == 0:
            return False
        return self.failed / self.processed <= FAILURE_RATE_THRESHOLD

    def as_dict(self) -> dict:
        """Forme sérialisable, utilisée par les logs et par les routes HTTP."""
        return {
            "entity": self.entity,
            "ok": self.ok,
            "processed": self.processed,
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "failed": self.failed,
            "duration_s": self.duration_s,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "errors": self.errors,
        }
