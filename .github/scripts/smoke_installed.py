"""Smoke test of an installed myPGM (wheel installed in a fresh venv, run outside the repo):
the package must find its theme, fonts, icons and example spectra, and the demo session
must open as with `mypgm --demo`. Run with QT_QPA_PLATFORM=offscreen."""
import sys
from pathlib import Path

from PyQt5.QtCore import QStandardPaths
from PyQt5.QtWidgets import QApplication

QStandardPaths.setTestModeEnabled(True)      # settings and log away from the user's folders

import myPGM                                  # noqa: E402
from myPGM.data_model import PressureGaugeDataManager   # noqa: E402
from myPGM.helpers import get_app_icon        # noqa: E402
from myPGM.presenter import Presenter         # noqa: E402
from myPGM.ui import theme                    # noqa: E402
from myPGM.ui.main_ui import MainWindow       # noqa: E402

package = Path(myPGM.__file__).parent
print("myPGM imported from", package)
if "site-packages" not in package.parts:
    sys.exit("myPGM was not imported from the installed wheel")

app = QApplication(sys.argv)
app.setApplicationName("myPGM")
theme.apply_theme(app, dark=False)
fonts = theme.load_fonts()
if fonts != {"ui": theme.UI_FAMILY, "mono": theme.MONO_FAMILY}:
    sys.exit(f"bundled fonts not loaded: {fonts}")

view = MainWindow()
presenter = Presenter(PressureGaugeDataManager(), view, demo=True)
view.show()
for _ in range(6):
    app.processEvents()

count = view.PvPmTableWindow.count_label.text()
print("pressure log:", count)
if count != "4 points":
    sys.exit(f"demo session not loaded: {count!r}")
if get_app_icon().isNull():
    sys.exit("app icon not found")

print("installed package OK")
