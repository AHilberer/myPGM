import numpy as np
import pytest

from myPGM import calibrations as C, fit_models as F
from myPGM.data_model import PressureGaugeDataObject


def fitted(resources, name, calib, model, guess=None):
    obj = PressureGaugeDataObject()
    obj.load_spectral_data_file(name, str(resources / name))
    obj.set_calibration(calib)
    obj.set_fit_model(model)
    obj.fit_data(guess)
    return obj


# Regression values from the current fit code (Oct 2026, after the initial-guess fix).
# Ruby pressures are read on R1 (the taller, longer-wavelength peak).
@pytest.mark.parametrize("name, calib, model, x, P", [
    ("Example_Ruby_1.asc", C.Ruby2020, F.DoubleVoigt,       694.9076, 1.699),
    ("Example_Ruby_1.asc", C.Ruby2020, F.DoubleLorentzian,  694.9096, 1.705),
    ("Example_Ruby_1.asc", C.Ruby2020, F.DoubleGaussian,    694.9059, 1.694),
    ("Example_Ruby_1.asc", C.Ruby2020, F.SingleLorentzian,  694.8672, 1.589),
    ("Example_Ruby_2.asc", C.Ruby2020, F.DoubleVoigt,       695.4771, 3.256),
    ("Example_Ruby_3.asc", C.Ruby2020, F.DoubleVoigt,       696.2243, 5.319),
    # Not pinned: Single Voigt on a whole ruby doublet is poorly constrained, and its
    # result depends on the platform by up to ~0.01 nm (e.g. Ruby_1: 694.8671 nm on
    # macOS, 694.8644 nm on Linux CI). Single peaks are covered by the H2 fits and
    # by test_fitting_range_restricts_data (R1 only).
    ("Example_H2.txt",     C.H2Vibron, F.SingleLorentzian, 4206.0321, 5.895),
    ("Example_H2.txt",     C.H2Vibron, F.SingleGaussian,   4206.0494, 5.898),
    ("Example_H2.txt",     C.H2Vibron, F.SingleVoigt,      4206.0350, 5.896),
], ids=lambda v: getattr(v, "name", v) if not isinstance(v, float) else None)
def test_example_fits(resources, name, calib, model, x, P):
    obj = fitted(resources, name, calib, model)
    assert obj.x == pytest.approx(x, abs=2e-3)
    assert obj.P == pytest.approx(P, abs=0.01)


def test_ruby_pressure_increases_across_examples(resources):
    P = [fitted(resources, f"Example_Ruby_{i}.asc", C.Ruby2020, F.DoubleVoigt).P for i in (1, 2, 3)]
    assert P[0] < P[1] < P[2]


def test_fit_stores_curve_and_covariance(resources):
    obj = fitted(resources, "Example_Ruby_1.asc", C.Ruby2020, F.DoubleVoigt)
    assert obj.fitted_data.shape == obj.normalized_data.shape
    n_params = len(obj.fit_result["opti"])
    assert obj.fit_result["cov"].shape == (n_params, n_params)


def test_fitting_range_restricts_data(resources):
    obj = PressureGaugeDataObject()
    obj.load_spectral_data_file("Example_Ruby_1.asc", str(resources / "Example_Ruby_1.asc"))
    obj.set_calibration(C.Ruby2020)
    obj.set_fit_model(F.SingleVoigt)
    obj.fitting_range = (694.5, 695.5)    # R1 only
    obj.fit_data()
    assert obj.fitted_data[:, 0].min() >= 694.5
    assert obj.fitted_data[:, 0].max() <= 695.5
    assert 694.8 < obj.x < 695.0


def test_double_model_on_single_peak_fails_cleanly(resources):
    # used to raise IndexError (crashing the app). Converging or not is fine, but a
    # failure must be a RuntimeError, which the presenter turns into a "Fit error" popup.
    for model in (F.DoubleVoigt, F.DoubleGaussian, F.DoubleLorentzian):
        try:
            fitted(resources, "Example_H2.txt", C.H2Vibron, model)
        except RuntimeError:
            pass


@pytest.mark.parametrize("n_points", [0, 1, 3, 9])     # Double Voigt has 9 parameters
def test_too_narrow_fit_range_fails_cleanly(resources, n_points):
    # used to raise TypeError (curve_fit) or IndexError (initial guess), shown as an
    # unexpected error instead of the "Fit error" popup
    obj = PressureGaugeDataObject()
    obj.load_spectral_data_file("Example_Ruby_1.asc", str(resources / "Example_Ruby_1.asc"))
    obj.set_calibration(C.Ruby2020)
    obj.set_fit_model(F.DoubleVoigt)
    x = obj.normalized_data[:, 0]
    obj.fitting_range = (x[500], x[499 + n_points]) if n_points else (1.0, 2.0)
    with pytest.raises(RuntimeError, match="points in the fit range"):
        obj.fit_data()


# --- initial guess -------------------------------------------------------------

def _triple_voigt(x, c, a1, x1, s1, g1, a2, x2, s2, g2, a3, x3, s3, g3):
    return (F.Single_Voigt(x, c, a1, x1, s1, g1) + F.Single_Voigt(x, 0, a2, x2, s2, g2)
            + F.Single_Voigt(x, 0, a3, x3, s3, g3))


