"""Recalibración posterior a fusión y aislamiento de originales compartidos."""

from bench.recalibrar import propose


def sample():
    return [
        {
            "tag": str(tag),
            "strategy": "d_hibrido",
            "channel": "ocr",
            "media": "scan",
            "raw": 0.9,
            "correct": field % 2 == 0,
            "kind": "mm",
            "residual": 0 if field % 2 == 0 else 0.05,
        }
        for tag in range(12)
        for field in range(60)
    ]


def test_d_recalibration_is_global_after_fusion_with_three_disjoint_groups():
    rows = sample()
    candidate, report = propose(rows, None)
    assert report["status"] == "candidate"
    assert report["after"]["d_hibrido"]["ece_calibrated"] == 0
    assert {k for k in candidate.curves if k.startswith("d_hibrido|")} == {"d_hibrido|*"}
    assert "d_hibrido" not in candidate.passthrough
    groups = [
        set(candidate.meta[k]) for k in ("curve_equipment", "conformal_equipment", "test_equipment")
    ]
    assert all(groups[i].isdisjoint(groups[j]) for i in range(3) for j in range(i))
    assert set.union(*groups) == {str(t) for t in range(12)}
    assert all("calibrated" not in row for row in rows)


def test_document_copies_cannot_masquerade_as_independent_equipment():
    rows = [{**r, "document_hashes": ["a" * 64]} for r in sample()]
    candidate, report = propose(rows, None)
    assert candidate is None and report["status"] == "insufficient"
    assert report["independent_groups"] == 1


def test_transitive_document_sharing_stays_in_one_partition():
    rows = sample()
    for row in rows:
        row["document_hashes"] = {"0": ["a" * 64], "1": ["a" * 64, "b" * 64], "2": ["b" * 64]}.get(
            row["tag"], []
        )
    candidate, report = propose(rows, None)
    assert report["status"] == "candidate"
    components = candidate.meta["equipment_components"]
    assert components["0"] == ["0", "1", "2"]
