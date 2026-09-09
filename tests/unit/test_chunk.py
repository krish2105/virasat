import fitz

from virasat.rag import chunk

# A small synthetic excerpt in the JHCPR layout. Test fixture only — never indexed.
EXCERPT = """
1. Short title.- (1.) This Regulation may be called the Test Regulation.
2. Definitions.- In these regulations,
(a) "facade" means the external elevation of a building facing a street and includes its colour and materials as well as the signage fixed upon it, whether painted or projecting;
(b) "height" means the vertical distance measured from the ground to the top of the parapet or, where there is no parapet, to the top storey;
3. Building Parameters. -
3.1 Height. No new floor shall be added above the existing height in the core zone.
3.2 Colour. External walls shall be painted in the prescribed terracotta colour.
"""


def _doc() -> fitz.Document:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((40, 60), EXCERPT, fontsize=8)
    return doc


def test_clause_hierarchy_and_paths() -> None:
    chunks = {c.clause_id: c for c in chunk.parse(_doc(), "sha")}
    assert {"REG-1", "REG-2", "REG-3", "REG-3.1", "REG-3.2"} <= set(chunks)
    assert chunks["REG-3.1"].path.endswith("3. Building Parameters > 3.1 Height")
    assert chunks["REG-3.1"].section == "3"
    assert "No new floor" in chunks["REG-3.1"].text


def test_change_type_metadata_prefilters() -> None:
    chunks = {c.clause_id: c for c in chunk.parse(_doc(), "sha")}
    assert "VERTICAL_ADDITION" in chunks["REG-3.1"].applies_to_change_type
    assert "DEMOLITION" not in chunks["REG-3.1"].applies_to_change_type
    assert chunks["REG-3.2"].applies_to_change_type == ["FACADE_ALTERATION"]


def test_no_chunk_splits_mid_clause() -> None:
    for c in chunk.parse(_doc(), "sha"):
        assert not c.text.endswith(("the", "of", "and", ",")), c.clause_id