def test_peak_structure_is_declared_not_guessed():
    # 12 peak parameters: the old "% 3" rule read a triple Voigt as 4 Gaussians
    triple = F.GaugeFitModel("Triple Voigt", _triple_voigt, "peak", "grey",
                             n_peaks=3, params_per_peak=4)
    assert triple.n_params == 13
    x = np.linspace(690, 700, 1001)
    y = _triple_voigt(x, 0.1, 0.5, 694.9, 0.1, 0.1, 0.3, 693.4, 0.1, 0.1, 0.2, 697.0, 0.1, 0.1)
    pinit = triple.get_pinit(x, y)
    assert len(pinit) == 13
    popt = np.array(pinit)
    popt[[2, 6, 10]] = [694.9, 693.4, 697.0]
    assert triple.position_index(popt) == 10              # longest wavelength
    assert F.DoubleVoigt.position_index(popt[:9]) == 2
    with pytest.raises(ValueError, match="peak parameters"):
        F.GaugeFitModel("Wrong", _triple_voigt, "peak", "grey", n_peaks=3, params_per_peak=3)


@pytest.mark.parametrize("model", [m for m in F.model_list if m.type == "peak"], ids=lambda m: m.name)
def test_every_peak_model_declares_its_structure(model):
    assert model.n_peaks in (1, 2) and model.params_per_peak in (3, 4)
    assert ("Voigt" in model.name) == (model.params_per_peak == 4)


def _two_gaussians(x):
    # both above the half-height detection threshold
    return (F.Single_Gaussian(x, 0, 1.0, 694.9, 0.15)      # tall, narrow
            + F.Single_Gaussian(x, 0, 0.7, 692.5, 0.15))   # smaller


def test_initial_guess_starts_from_tallest_peak():
    x = np.linspace(690, 698, 800)
    pinit = F.SingleGaussian.get_pinit(x, _two_gaussians(x))
    assert pinit[2] == pytest.approx(694.9, abs=0.02)


def test_initial_guess_widths_match_peaks():
    x = np.linspace(690, 698, 800)
    # second peak above the half-height detection threshold, and much wider
    y = (F.Single_Gaussian(x, 0, 1.0, 694.9, 0.15)
         + F.Single_Gaussian(x, 0, 0.7, 692.5, 0.45))
    positions, widths = F.GaugeFitModel._find_peak_guesses(x, y, x[1] - x[0], 2)
    assert positions == pytest.approx([694.9, 692.5], abs=0.02)
    # each position keeps its own width (they used to be mismatched)
    assert widths[1] == pytest.approx(3 * widths[0], rel=0.15)


def test_initial_guess_with_fewer_peaks_than_model():
    x = np.linspace(690, 698, 800)
    y = F.Single_Gaussian(x, 0, 1.0, 694.9, 0.15)
    pinit = F.DoubleVoigt.get_pinit(x, y)
    assert len(pinit) == 9
    assert np.all(np.isfinite(pinit))


def test_voigt_start_matches_measured_peak_height():
    # the Voigt amplitude is an area: the starting peak must still have the data's
    # height, for narrow ruby lines (nm) as for the ~10 cm-1 wide H2 vibron
    for width in (0.15, 9.0):
        x = np.linspace(-60 * width, 60 * width, 2000)
        y = 0.2 + F.Single_Voigt(x, 0, 1.0, 0.0, width, width) / F.Single_Voigt(0, 0, 1.0, 0.0, width, width)
        p = F.SingleVoigt.get_pinit(x, y)
        start_height = F.Single_Voigt(p[2], p[0], *p[1:]) - p[0]
        assert start_height == pytest.approx(y.max() - p[0], rel=0.05)


def test_every_calibration_default_model_fits_its_example(resources):
    # the default model of each calibration used by an example spectrum converges
    models = {m.name: m for m in F.model_list}
    for name, calib in [("Example_Ruby_1.asc", C.Ruby2020), ("Example_H2.txt", C.H2Vibron)]:
        obj = fitted(resources, name, calib, models[calib.default_fit_model])
        assert obj.P_err is not None


def test_initial_guess_from_click():
    x = np.linspace(690, 698, 800)
    pinit = F.DoubleVoigt.get_pinit(x, _two_gaussians(x), guess_peak=694.0)
    assert pinit[2] == 694.0


# --- Raman edge ------------------------------------------------------------------

def _edge_object(edge_at=1450.0):
    x = np.linspace(1300, 1600, 601)
    y = 1 - 1 / (1 + np.exp(-(x - edge_at) / 2))     # high-to-low step
    obj = PressureGaugeDataObject()
    obj.original_data = np.column_stack((x, y))
    obj.normalize_data()
    obj.set_calibration(C.Akahama2006)
    obj.set_fit_model(F.RamanEdge)
    return obj


def test_raman_edge_at_steepest_descent():
    obj = _edge_object(1450.0)
    obj.fit_data()
    assert obj.x == pytest.approx(1450.0, abs=0.5)


def test_raman_edge_uses_click_position():
    obj = _edge_object(1450.0)
    obj.fit_data(guess_peak=1420.0)
    assert obj.x == 1420.0


def test_raman_edge_in_too_narrow_range_fails_cleanly():
    obj = _edge_object(1450.0)
    obj.fitting_range = (1449.9, 1450.1)       # a single point
    with pytest.raises(RuntimeError, match="points in the fit range"):
        obj.fit_data()


def test_raman_edge_with_x_stored_decreasing(resources):
    # the gradient was taken in file order: with x decreasing, the steepest rise was found
    obj = _edge_object(1450.0)
    obj.original_data = obj.original_data[::-1].copy()
    obj.normalize_data()
    obj.fit_data()
    assert obj.x == pytest.approx(1450.0, abs=0.5)

    ascending = fitted(resources, "Example_diam_Raman.asc", C.Akahama2006, F.RamanEdge)
    descending = PressureGaugeDataObject()
    descending.load_spectral_data_file("d", str(resources / "Example_diam_Raman.asc"))
    descending.original_data = descending.original_data[::-1].copy()
    descending.normalize_data()
    descending.set_calibration(C.Akahama2006)
    descending.set_fit_model(F.RamanEdge)
    descending.fit_data()
    assert descending.x == ascending.x
