from src.domain.entities.amendment import Amendment, AmendmentStatus


def _a(**kw):
    return Amendment(uid="A", legislature=17, texte_uid="T", author_type="Député", **kw)


def test_sort_wins():
    assert _a(sort="Adopté").status == AmendmentStatus.ADOPTED
    assert _a(sort="Non soutenu").status == AmendmentStatus.UNSUPPORTED


def test_state_when_no_sort():
    assert _a(state="Irrecevable 40", sub_state="Charge").status == AmendmentStatus.INADMISSIBLE
    assert _a(state="Retiré").status == AmendmentStatus.WITHDRAWN
    assert _a(state="A discuter").status == AmendmentStatus.PENDING


def test_article_ref():
    assert _a(division_title="Article 1er", division_position="Avant").article_ref == (
        "Avant l'article 1er"
    )
    assert _a(division_title="Annexe", division_position="A").article_ref == "Annexe"
    assert _a().article_ref is None
