#pylint: disable=invalid-name,attribute-defined-outside-init,line-too-long,too-many-instance-attributes
# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'ui/cluster_status.ui'
#
# Created: Fri Jun 21 13:16:42 2013
#      by: PyQt4 UI code generator 4.7.4
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

class Ui_Frame(object):
    def setupUi(self, Frame):
        Frame.setObjectName("Frame")
        Frame.resize(753, 563)
        Frame.setFrameShape(QtGui.QFrame.StyledPanel)
        Frame.setFrameShadow(QtGui.QFrame.Raised)
        self.verticalLayout = QtGui.QVBoxLayout(Frame)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout_5 = QtGui.QHBoxLayout()
        self.horizontalLayout_5.setObjectName("horizontalLayout_5")
        self.label_3 = QtGui.QLabel(Frame)
        self.label_3.setMinimumSize(QtCore.QSize(160, 0))
        self.label_3.setMaximumSize(QtCore.QSize(160, 16777215))
        self.label_3.setObjectName("label_3")
        self.horizontalLayout_5.addWidget(self.label_3)
        self.resource_combo = QtGui.QComboBox(Frame)
        self.resource_combo.setObjectName("resource_combo")
        self.horizontalLayout_5.addWidget(self.resource_combo)
        self.verticalLayout.addLayout(self.horizontalLayout_5)
        self.horizontalLayout_4 = QtGui.QHBoxLayout()
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.job_table = QtGui.QTableWidget(Frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.job_table.sizePolicy().hasHeightForWidth())
        self.job_table.setSizePolicy(sizePolicy)
        self.job_table.setObjectName("job_table")
        self.job_table.setColumnCount(0)
        self.job_table.setRowCount(0)
        self.horizontalLayout_4.addWidget(self.job_table)
        self.verticalLayout.addLayout(self.horizontalLayout_4)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.label = QtGui.QLabel(Frame)
        self.label.setObjectName("label")
        self.horizontalLayout.addWidget(self.label)
        self.username_edit = QtGui.QLineEdit(Frame)
        self.username_edit.setInputMask("")
        self.username_edit.setText("")
        self.username_edit.setObjectName("username_edit")
        self.horizontalLayout.addWidget(self.username_edit)
        self.label_2 = QtGui.QLabel(Frame)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout.addWidget(self.label_2)
        self.password_edit = QtGui.QLineEdit(Frame)
        self.password_edit.setInputMask("")
        self.password_edit.setText("")
        self.password_edit.setEchoMode(QtGui.QLineEdit.Password)
        self.password_edit.setObjectName("password_edit")
        self.horizontalLayout.addWidget(self.password_edit)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_4 = QtGui.QLabel(Frame)
        self.label_4.setObjectName("label_4")
        self.horizontalLayout_2.addWidget(self.label_4)
        self.date_time_edit = QtGui.QDateTimeEdit(Frame)
        self.date_time_edit.setObjectName("date_time_edit")
        self.horizontalLayout_2.addWidget(self.date_time_edit)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem1)
        self.refresh_button = QtGui.QPushButton(Frame)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.refresh_button.sizePolicy().hasHeightForWidth())
        self.refresh_button.setSizePolicy(sizePolicy)
        self.refresh_button.setObjectName("refresh_button")
        self.horizontalLayout_2.addWidget(self.refresh_button)
        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.retranslateUi(Frame)
        QtCore.QMetaObject.connectSlotsByName(Frame)

    def retranslateUi(self, Frame):
        Frame.setWindowTitle(QtGui.QApplication.translate("Frame", "Frame", None, QtGui.QApplication.UnicodeUTF8))
        self.label_3.setText(QtGui.QApplication.translate("Frame", "Compute resource:", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("Frame", "Username:", None, QtGui.QApplication.UnicodeUTF8))
        self.username_edit.setToolTip(QtGui.QApplication.translate("Frame", "Enter compute resource username", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("Frame", "Password:", None, QtGui.QApplication.UnicodeUTF8))
        self.password_edit.setToolTip(QtGui.QApplication.translate("Frame", "Enter compute resource password", None, QtGui.QApplication.UnicodeUTF8))
        self.label_4.setText(QtGui.QApplication.translate("Frame", "Show items after:", None, QtGui.QApplication.UnicodeUTF8))
        self.refresh_button.setToolTip(QtGui.QApplication.translate("Frame", "Click to refresh the job list", None, QtGui.QApplication.UnicodeUTF8))
        self.refresh_button.setText(QtGui.QApplication.translate("Frame", "Refresh", None, QtGui.QApplication.UnicodeUTF8))

