import json

import numpy as np
import pytest

from myPGM import calibrations as C, fit_models as F
from myPGM.data_model import PressureGaugeDataObject, PressureGaugeDataManager
from myPGM.helpers import PressureCalculationFailed


@pytest.fixture
def ruby(resources):
    obj = PressureGaugeDataObject()
    obj.load_spectral_data_file("Example_Ruby_1.asc", str(resources / "Example_Ruby_1.asc"))
    obj.set_calibration(C.Ruby2020)
    obj.set_fit_model(F.DoubleVoigt)
    return obj


def test_ids_are_unique():
    ids = [PressureGaugeDataObject().id for _ in range(1000)]
    ids += [PressureGaugeDataObject.generate_id() for _ in range(100)]
    assert len(set(ids)) == len(ids)


def test_manager_add_and_delete():
    manager = PressureGaugeDataManager()
    objs = [PressureGaugeDataObject() for _ in range(5)]
    for o in objs:
        manager.add_instance(o)
    assert len(manager) == 5
    manager.delete_instance(objs[0].id)
    assert objs[0].id not in manager and len(manager) == 4
    with pytest.raises(TypeError):
        manager.add_instance("not a data object")
    with pytest.raises(KeyError):
        manager.delete_instance(-1)


def test_normalized_data_max_is_one(ruby):
    assert ruby.normalized_data[:, 1].max() == pytest.approx(1.0)
    np.testing.assert_array_equal(ruby.normalized_data[:, 0], ruby.original_data[:, 0])


# --- pressure <-> x ---------------------------------------------------------------

def test_set_x_then_P_are_consistent():
    obj = PressureGaugeDataObject()
    obj.set_calibration(C.Ruby2020)
    P = obj.set_x(700.0)
    assert P == pytest.approx(C.Ruby2020.func(700.0, 298, C.Ruby2020.x0default, 298))
    assert obj.set_P(P) == pytest.approx(700.0, abs=1e-6)


def test_changing_T_updates_P():
    obj = PressureGaugeDataObject()
    obj.set_calibration(C.Ruby2020)
    obj.set_x(700.0)
    P_room = obj.P
    obj.set_T(400)
    assert obj.P < P_room


def test_invalid_calibration_parameters_raise():
    obj = PressureGaugeDataObject()
    obj.set_calibration(C.Ruby2020)
    obj.set_x(700.0)
    with pytest.raises(PressureCalculationFailed):
        obj.set_x0(0)          # division by zero in the ruby formula


# --- spectrum processing ----------------------------------------------------------

def test_auto_background_leaves_nonnegative_spectrum(ruby):
    ruby.convexhull_bg()
    x, y = ruby.get_data_to_process()
    assert y.min() >= -1e-9
    assert ruby.bg is not None


def test_reset_background(ruby):
    ruby.convexhull_bg()
    ruby.reset_bg()
    x, y = ruby.get_data_to_process()
    np.testing.assert_array_equal(y, ruby.normalized_data[:, 1])
    assert ruby.bg is None


def test_external_background_length_checked(ruby):
    with pytest.raises(ValueError):
        ruby.subtract_external_bg(np.zeros(10))


def test_smoothing_keeps_x_and_reduces_noise(ruby):
    y_raw = ruby.normalized_data[:, 1].copy()
    ruby.smoothen(9)
    x, y = ruby.get_data_to_process()
    np.testing.assert_array_equal(x, ruby.normalized_data[:, 0])
    assert np.std(np.diff(y)) < np.std(np.diff(y_raw))


def test_spectro_recalibration(ruby, resources):
    from myPGM.helpers import spectro_calibration_reader
    new_x = spectro_calibration_reader(resources / "alternate_spectro_calib.asc")
    ruby.spectro_recalib(new_x)
    x, _ = ruby.get_data_to_process()
    np.testing.assert_array_equal(x, new_x)
    ruby.reset_spectro_recalib()
    x, _ = ruby.get_data_to_process()
    np.testing.assert_array_equal(x, ruby.normalized_data[:, 0])


def test_spectro_recalibration_length_mismatch(ruby):
    with pytest.raises(RuntimeError):
        ruby.spectro_recalib(np.arange(10.0))


# Known bugs, roadmap item 11 (processing chain). strict=True: once fixed, these
# start passing and pytest reports it, so the xfail marker can be removed.
@pytest.mark.xfail(strict=True, reason="smoothing rebuilds x from normalized_data (item 11)")
def test_smoothing_keeps_spectro_recalibration(ruby, resources):
    from myPGM.helpers import spectro_calibration_reader
    new_x = spectro_calibration_reader(resources / "alternate_spectro_calib.asc")
    ruby.spectro_recalib(new_x)
    ruby.smoothen(5)
    x, _ = ruby.get_data_to_process()
    np.testing.assert_array_equal(x, new_x)


@pytest.mark.xfail(strict=True, reason="second Auto Bg overwrites bg with the increment (item 11)")
def test_repeated_auto_background_then_smoothing(ruby):
    ruby.convexhull_bg()
    ruby.convexhull_bg()
    _, y_bg = ruby.get_data_to_process()
    ruby.smoothen(1)          # window 1 = no smoothing: spectrum must not change
    _, y = ruby.get_data_to_process()
    np.testing.assert_allclose(y, y_bg, atol=1e-9)


# --- session serialisation ----------------------------------------------------------

def test_to_dict_from_dict_round_trip(ruby):
    ruby.fitting_range = (692.0, 697.0)
    ruby.fit_data()
    ruby.set_Pm(12.5)
    payload = json.loads(json.dumps(ruby.to_dict()))     # must be JSON-serialisable

    calib_dict = {c.name: c for c in C.calib_list}
    model_dict = {m.name: m for m in F.model_list}
    restored = PressureGaugeDataObject.from_dict(payload, calib_dict, model_dict)

    assert restored.id == ruby.id
    assert restored.calib is C.Ruby2020 and restored.fit_model is F.DoubleVoigt
    for attr in ("P", "x", "x0", "T", "T0", "Pm"):
        assert getattr(restored, attr) == pytest.approx(getattr(ruby, attr)), attr
    np.testing.assert_allclose(restored.original_data, ruby.original_data)
    np.testing.assert_allclose(restored.fit_result["opti"], ruby.fit_result["opti"])
    assert list(restored.fitting_range) == [692.0, 697.0]
