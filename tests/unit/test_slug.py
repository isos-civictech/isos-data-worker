from src.infrastructure.persistence.serving.slug import deputy_slug, slugify


def test_accents_and_spaces():
    assert deputy_slug("Jean-Luc", "Mélenchon") == "jean-luc-melenchon"


def test_apostrophes_and_double_names():
    assert deputy_slug("Amélia", "Lakrafi d'Estrées") == "amelia-lakrafi-d-estrees"


def test_is_stable():
    assert slugify("François Hollande") == slugify("François Hollande")


def test_never_ends_with_a_dash():
    assert not slugify("Nom -").endswith("-")
