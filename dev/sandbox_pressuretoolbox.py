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


    #~~~~ this is how it will be done in main_ui.py ~~~~
    # 


    calib_dict = {a.name: a for a in myPGM.calibrations.calib_list}
    toolbox = PressureToolbox(calib_dict)

    #~~~~ this is how it will be done in presenter.py? ~~~~
    # 
 
    # initial state
    buffer = PressureGaugeDataObject()
    buffer.calib = calib_dict["Ruby2020"]

    buffer.Pm = 0
    buffer.T = 298
    buffer.x0 = 694.28
    buffer.T0 = 298
    buffer.set_x(694.28)
 
    toolbox.set_state(buffer)
    

    def on_P_edited(p):
        buffer.set_P(p)
        toolbox.set_state(buffer)

    def on_x_edited(x):
        buffer.set_x(x)        
        toolbox.set_state(buffer)

    def on_T_edited(T):
        buffer.set_T(T)        
        toolbox.set_state(buffer)

    def on_x0_edited(x0):
        buffer.set_x0(x0)

        print(id(buffer.calib))
        print(id(toolbox.calibrations[buffer.calib.name]))
        print(id(calib_dict[buffer.calib.name]))
        
        toolbox.set_state(buffer)

    def on_T0_edited(T0):
        buffer.set_T0(T0)        
        toolbox.set_state(buffer)

    # Connects
    toolbox.calibChanged.connect(buffer.set_calibration)
    toolbox.PChanged.connect(on_P_edited)
    toolbox.xChanged.connect(on_x_edited)
    toolbox.TChanged.connect(on_T_edited)
    toolbox.x0Changed.connect(on_x0_edited)
    toolbox.T0Changed.connect(on_T0_edited)
     #~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ 

    toolbox.show()

    sys.exit(app.exec_())