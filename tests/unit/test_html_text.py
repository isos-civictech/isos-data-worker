from src.infrastructure.adapters.html_text import html_to_text, split_names


def test_paragraphs_and_entities():
    fragment = '<p style="x">Apr&#x00E8;s l&#x2019;alin&#x00E9;a&nbsp;34</p><p>ins&#233;rer :</p>'
    assert html_to_text(fragment) == "Après l’alinéa 34\n\ninsérer :"


def test_empty():
    assert html_to_text(None) is None
    assert html_to_text("<p></p>") is None


def test_names():
    assert split_names(" Mme&#160;Dupont,  M.&#160;Jean&#160;Martin et Mme Durand") == [
        "Mme Dupont",
        "M. Jean Martin",
        "Mme Durand",
    ]
    assert split_names(None) == []
