"""
PoliticalGroupRef — a parliamentary group (groupe politique).

Source: AMO10 ZIP, `organe/PO{id}.xml` members with codeType == "GP".
    ZIP: https://data.assemblee-nationale.fr/static/openData/repository/
        {legislature}/amo/deputes_actifs_mandats_actifs_organes/
        AMO10_deputes_actifs_mandats_actifs_organes.xml.zip

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
