"""
GovernmentRole — a ministerial post held by an actor (minister, secrétaire d'État).

Source: AMO30 (see deputy.py), `mandat` nodes with typeOrgane == MINISTERE and
xsi:type MandatSimple_Type. The MandatMission_Type ones ("en mission" for the
government) are not posts and are ignored; GOUVERNEMENT mandats only say the
person sits in the cabinet, the MINISTERE one says which ministry.

XML field mapping:
    uid          → mandat/uid
    deputy_uid   → mandat/acteurRef
    title        → mandat/infosQualite/libQualiteSex     "Ministre déléguée", "Secrétaire d'État"
    ministry_uid → mandat/organes/organeRef              "PO873654"
    ministry     → organe/PO{id}.xml/libelle             "Ministère de l'Économie…"
    start        → mandat/dateDebut
    end          → mandat/dateFin                        (empty = in office)
"""

from datetime import date

from pydantic import BaseModel, ConfigDict

from src.domain.shared.validators import NotBlankStr


class GovernmentRole(BaseModel):
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    uid: NotBlankStr
    deputy_uid: NotBlankStr
    title: str | None = None
    ministry_uid: str | None = None
    ministry: str | None = None
    start: date | None = None
    end: date | None = None
