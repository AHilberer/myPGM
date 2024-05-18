import sys

from PyQt5.QtWidgets import QApplication
from main_ui import *

# Run the application
if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    #file = open("myPGM/styles.qss",'r')

    try:
        with file:
            qss = file.read()
            app.setStyleSheet(qss)
    except:
        pass
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())