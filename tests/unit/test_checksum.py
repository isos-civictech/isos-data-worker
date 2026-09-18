from src.infrastructure.persistence.checksum import sha256_bytes, sha256_text


def test_whitespace_changes_do_not_create_a_new_version():
    """
    The whole point of normalising: a reflowed line break in the source must not
    produce a brand new article version saying exactly the same thing.
    """
    original = "Art. 1er. — Le présent article est ainsi rédigé."
    reflowed = "Art. 1er. —   Le présent article\n   est ainsi rédigé."

    assert sha256_text(original) == sha256_text(reflowed)


def test_real_text_changes_are_detected():
    assert sha256_text("Le taux est de 20 %.") != sha256_text("Le taux est de 25 %.")


def test_text_and_bytes_answer_different_questions():
    """
    sha256_text drives versioning (normalised), sha256_bytes drives the
    ingestion log (byte for byte). They must not be interchangeable.
    """
    text = "a  b"
    assert sha256_text(text) != sha256_bytes(text.encode())


def test_is_stable_across_calls():
    assert sha256_text("stable") == sha256_text("stable")
