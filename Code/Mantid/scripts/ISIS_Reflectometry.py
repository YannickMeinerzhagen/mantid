"""
    Script used to start the ISIS Reflectomery GUI from MantidPlot
"""
from PyQt4 import QtGui
#, QtCore
from ui.reflectometer import refl_gui

class ConfirmQMainWindow(QtGui.QMainWindow):
    def __init__(self, ui):
        super(ConfirmQMainWindow, self).__init__()
        self.modFlag = False
        self.gui = ui
    def savecheck(self):
        msgBox = QtGui.QMessageBox()
        msgBox.setText("The table has been modified. Do you want to save your changes?")
        msgBox.setStandardButtons(QtGui.QMessageBox.Save | QtGui.QMessageBox.Discard | QtGui.QMessageBox.Cancel)
        msgBox.setIcon(QtGui.QMessageBox.Question)
        msgBox.setDefaultButton(QtGui.QMessageBox.Save)
        msgBox.setEscapeButton(QtGui.QMessageBox.Cancel)
        ret = msgBox.exec_()
        saved = None
        if ret == QtGui.QMessageBox.Save:
            saved = self.gui.save()
        return ret, saved
    def closeEvent(self, event):
        self.gui.buttonProcess.setFocus()
        if self.modFlag:
            event.ignore()
            ret, saved = self.savecheck()
            if ret == QtGui.QMessageBox.Save:
                if saved:
                    event.accept()
            elif ret == QtGui.QMessageBox.Discard:
                event.accept()
ui = refl_gui.ReflGui()
MainWindow = ConfirmQMainWindow(ui)
ui.setupUi(MainWindow)
MainWindow.show()
