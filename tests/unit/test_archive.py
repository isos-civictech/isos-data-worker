import io
import zipfile

from src.infrastructure.http.archive import iter_zip_members


def _zip(members: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, content in members.items():
            archive.writestr(name, content)
    return buffer.getvalue()


PAYLOAD = _zip(
    {
        "acteur/PA1.xml": b"<acteur>1</acteur>",
        "acteur/PA2.xml": b"<acteur>2</acteur>",
        "organe/PO1.xml": b"<organe>1</organe>",
        "README.txt": b"ignore me",
    }
)


def test_filters_on_prefix():
    names = [name for name, _ in iter_zip_members(PAYLOAD, prefix="acteur/")]
    assert names == ["acteur/PA1.xml", "acteur/PA2.xml"]


def test_filters_on_suffix():
    names = [name for name, _ in iter_zip_members(PAYLOAD, suffix=".txt")]
    assert names == ["README.txt"]


def test_limit_stops_early():
    """This is what turns a three-minute feedback loop into a two-second one."""
    members = list(iter_zip_members(PAYLOAD, prefix="acteur/", limit=1))
    assert len(members) == 1


def test_yields_content():
    _, content = next(iter(iter_zip_members(PAYLOAD, prefix="acteur/PA1")))
    assert content == b"<acteur>1</acteur>"


def test_is_a_generator_not_a_list():
    """The Syceron archive is far too big to materialise in memory."""
    result = iter_zip_members(PAYLOAD)
    assert not isinstance(result, list)
    assert hasattr(result, "__next__")
