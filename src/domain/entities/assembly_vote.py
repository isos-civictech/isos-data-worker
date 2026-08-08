"""
Assembly vote — a formal vote in the National Assembly.

Source: Scrutins JSON
    ZIP: https://data.assemblee-nationale.fr/static/openData/repository/
        {legislature}/loi/scrutins/Scrutins.json.zip

JSON field mapping:
    uid              → scrutin/uid
    legislature      → scrutin/legislature
    vote_number      → scrutin/numero
    debate_uid       → scrutin/seanceRef             ← links to Debate
    amendment_uid    → scrutin/amendementRef          ← None = vote on full text
    texte_uid        → scrutin/texteLegislatifRef     ← links to Law
    date             → scrutin/dateScrutin
    vote_type        → scrutin/typeVote/libelleTypevote
    title            → scrutin/titre
    result           → scrutin/syntheseVote/libelleMajorite
    votes_in_favor   → scrutin/syntheseVote/decompte/pour
    votes_against    → scrutin/syntheseVote/decompte/contre
    abstention_count → scrutin/syntheseVote/decompte/abstentions
    non_voting_count → scrutin/syntheseVote/decompte/nonVotants
    votes            → scrutin/ventilationVotes/organe[]/groupe[]/vote[]
"""
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, ConfigDict, Field, field_validator
from src.domain.shared.validators import Legislature, NotBlankStr

class VoteResult(str, Enum):
    ADOPTED = "adopté"
    REJECTED = "aejeté"
    
class VotePosition(str, Enum):
    IN_FAVOR  = "pour"
    AGAINST   = "contre"
    ABSTENTION = "abstention"
    NON_VOTING = "nonVotant"
    
class Voter(BaseModel):
    """One deputy's individual vote record."""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    deputy_uid: NotBlankStr
    mandate_uid: str | None = None
    by_delegation: bool = False

class NominalVoteCount(BaseModel):
    """Individual votes grouped by position — mirrors source JSON structure."""
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    in_favor: list[Voter] = Field(default_factory=list, alias="pours")
    against: list[Voter] = Field(default_factory=list, alias="contres")
    abstention: list[Voter] = Field(default_factory=list, alias="abstentions")
    non_voting: list[Voter] = Field(default_factory=list, alias="nonVotants")
    non_voting_voluntary: list[Voter] = Field(
        default_factory=list, alias="nonVotantsVolontaires"
    )

class RollCallVote(BaseModel):
    """Individual vote by one deputy on an assembly vote."""
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

    deputy_uid: NotBlankStr
    mandate_uid: str | None = None
    position: VotePosition
    by_delegation: bool = False

class AssemblyVote(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

    uid: NotBlankStr
    legislature: Legislature
    vote_number: int
    debate_uid: NotBlankStr
    amendment_uid: str | None = None
    texte_uid: str | None = None
    date: datetime
    vote_type: str
    title: str | None = None
    result: VoteResult | None = None
    votes_in_favor: int = 0
    votes_against: int = 0
    abstention_count: int = 0
    non_voting_count: int = 0
    roll_call_votes: NominalVoteCount = Field(default_factory=NominalVoteCount)
    
    @field_validator("votes_in_favor", "votes_against", "abstention_count", "non_voting_count")
    @classmethod
    def must_be_positive(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Vote count cannot be negative")
        return v
