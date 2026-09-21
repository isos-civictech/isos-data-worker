"""
Ballot — one public vote ("scrutin") in the hémicycle, with every deputy's position.

Source: {base}/static/openData/repository/{legislature}/loi/scrutins/Scrutins.json.zip
        (~26 MB, json/VTANR5L17V{n}.json, one file per scrutin)

JSON field mapping (root key: scrutin):
    uid              → uid                                  "VTANR5L17V2657"
    legislature      → legislature
    number           → numero
    sitting_uid      → seanceRef                            "RUANR5L17S2025IDS29580" = agenda uid
    session_ref      → sessionRef                           "SCR5A2025O1"
    date             → dateScrutin
    kind             → typeVote/codeTypeVote                SPO | SPS | MOC
    kind_label       → typeVote/libelleTypeVote             "scrutin public ordinaire"
    majority_rule    → typeVote/typeMajorite
    result           → sort/code                            adopté | rejeté
    title            → titre                    "l'amendement n° 585 de M. Pauget à l'article 10…"
    requested_by     → demandeur/texte            who asked for a public vote
    dossier_uid      → objet/dossierLegislatif/dossierRef   set in ~30 % of files
    location         → lieuVote                             Hémicycle | Salons
    voters/expressed/required → syntheseVote/{nombreVotants,suffragesExprimes,nbrSuffragesRequis}
    for_count…       → syntheseVote/decompte/{pour, contre, abstentions, nonVotants, …Volontaires}
    groups           → ventilationVotes/organe/groupes/groupe[]   (see GroupVote)
    votes            → …/groupe[]/vote/decompteNominatif/{pours,contres,…}/votant[]
    corrections      → miseAuPoint/{pours,contres,abstentions,nonVotants}/votant[]
                       a deputy stating afterwards what they meant to vote
Every list can be a dict when it has one element, and null when empty.
"""

import re
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, computed_field

from src.domain.shared.validators import Legislature, NotBlankStr


class BallotKind(StrEnum):
    ORDINARY = "SPO"  # scrutin public ordinaire
    SOLEMN = "SPS"  # scrutin public solennel
    CENSURE_MOTION = "MOC"  # motion de censure: only the "pour" are counted


class VotePosition(StrEnum):
    FOR = "pour"
    AGAINST = "contre"
    ABSTENTION = "abstention"
    NON_VOTING = "nonVotant"  # present but did not vote, or absent
    NON_VOTING_VOLUNTARY = "nonVotantVolontaire"  # the président, or a deputy who stated it


# "l'amendement n° 585", "l’amendement de suppression n° 444", "le sous-amendement n° 40".
_AMENDMENT_NUMBER = re.compile(r"(?:sous-)?amendement(?: de \w+)? n°\s*([\w-]+)", re.I)


class BallotVote(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    deputy_uid: NotBlankStr
    mandate_uid: str | None = None
    group_uid: str | None = None
    position: VotePosition
    by_delegation: bool = False
    # Position declared afterwards in the "mises au point"; the cast vote stands.
    corrected_position: VotePosition | None = None


class GroupVote(BaseModel):
    """How one political group voted: majority line and counts."""

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    group_uid: NotBlankStr
    members: int | None = None
    majority_position: str | None = None
    for_count: int = 0
    against_count: int = 0
    abstention_count: int = 0
    non_voting_count: int = 0


class Ballot(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    uid: NotBlankStr
    legislature: Legislature
    number: int
    sitting_uid: NotBlankStr
    session_ref: str | None = None
    date: date
    kind: BallotKind
    kind_label: str | None = None
    majority_rule: str | None = None
    result: str | None = None
    title: str | None = None
    requested_by: str | None = None
    dossier_uid: str | None = None
    location: str | None = None
    voters: int | None = None
    expressed: int | None = None
    required: int | None = None
    for_count: int = 0
    against_count: int = 0
    abstention_count: int = 0
    non_voting_count: int = 0
    non_voting_voluntary_count: int = 0
    groups: list[GroupVote] = []
    votes: list[BallotVote] = []

    @computed_field
    @property
    def adopted(self) -> bool:
        return self.result == "adopté"

    @computed_field
    @property
    def amendment_number(self) -> str | None:
        """'585' from "l'amendement n° 585 de M. Pauget…"; None when the vote is on a text."""
        match = _AMENDMENT_NUMBER.search(self.title or "")
        return match.group(1) if match else None
