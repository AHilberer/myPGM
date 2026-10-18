import numpy as np
import pytest

from myPGM import calibrations as C


# H2 is a direct polynomial P(nu): it does not use x0 and has no P(x0) = 0 point.
X0_BASED = [c for c in C.calib_list if c is not C.H2Vibron]

# The GUI mutates x0default/T0default of these shared objects when the user edits
# x0/T0, so freeze the shipped defaults at collection time.
DEFAULTS = {c.name: (c.x0default, c.T0default) for c in C.calib_list}


def _ids(calibs):
    return [c.name for c in calibs]


def test_calibration_names_are_unique():
    names = [c.name for c in C.calib_list]
    assert len(names) == len(set(names))


@pytest.mark.parametrize("calib", X0_BASED, ids=_ids(X0_BASED))
def test_zero_pressure_at_reference(calib):
    x0, T0 = DEFAULTS[calib.name]
    assert calib.func(x0, T0, x0, T0) == pytest.approx(0, abs=1e-9)


@pytest.mark.parametrize("calib", C.calib_list, ids=_ids(C.calib_list))
def test_pressure_increases_with_x(calib):
    x0, T0 = DEFAULTS[calib.name]
    if calib is C.H2Vibron:
        x = np.linspace(4155, 4266, 50)   # ~0-30 GPa, validity range of the fit
    else:
        x = np.linspace(x0, x0 * 1.04, 50)
    P = np.array([calib.func(xi, T0, x0, T0) for xi in x])
    assert np.all(np.diff(P) > 0)


@pytest.mark.parametrize("calib", C.calib_list, ids=_ids(C.calib_list))
@pytest.mark.parametrize("P", [0.5, 5, 30])
def test_inverse_round_trip(calib, P):
    x0, T0 = DEFAULTS[calib.name]
    x = calib.invfunc(P, T0, x0, T0)
    assert calib.func(x, T0, x0, T0) == pytest.approx(P, abs=1e-6)


def test_h2_inverse_stays_on_physical_branch():
    # x0default is -1 for H2: the inverse must still land on the vibron branch
    c = C.H2Vibron
    for P, nu_min, nu_max in [(1, 4160, 4175), (10, 4220, 4232), (30, 4260, 4272)]:
        assert nu_min < c.invfunc(P, 298, DEFAULTS[c.name][0], 298) < nu_max


# Regression values: computed with the current formulas (Oct 2026) so that any
# refactor (e.g. replacing the numerical inverse) cannot change results silently.
# They are not independent literature checks.
@pytest.mark.parametrize("calib, x, expected", [
    (C.Ruby2020,            700.0,  16.1211),
    (C.RubyMao1986,         700.0,  16.1240),
    (C.RubyMao1986_DatchiF, 700.0,  16.1099),
    (C.RubyHolzapfel2005,   700.0,  16.0586),
    (C.RubyDO2007,          700.0,  16.2251),
    (C.SamariumDatchi,      690.0,  17.4390),
    (C.SamRashchenko2015,   690.0,  17.6918),
    (C.Hilberer2026,        1400.0, 30.1162),
    (C.Akahama2006,         1400.0, 28.9040),
    (C.Eremets2023,         1400.0, 28.1500),
    (C.cBNDatchi,           1100.0, 14.3201),
    (C.H2Vibron,            4206.0,  5.8890),
], ids=lambda v: v.name if isinstance(v, C.HPCalibration) else None)
def test_regression_values(calib, x, expected):
    x0, T0 = DEFAULTS[calib.name]
    assert calib.func(x, T0, x0, T0) == pytest.approx(expected, abs=1e-3)


def test_ruby_temperature_correction_shifts_pressure():
    # at higher T the same wavelength means a lower pressure (Datchi 2007 correction)
    c = C.Ruby2020
    x0 = DEFAULTS[c.name][0]
    assert c.func(700.0, 400, x0, 298) < c.func(700.0, 298, x0, 298)


def test_default_fit_models_exist():
    from myPGM.fit_models import model_list
    names = {m.name for m in model_list}
    for c in C.calib_list:
        assert c.default_fit_model in names, c.name
