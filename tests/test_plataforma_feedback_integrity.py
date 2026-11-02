import pytest

from trazia.extraction import Candidate
from trazia.feedback import Feedback, extraction_prompt, prioritize, using
from trazia.model import Source
from trazia.vision.prompts import TASKS


def sample():
    return Candidate(
        path="diameter",
        value=2000,
        unit="mm",
        channel="ocr",
        source=Source(document_id="SYNTHETIC", page=1, locator="fixture", confidence=0.8),
    )


def test_unverified_profile_never_changes_prompt_or_confidence():
    c = sample()
    spec = TASKS["lineas"]
    profile = Feedback(examples=({"after": 2000},), priorities={"ocr": 1.15}, verified=False)
    with using(profile):
        assert extraction_prompt(spec) == (spec.prompt, spec.prompt_sha256)
        assert prioritize([c]) == [c]
    assert (
        profile.sha256 != Feedback(examples=profile.examples, priorities=profile.priorities).sha256
    )


@pytest.mark.parametrize(
    "weight,expected", [(5, 0.92), (-5, 0.68), (float("nan"), 0.8), ("bad", 0.8)]
)
def test_runtime_enforces_bounded_finite_priorities(weight, expected):
    c = sample()
    with using(Feedback(priorities={"ocr": weight})):
        [adjusted] = prioritize([c])
    assert adjusted.source.confidence == pytest.approx(expected)
    assert adjusted.confidence_raw == 0.8
    assert c.source.confidence == 0.8
