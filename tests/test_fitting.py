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
    ("Example_Ruby_1.asc", C.Ruby2020, F.SingleVoigt,       694.8678, 1.591),
    ("Example_Ruby_1.asc", C.Ruby2020, F.SingleLorentzian,  694.8672, 1.589),
    ("Example_Ruby_2.asc", C.Ruby2020, F.DoubleVoigt,       695.4771, 3.256),
    ("Example_Ruby_2.asc", C.Ruby2020, F.SingleVoigt,       695.4399, 3.153),
    ("Example_Ruby_3.asc", C.Ruby2020, F.DoubleVoigt,       696.2243, 5.319),
    # Not pinned: Single Voigt on the whole Ruby_3 doublet is poorly constrained and
    # gives 696.143 nm on macOS but 696.159 nm on Linux CI (~0.05 GPa apart).
    ("Example_H2.txt",     C.H2Vibron, F.SingleLorentzian, 4206.0321, 5.895),
    ("Example_H2.txt",     C.H2Vibron, F.SingleGaussian,   4206.0494, 5.898),
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


# --- initial guess -------------------------------------------------------------

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
