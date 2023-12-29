import sys
from PyQt5.QtWidgets import (QApplication)

from ui import *

# Run the application
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())