from datetime import datetime

from src.infrastructure.persistence.serving.mappers.agenda_mapper import sitting_slug, sitting_title


def test_title_matches_the_compte_rendu_wording():
    start = datetime(2024, 11, 6, 14, 0)
    assert sitting_title("Première", start) == "Première séance du mercredi 06 novembre 2024"
    assert sitting_title(None, start) == "Séance du mercredi 06 novembre 2024"


def test_slug_is_readable_and_stable():
    assert sitting_slug("Première", datetime(2024, 11, 6)) == "seance-2024-11-06-1"
    assert sitting_slug("Unique", datetime(2024, 11, 6)) == "seance-2024-11-06-unique"
