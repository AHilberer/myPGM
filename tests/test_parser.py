import numpy as np
import pytest

from myPGM.helpers import customparse_file2data, spectro_calibration_reader


@pytest.mark.parametrize("name, n_points", [
    ("Example_Ruby_1.asc", 1024),
    ("Example_Ruby_2.asc", 1024),
    ("Example_Ruby_3.asc", 1024),
    ("Example_H2.txt", 2000),
    ("Example_diam_Raman.asc", 2000),   # has a text header before the data
])
def test_example_files(resources, name, n_points):
    data = customparse_file2data(resources / name)
    assert data.shape == (n_points, 2)
    assert np.all(np.isfinite(data))
    assert np.all(np.diff(data[:, 0]) != 0)


@pytest.mark.parametrize("text", [
    "694.28\t100.5\n694.30\t101.5\n694.32\t102.5\n",      # tab
    "694.28;100.5\n694.30;101.5\n694.32;102.5\n",         # semicolon
    "694.28,100.5\n694.30,101.5\n694.32,102.5\n",         # comma (CSV)
    "694.28   100.5\n 694.30 101.5\n694.32  102.5\n",     # repeated spaces
    "694,28\t100,5\n694,30\t101,5\n694,32\t102,5\n",      # decimal comma + tab
    "694,28;100,5\n694,30;101,5\n694,32;102,5\n",         # decimal comma + semicolon
    "x\ty\nheader line\n694.28\t100.5\n694.30\t101.5\n694.32\t102.5\nend\n",  # header/footer
], ids=["tab", "semicolon", "csv", "spaces", "comma-tab", "comma-semicolon", "header"])
def test_delimiters_and_decimal_comma(tmp_path, text):
    f = tmp_path / "spectrum.txt"
    f.write_text(text)
    np.testing.assert_allclose(
        customparse_file2data(f),
        [[694.28, 100.5], [694.30, 101.5], [694.32, 102.5]],
    )


def test_extra_columns_are_ignored(tmp_path):
    f = tmp_path / "three_cols.txt"
    f.write_text("1\t10\t100\n2\t20\t200\n")
    np.testing.assert_allclose(customparse_file2data(f), [[1, 10], [2, 20]])


def test_no_numeric_data_raises(tmp_path):
    f = tmp_path / "bad.asc"
    f.write_text("hello\nworld\n")
    with pytest.raises(RuntimeError):
        customparse_file2data(f)


def test_spectro_calibration_formats_agree(resources):
    two_cols = spectro_calibration_reader(resources / "alternate_spectro_calib_2cols.asc")
    one_col_header = spectro_calibration_reader(resources / "alternate_spectro_calib_1col_header.asc")
    assert len(two_cols) == 1024
    np.testing.assert_array_equal(two_cols, one_col_header)


def test_spectro_calibration_single_column(resources):
    x = spectro_calibration_reader(resources / "alternate_spectro_calib.asc")
    assert x.shape == (1024,)
    assert np.all(np.diff(x) > 0)


def test_spectro_calibration_empty_raises(tmp_path):
    f = tmp_path / "empty.asc"
    f.write_text("no numbers here\n")
    with pytest.raises(RuntimeError):
        spectro_calibration_reader(f)
