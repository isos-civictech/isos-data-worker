"""
PoliticalGroupRef — a parliamentary group (groupe politique).

Source: AMO30 ZIP, `organe/PO{id}.xml` members with codeType == "GP" (all legislatures: filter).
    ZIP: see deputy.py

XML field mapping (inside organe/PO{id}.xml):
    uid         → organe/uid                ("PO845401")
    name        → organe/libelle            ("Renaissance")
    short_name  → organe/libelleAbrege      ("RE", sometimes empty)
    legislature → organe/legislature        (absent on permanent organes)
"""

from pydantic import BaseModel, ConfigDict

from src.domain.shared.validators import NotBlankStr


class PoliticalGroupRef(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )

    uid: NotBlankStr
    name: NotBlankStr
    short_name: str | None = None
    legislature: int | None = None
