"""
Ballot adapter — public votes.

Source: {base}/static/openData/repository/{legislature}/loi/scrutins/Scrutins.json.zip
"""

import json
from datetime import date
from typing import Any

from src.domain.entities.ballot import Ballot, BallotVote, GroupVote, VotePosition
from src.domain.ports.sources.ballot_source import BallotSource
from src.domain.ports.storage import RawStoragePort
from src.domain.shared.validators import Legislature
from src.infrastructure.http.archive import iter_zip_members
from src.infrastructure.http.client import HttpClient

ARCHIVE_PATH = "/static/openData/repository/{legislature}/loi/scrutins/Scrutins.json.zip"
MEMBER_PREFIX = "json/"
UNKNOWN_GROUP = "PO0"

# JSON list name -> position. nonVotantsVolontaires is never filled nominatively.
POSITIONS = {
    "pours": VotePosition.FOR,
    "contres": VotePosition.AGAINST,
    "abstentions": VotePosition.ABSTENTION,
    "nonVotants": VotePosition.NON_VOTING,
    "nonVotantsVolontaires": VotePosition.NON_VOTING_VOLUNTARY,
}


def _as_list(value: Any) -> list:
    """One child is a dict, several a list, none is null — and lists may hold nulls."""
    if value is None:
        return []
    return [v for v in (value if isinstance(value, list) else [value]) if v is not None]


def _votants(block: Any) -> list[dict]:
    """`{"votant": …}` or a list of those -> flat list of votant dicts."""
    return [v for entry in _as_list(block) for v in _as_list(entry.get("votant"))]


def _int(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value[:10]) if value else None
    except ValueError:
        return None


class AnBallotAdapter(BallotSource):
    def __init__(self, http: HttpClient, storage: RawStoragePort, base_url: str) -> None:
        self._http = http
        self._storage = storage
        self._base_url = base_url.rstrip("/")
        self._cache: dict[int, bytes] = {}
        self.last_s3_key: str | None = None

    def archive_url(self, legislature: int) -> str:
        return self._base_url + ARCHIVE_PATH.format(legislature=legislature)

    async def _archive(self, legislature: int) -> bytes:
        if legislature not in self._cache:
            payload = await self._http.get_bytes(self.archive_url(legislature))
            self.last_s3_key = await self._storage.put(
                f"raw/ballots/{legislature}/Scrutins.json.zip",
                payload,
                content_type="application/zip",
            )
            self._cache[legislature] = payload
        return self._cache[legislature]

    async def fetch_all(
        self,
        legislature: Legislature,
        *,
        since: date | None = None,
        until: date | None = None,
        limit: int | None = None,
    ) -> list[Ballot]:
        payload = await self._archive(legislature)
        ballots: list[Ballot] = []
        for _, content in iter_zip_members(payload, prefix=MEMBER_PREFIX, suffix=".json"):
            ballot = self._parse(content)
            if ballot is None:
                continue
            if (since and ballot.date < since) or (until and ballot.date > until):
                continue
            ballots.append(ballot)
            if limit is not None and len(ballots) >= limit:
                break
        ballots.sort(key=lambda b: b.number)
        return ballots

    async def fetch_by_uid(self, uid: str, legislature: Legislature) -> Ballot | None:
        payload = await self._archive(legislature)
        for _, content in iter_zip_members(payload, prefix=f"{MEMBER_PREFIX}{uid}.json"):
            return self._parse(content)
        return None

    # -- parsing: pure function, covered by tests/adapters ----------------------

    @classmethod
    def _parse(cls, raw: bytes) -> Ballot | None:
        s = json.loads(raw).get("scrutin")
        if not s or not s.get("uid") or not s.get("seanceRef"):
            return None
        kind = s.get("typeVote") or {}
        synthesis = s.get("syntheseVote") or {}
        counts = synthesis.get("decompte") or {}
        objet = s.get("objet") or {}
        dossier = objet.get("dossierLegislatif") or {}

        groups, votes = cls._parse_groups(s)
        cls._apply_corrections(s.get("miseAuPoint") or {}, votes)

        return Ballot(
            uid=s["uid"],
            legislature=int(s.get("legislature") or 0),
            number=int(s.get("numero") or 0),
            agenda_uid=s["seanceRef"],
            session_ref=s.get("sessionRef"),
            date=_date(s.get("dateScrutin")),
            kind=kind.get("codeTypeVote"),
            kind_label=kind.get("libelleTypeVote"),
            majority_rule=kind.get("typeMajorite"),
            result=(s.get("sort") or {}).get("code"),
            title=s.get("titre"),
            requested_by=(s.get("demandeur") or {}).get("texte"),
            dossier_uid=dossier.get("dossierRef"),
            location=s.get("lieuVote"),
            voters=_int(synthesis.get("nombreVotants")),
            expressed=_int(synthesis.get("suffragesExprimes")),
            required=_int(synthesis.get("nbrSuffragesRequis")),
            for_count=_int(counts.get("pour")) or 0,
            against_count=_int(counts.get("contre")) or 0,
            abstention_count=_int(counts.get("abstentions")) or 0,
            non_voting_count=_int(counts.get("nonVotants")) or 0,
            non_voting_voluntary_count=_int(counts.get("nonVotantsVolontaires")) or 0,
            groups=groups,
            votes=votes,
        )

    @staticmethod
    def _parse_groups(s: dict) -> tuple[list[GroupVote], list[BallotVote]]:
        groups: list[GroupVote] = []
        votes: list[BallotVote] = []
        organe = (s.get("ventilationVotes") or {}).get("organe") or {}
        for g in _as_list((organe.get("groupes") or {}).get("groupe")):
            # "PO0": the AN could not tell the group (12 scrutins). Votes keep no group.
            group_uid = g.get("organeRef")
            if not group_uid or group_uid == UNKNOWN_GROUP:
                group_uid = None
            vote = g.get("vote") or {}
            by_count = vote.get("decompteVoix") or {}
            if group_uid:
                groups.append(
                    GroupVote(
                        group_uid=group_uid,
                        members=_int(g.get("nombreMembresGroupe")),
                        majority_position=vote.get("positionMajoritaire"),
                        for_count=_int(by_count.get("pour")) or 0,
                        against_count=_int(by_count.get("contre")) or 0,
                        abstention_count=_int(by_count.get("abstentions")) or 0,
                        non_voting_count=_int(by_count.get("nonVotants")) or 0,
                    )
                )
            nominative = vote.get("decompteNominatif") or {}
            for key, position in POSITIONS.items():
                for votant in _votants(nominative.get(key)):
                    if not votant.get("acteurRef"):
                        continue
                    votes.append(
                        BallotVote(
                            deputy_uid=votant["acteurRef"],
                            mandate_uid=votant.get("mandatRef"),
                            group_uid=group_uid,
                            position=position,
                            by_delegation=str(votant.get("parDelegation")).lower() == "true",
                        )
                    )
        return groups, votes

    @staticmethod
    def _apply_corrections(corrections: dict, votes: list[BallotVote]) -> None:
        """Mises au point: the deputy says what they meant; the cast vote is kept as is."""
        by_deputy = {v.deputy_uid: v for v in votes}
        for key, position in POSITIONS.items():
            for votant in _votants(corrections.get(key)):
                vote = by_deputy.get(votant.get("acteurRef"))
                if vote is not None:
                    vote.corrected_position = position
