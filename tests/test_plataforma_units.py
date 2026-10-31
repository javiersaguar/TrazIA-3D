import pytest

from trazia.units import AmbiguousNumber, UnitError, normalize, number


@pytest.mark.parametrize(
    "text,kind,value,unit",
    [
        ("2.000,5 mm", "length", 2000.5, "mm"),
        ("2,000.5 mm", "length", 2000.5, "mm"),
        ("2 cm", "length", 20, "mm"),
        ("2 m", "length", 2000, "mm"),
        ("5'-6\"", "length", 1676.4, "mm"),
        ('1 1/2"', "length", 38.1, "mm"),
        ("1 MPa", "pressure", 10, "bar"),
        ("100 kPa", "pressure", 1, "bar"),
        ("212 °F", "temperature", 100, "C"),
        ("-40 °C", "temperature", -40, "C"),
        ("2 t", "mass", 2000, "kg"),
        ("1 lb", "mass", 0.45359237, "kg"),
        ("1 psi", "pressure", 0.0689475729, "bar"),
    ],
)
def test_pint_canonical_and_original_evidence(text, kind, value, unit):
    result = normalize(text, kind)
    assert result.value == pytest.approx(value)
    assert result.unit == unit and result.text_original == text and result.unit_original


def test_ambiguity_context_and_pressure_reference_are_explicit():
    with pytest.raises(AmbiguousNumber) as error:
        normalize("2.000 mm", "length")
    assert error.value.alternatives == (2, 2000)
    assert normalize("2.000 mm", "length", decimal=",").value == 2000
    assert normalize("2.000 mm", "length", decimal=".").value == 2
    assert normalize("10 bara", "pressure").unit == "bara"
    assert normalize("10 bar(g)", "pressure").pressure_basis == "gauge"
    assert normalize("1 kg/cm²", "pressure").notices
    for raw in ("1,2,3", "12 34", "1.23.456"):
        with pytest.raises(UnitError):
            number(raw)
    with pytest.raises(UnitError):
        normalize("1 kg", "length")
    with pytest.raises(UnitError):
        normalize('1/0"', "length")
