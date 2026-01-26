import sys
import os
from PyQt5.QtWidgets import QApplication
from myPGM.data_model import (PressureGaugeDataObject,
                                PressureGaugeDataManager)
from myPGM.presenter import Presenter
import myPGM.calibrations

from myPGM.ui.PressureToolbox import PressureToolbox 


# Run the application
if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    #~~~~this is how it will be done in main_ui.py~~~~ 


    calib_dict = {a.name: a for a in myPGM.calibrations.calib_list}
    
    # initial state
    buffer = PressureGaugeDataObject()
    buffer.Pm = 0
    buffer.P = 0
    buffer.x = 694.28
    buffer.T = 298
    buffer.x0 = 694.28
    buffer.T0 = 298
    buffer.calib = calib_dict["Ruby2020"]

    toolbox = PressureToolbox(calib_dict)
    toolbox.set_state(buffer)
    

     #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ 

    toolbox.show()

    sys.exit(app.exec_())