"""B lee el plano de orientación de boquillas (VESOR) y lo cruza con el GA (ROADMAP 2.1)."""

import random

import pytest

from synthetic.render_v2 import render_ga
from synthetic.sets import _vessel_pair
from synthetic.vendors import VENDORS
from synthetic.vesor import printed, render_vesor
from trazia.pipeline import InputDocument, process


def _case(vendor_key: str):
    vendor = VENDORS[vendor_key]
    spec, _ = _vessel_pair(random.Random(11), 3, vendor)
    return spec, vendor


def _read(docs, monkeypatch):
    monkeypatch.setenv("TRAZIA_CALIBRATION", "off")
    return process(docs, project_id="P", equipment_id="v-1", revision="1", strategy="b_reglas")


def _azimuths(result, channel):
    return {
        c.path.split(".")[1]: c.value
        for c in result.candidates
        if c.path.endswith(".azimuth") and c.channel == channel
    }


@pytest.mark.parametrize("vendor_key", ["atlas", "iberica"])
@pytest.mark.parametrize("table", [True, False])
def test_b_reads_every_orientation_from_the_vesor(vendor_key, table, monkeypatch):
    spec, vendor = _case(vendor_key)
    vesor = render_vesor(spec, vendor, table=table)
    result = _read(
        [InputDocument(f"VESOR_{spec.tag}.pdf", vesor, f"VESOR-{spec.tag}")], monkeypatch
    )
    read = _azimuths(result, "vesor")
    assert read == pytest.approx(printed(spec, vendor))
    vesor_sources = [c.source for c in result.candidates if c.channel == "vesor"]
    assert vesor_sources and all(s.document_id == f"VESOR-{spec.tag}" for s in vesor_sources)
    assert all(s.bbox is not None for s in vesor_sources)


def test_plan_labels_are_only_read_in_a_vesor(monkeypatch):
    spec, vendor = _case("atlas")
    vesor = render_vesor(spec, vendor, table=False)
    result = _read(
        [InputDocument(f"GAD_{spec.tag}_rev1.pdf", vesor, f"GA-{spec.tag}")], monkeypatch
    )
    assert _azimuths(result, "vesor") == {}


def test_a_vesor_that_disagrees_with_the_ga_is_flagged_not_silently_chosen(monkeypatch):
    spec, vendor = _case("atlas")
    nozzle = spec.nozzles[0]
    wrong = (nozzle.azimuth + 90) % 360
    ga, _ = render_ga(spec, "1", vendor)
    vesor = render_vesor(spec, vendor, azimuths={nozzle.id: wrong})
    result = _read(
        [
            InputDocument(f"GAD_{spec.tag}_rev1.pdf", ga, f"GA-{spec.tag}"),
            InputDocument(f"VESOR_{spec.tag}.pdf", vesor, f"VESOR-{spec.tag}"),
        ],
        monkeypatch,
    )
    path = f"nozzles.{nozzle.id}.azimuth"
    assert path in result.conflicts
    [chosen] = [c for c in result.candidates if c.path == path]
    others = {chosen.value, *(a.value for a in chosen.alternatives)}
    assert {
        printed(spec, vendor)[nozzle.id],
        (90 - wrong) % 360 if vendor.azimuth_convention == "cw_north" else wrong,
    } <= others
    # Las boquillas en las que coinciden no se marcan.
    agree = f"nozzles.{spec.nozzles[1].id}.azimuth"
    assert agree not in result.conflicts
