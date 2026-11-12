from src.infrastructure.persistence.serving.mappers.debate_mapper import transcript_html


def _row(point, title, speaker, content):
    return {
        "point_uid": point,
        "point_title": title,
        "speaker_name": speaker,
        "content": content,
    }


def test_headings_follow_agenda_points_and_text_is_escaped():
    html = transcript_html(
        [
            _row("P1", "Questions au gouvernement", "Mme Dupont", "Bonjour <tous>"),
            _row("P1", "Questions au gouvernement", "M. Martin", "Merci."),
            _row("P2", "Projet de loi", "M. Durand", "Article 1."),
        ]
    )
    assert html == (
        "<h2>Questions au gouvernement</h2>"
        "<p><strong>Mme Dupont</strong> : Bonjour &lt;tous&gt;</p>"
        "<p><strong>M. Martin</strong> : Merci.</p>"
        "<h2>Projet de loi</h2>"
        "<p><strong>M. Durand</strong> : Article 1.</p>"
    )


def test_no_speech_gives_none():
    assert transcript_html([]) is None
    assert transcript_html([_row("P1", "Titre", "X", "  ")]) is None
