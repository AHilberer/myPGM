from PyQt5.QtWidgets import (QWidget,
                             QVBoxLayout,
                             QGroupBox,
                             QTabWidget,
                             QCheckBox
                             )

class ParameterWindow(QWidget):
    """
    Parameter window class
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Parameters")
        self.setGeometry(200, 200, 400, 400)
        paramlayout = QVBoxLayout()
        self.setLayout(paramlayout)
        
        fitparamBox = QGroupBox('Fitting parameters')
        fitparamlayout = QVBoxLayout()
        tabs = QTabWidget()
        tabs.addTab(self.RubyTab(), "Ruby")
        tabs.addTab(self.SamariumTab(), "Samarium")
        fitparamlayout.addWidget(tabs)
        fitparamBox.setLayout(fitparamlayout)
        paramlayout.addWidget(fitparamBox)


        otherBox = QGroupBox('Future box')
        otherlayout = QVBoxLayout()
        tabs = QTabWidget()
        tabs.addTab(self.RubyTab(), "Ruby")
        tabs.addTab(self.SamariumTab(), "Samarium")
        otherlayout.addWidget(tabs)
        otherBox.setLayout(otherlayout)
        paramlayout.addWidget(otherBox)

    def RubyTab(self):
        """Create the General page UI."""
        rubyTab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QCheckBox("General Option 1"))
        layout.addWidget(QCheckBox("General Option 2"))
        rubyTab.setLayout(layout)
        return rubyTab

    def SamariumTab(self):
        """Create the Network page UI."""
        samariumTab = QWidget()
        layout = QVBoxLayout()
        layout.addWidget(QCheckBox("Network Option 1"))
        layout.addWidget(QCheckBox("Network Option 2"))
        samariumTab.setLayout(layout)
        return samariumTab