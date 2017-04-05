#pylint: disable=invalid-name,relative-import,W0611,R0921,R0902,R0904,R0921,C0302,R0912
################################################################################
#
# MainWindow application for reducing HFIR 4-circle
#
################################################################################
import os
import sys
import csv
import time
import datetime
import random
import numpy

from PyQt4 import QtCore, QtGui
try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    from mantidqtpython import MantidQt
except ImportError as e:
    NO_SCROLL = True
else:
    NO_SCROLL = False

import guiutility as gutil
import peakprocesshelper as peak_util
import fourcircle_utility as hb3a_util
import plot3dwindow
from multi_threads_helpers import *
import optimizelatticewindow as ol_window
import viewspicedialog
import peak_integration_utility
import FindUBUtility

# import line for the UI python class
from ui_MainWindow import Ui_MainWindow

# define constants
IndexFromSpice = 'From Spice (pre-defined)'
IndexFromUB = 'From Calculation By UB'
MAGNETIC_TOL = 0.2


class MainWindow(QtGui.QMainWindow):
    """ Class of Main Window (top)
    """
    TabPage = {'View Raw Data': 2,
               'Calculate UB': 3,
               'UB Matrix': 4,
               'Peak Integration': 6,
               'Scans Processing': 5}

    def __init__(self, parent=None):
        """ Initialization and set up
        """
        # Base class
        QtGui.QMainWindow.__init__(self,parent)

        # UI Window (from Qt Designer)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # children windows
        self._my3DWindow = None
        self._refineConfigWindow = None
        self._peakIntegrationInfoWindow = None
        self._addUBPeaksDialog = None
        self._spiceViewer = None

        # Make UI scrollable
        if NO_SCROLL is False:
            self._scrollbars = MantidQt.API.WidgetScrollbarDecorator(self)
            self._scrollbars.setEnabled(True)  # Must follow after setupUi(self)!

        self._init_widgets()

        # thread
        self._myIntegratePeaksThread = None
        self._addUBPeaksThread = None

        # Mantid configuration
        self._instrument = str(self.ui.comboBox_instrument.currentText())
        # config = ConfigService.Instance()
        # self._instrument = config["default.instrument"]

        # Event handling definitions
        # Top
        self.connect(self.ui.pushButton_setExp, QtCore.SIGNAL('clicked()'),
                     self.do_set_experiment)

        # Tab 'Data Access'
        self.connect(self.ui.pushButton_applySetup, QtCore.SIGNAL('clicked()'),
                     self.do_apply_setup)
        self.connect(self.ui.pushButton_browseLocalDataDir, QtCore.SIGNAL('clicked()'),
                     self.do_browse_local_spice_data)
        self.connect(self.ui.pushButton_testURLs, QtCore.SIGNAL('clicked()'),
                     self.do_test_url)
        self.connect(self.ui.pushButton_ListScans, QtCore.SIGNAL('clicked()'),
                     self.do_list_scans)
        self.connect(self.ui.pushButton_downloadExpData, QtCore.SIGNAL('clicked()'),
                     self.do_download_spice_data)
        self.connect(self.ui.comboBox_mode, QtCore.SIGNAL('currentIndexChanged(int)'),
                     self.do_change_data_access_mode)
        self.connect(self.ui.pushButton_applyCalibratedSampleDistance, QtCore.SIGNAL('clicked()'),
                     self.do_set_user_detector_distance)
        self.connect(self.ui.pushButton_applyUserDetCenter, QtCore.SIGNAL('clicked()'),
                     self.do_set_user_detector_center)
        self.connect(self.ui.pushButton_applyUserWavelength, QtCore.SIGNAL('clicked()'),
                     self.do_set_user_wave_length)
        self.connect(self.ui.pushButton_applyDetectorSize, QtCore.SIGNAL('clicked()'),
                     self.do_set_detector_size)

        # Tab survey
        self.connect(self.ui.pushButton_survey, QtCore.SIGNAL('clicked()'),
                     self.do_survey)
        self.connect(self.ui.pushButton_saveSurvey, QtCore.SIGNAL('clicked()'),
                     self.do_save_survey)
        self.connect(self.ui.pushButton_loadSurvey, QtCore.SIGNAL('clicked()'),
                     self.do_load_survey)
        self.connect(self.ui.pushButton_viewSurveyPeak, QtCore.SIGNAL('clicked()'),
                     self.do_view_survey_peak)
        self.connect(self.ui.pushButton_addPeaksToRefine, QtCore.SIGNAL('clicked()'),
                     self.do_add_peaks_for_ub)
        self.connect(self.ui.pushButton_mergeScansSurvey, QtCore.SIGNAL('clicked()'),
                     self.do_merge_scans_survey)
        self.connect(self.ui.pushButton_selectAllSurveyPeaks, QtCore.SIGNAL('clicked()'),
                     self.do_select_all_survey)
        self.connect(self.ui.pushButton_sortInfoTable, QtCore.SIGNAL('clicked()'),
                     self.do_filter_sort_survey_table)
        self.connect(self.ui.pushButton_clearSurvey, QtCore.SIGNAL('clicked()'),
                     self.do_clear_survey)
        self.connect(self.ui.pushButton_viewRawSpice, QtCore.SIGNAL('clicked()'),
                     self.do_show_spice_file)

        self.connect(self.ui.lineEdit_numSurveyOutput, QtCore.SIGNAL('editingFinished()'),
                     self.evt_show_survey)
        self.connect(self.ui.lineEdit_numSurveyOutput, QtCore.SIGNAL('returnPressed()'),
                     self.evt_show_survey)
        self.connect(self.ui.lineEdit_numSurveyOutput, QtCore.SIGNAL('textEdited(const QString&)'),
                     self.evt_show_survey)

        # Tab 'View Raw Data'
        self.connect(self.ui.pushButton_setScanInfo, QtCore.SIGNAL('clicked()'),
                     self.do_load_scan_info)
        self.connect(self.ui.pushButton_plotRawPt, QtCore.SIGNAL('clicked()'),
                     self.do_plot_pt_raw)
        self.connect(self.ui.pushButton_prevPtNumber, QtCore.SIGNAL('clicked()'),
                     self.do_plot_prev_pt_raw)
        self.connect(self.ui.pushButton_nextPtNumber, QtCore.SIGNAL('clicked()'),
                     self.do_plot_next_pt_raw)
        self.connect(self.ui.pushButton_showPtList, QtCore.SIGNAL('clicked()'),
                     self.show_scan_pt_list)
        self.connect(self.ui.pushButton_showSPICEinRaw, QtCore.SIGNAL('clicked()'),
                     self.do_show_spice_file_raw)
        self.connect(self.ui.pushButton_addROI, QtCore.SIGNAL('clicked()'),
                     self.do_add_roi)
        self.connect(self.ui.pushButton_cancelROI, QtCore.SIGNAL('clicked()'),
                     self.do_del_roi)
        self.connect(self.ui.pushButton_nextScanNumber, QtCore.SIGNAL('clicked()'),
                     self.do_plot_next_scan)
        self.connect(self.ui.pushButton_prevScanNumber, QtCore.SIGNAL('clicked()'),
                     self.do_plot_prev_scan)
        self.connect(self.ui.pushButton_maskScanPt, QtCore.SIGNAL('clicked()'),
                     self.do_mask_pt_2d)
        self.connect(self.ui.pushButton_saveMask, QtCore.SIGNAL('clicked()'),
                     self.do_save_roi)

        # Tab 'calculate ub matrix'
        self.connect(self.ui.pushButton_addUBScans, QtCore.SIGNAL('clicked()'),
                     self.do_add_ub_peaks)
        # self.connect(self.ui.pushButton_addPeakToCalUB, QtCore.SIGNAL('clicked()'),
        #              self.do_add_ub_peak)
        self.connect(self.ui.pushButton_calUB, QtCore.SIGNAL('clicked()'),
                     self.do_cal_ub_matrix)
        self.connect(self.ui.pushButton_acceptUB, QtCore.SIGNAL('clicked()'),
                     self.do_accept_ub)
        self.connect(self.ui.pushButton_indexUBPeaks, QtCore.SIGNAL('clicked()'),
                     self.do_index_ub_peaks)
        self.connect(self.ui.pushButton_deleteUBPeak, QtCore.SIGNAL('clicked()'),
                     self.do_del_ub_peaks)
        self.connect(self.ui.pushButton_clearUBPeakTable, QtCore.SIGNAL('clicked()'),
                     self.do_clear_ub_peaks)
        self.connect(self.ui.pushButton_resetPeakHKLs, QtCore.SIGNAL('clicked()'),
                     self.do_reset_ub_peaks_hkl)
        # self.connect(self.ui.pushButton_selectAllPeaks, QtCore.SIGNAL('clicked()'),
        #              self.do_select_all_peaks)
        self.connect(self.ui.pushButton_viewScan3D, QtCore.SIGNAL('clicked()'),
                     self.do_view_data_3d)
        self.connect(self.ui.pushButton_plotSelectedData, QtCore.SIGNAL('clicked()'),
                     self.do_view_data_set_3d)
        self.connect(self.ui.pushButton_setHKL2Int, QtCore.SIGNAL('clicked()'),
                     self.do_set_ub_tab_hkl_to_integers)
        self.connect(self.ui.pushButton_undoSetToInteger, QtCore.SIGNAL('clicked()'),
                     self.do_undo_ub_tab_hkl_to_integers)
        self.connect(self.ui.pushButton_clearIndexing, QtCore.SIGNAL('clicked()'),
                     self.do_clear_all_peaks_index_ub)

        self.connect(self.ui.pushButton_refineUB, QtCore.SIGNAL('clicked()'),
                     self.do_refine_ub_indexed_peaks)
        self.connect(self.ui.pushButton_refineUBCalIndex, QtCore.SIGNAL('clicked()'),
                     self.do_refine_ub_cal_indexed_peaks)

        self.connect(self.ui.pushButton_refineUBFFT, QtCore.SIGNAL('clicked()'),
                     self.do_refine_ub_fft)
        self.connect(self.ui.pushButton_findUBLattice, QtCore.SIGNAL('clicked()'),
                     self.do_refine_ub_lattice)

        self.connect(self.ui.radioButton_ubAdvancedSelection, QtCore.SIGNAL('toggled(bool)'),
                     self.do_select_all_peaks)
        self.connect(self.ui.radioButton_ubSelectAllScans, QtCore.SIGNAL('toggled(bool)'),
                     self.do_select_all_peaks)
        self.connect(self.ui.radioButton_ubSelectNoScan, QtCore.SIGNAL('toggled(bool)'),
                     self.do_select_all_peaks)

        # Tab 'Setup'
        self.connect(self.ui.pushButton_useDefaultDir, QtCore.SIGNAL('clicked()'),
                     self.do_setup_dir_default)
        self.connect(self.ui.pushButton_browseLocalCache, QtCore.SIGNAL('clicked()'),
                     self.do_browse_local_cache_dir)
        self.connect(self.ui.pushButton_browseWorkDir, QtCore.SIGNAL('clicked()'),
                     self.do_browse_working_dir)
        self.connect(self.ui.comboBox_instrument, QtCore.SIGNAL('currentIndexChanged(int)'),
                     self.do_change_instrument_name)

        # Tab 'UB Matrix'
        self.connect(self.ui.pushButton_showUB2Edit, QtCore.SIGNAL('clicked()'),
                     self.do_show_ub_in_box)
        self.connect(self.ui.pushButton_syncUB, QtCore.SIGNAL('clicked()'),
                     self.do_sync_ub)
        self.connect(self.ui.pushButton_saveUB, QtCore.SIGNAL('clicked()'),
                     self.do_save_ub)

        # Tab 'Scans Processing'
        self.connect(self.ui.pushButton_addScanSliceView, QtCore.SIGNAL('clicked()'),
                     self.do_add_scans_merge)
        self.connect(self.ui.pushButton_mergeScans, QtCore.SIGNAL('clicked()'),
                     self.do_merge_scans)
        self.connect(self.ui.pushButton_integratePeaks, QtCore.SIGNAL('clicked()'),
                     self.do_integrate_peaks)
        self.connect(self.ui.pushButton_setupPeakIntegration, QtCore.SIGNAL('clicked()'),
                     self.do_switch_tab_peak_int)
        self.connect(self.ui.pushButton_refreshMerged, QtCore.SIGNAL('clicked()'),
                     self.do_refresh_merged_scans_table)
        self.connect(self.ui.pushButton_plotMergedScans, QtCore.SIGNAL('clicked()'),
                     self.do_view_merged_scans_3d)
        self.connect(self.ui.pushButton_showUB, QtCore.SIGNAL('clicked()'),
                     self.do_view_ub)
        self.connect(self.ui.pushButton_exportPeaks, QtCore.SIGNAL('clicked()'),
                     self.do_export_to_fp)
        self.connect(self.ui.pushButton_selectAllScans2Merge, QtCore.SIGNAL('clicked()'),
                     self.do_select_merged_scans)
        self.connect(self.ui.pushButton_indexMergedScans, QtCore.SIGNAL('clicked()'),
                     self.do_index_merged_scans_peaks)
        self.connect(self.ui.pushButton_applyKShift, QtCore.SIGNAL('clicked()'),
                     self.do_apply_k_shift)
        self.connect(self.ui.pushButton_clearMergeScanTable, QtCore.SIGNAL('clicked()'),
                     self.do_clear_merge_table)
        self.connect(self.ui.pushButton_multipleScans, QtCore.SIGNAL('clicked()'),
                     self.do_merge_multi_scans)
        self.connect(self.ui.pushButton_convertMerged2HKL, QtCore.SIGNAL('clicked()'),
                     self.do_convert_merged_to_hkl)
        self.connect(self.ui.pushButton_showScanWSInfo, QtCore.SIGNAL('clicked()'),
                     self.do_show_workspaces)
        self.connect(self.ui.pushButton_showIntegrateDetails, QtCore.SIGNAL('clicked()'),
                     self.do_show_integration_details)
        self.connect(self.ui.pushButton_toggleIntegrateType, QtCore.SIGNAL('clicked()'),
                     self.do_toggle_table_integration)
        self.connect(self.ui.pushButton_exportSelectedPeaks, QtCore.SIGNAL('clicked()'),
                     self.do_export_selected_peaks_to_integrate)

        # Tab 'Integrate (single) Peaks'
        self.connect(self.ui.pushButton_integratePt, QtCore.SIGNAL('clicked()'),
                     self.do_integrate_single_scan)
        self.connect(self.ui.comboBox_ptCountType, QtCore.SIGNAL('currentIndexChanged(int)'),
                     self.evt_change_normalization)  # calculate the normalized data again
        # TODO/FIXME/NOW - Need to find out why I want this!
        # self.connect(self.ui.pushButton_showIntegrateDetails, QtCore.SIGNAL('clicked()'),
        #              self.do_show_single_peak_integration)
        self.connect(self.ui.pushButton_clearPeakIntFigure, QtCore.SIGNAL('clicked()'),
                     self.do_clear_peak_integration_canvas)

        # Tab k-shift vector
        self.connect(self.ui.pushButton_addKShift, QtCore.SIGNAL('clicked()'),
                     self.do_add_k_shift_vector)

        # Menu and advanced tab
        self.connect(self.ui.actionExit, QtCore.SIGNAL('triggered()'),
                     self.menu_quit)

        self.connect(self.ui.actionSave_Session, QtCore.SIGNAL('triggered()'),
                     self.save_current_session)
        self.connect(self.ui.actionLoad_Session, QtCore.SIGNAL('triggered()'),
                     self.load_session)

        self.connect(self.ui.actionSave_Project, QtCore.SIGNAL('triggered()'),
                     self.action_save_project)
        self.connect(self.ui.actionOpen_Project, QtCore.SIGNAL('triggered()'),
                     self.action_load_project)
        self.connect(self.ui.actionOpen_Last_Project, QtCore.SIGNAL('triggered()'),
                     self.action_load_last_project)

        self.connect(self.ui.pushButton_loadLastNthProject, QtCore.SIGNAL('clicked()'),
                     self.do_load_nth_project)

        # Validator ... (NEXT)

        # Declaration of class variable
        # some configuration
        self._homeSrcDir = os.getcwd()
        self._homeDir = os.getcwd()

        # Control
        self._myControl = r4c.CWSCDReductionControl(self._instrument)
        self._allowDownload = True
        self._dataAccessMode = 'Download'
        self._surveyTableFlag = True
        self._ubPeakTableFlag = True

        # set the detector geometry
        self.do_set_detector_size()

        # Sub window
        self._baseTitle = 'Title is not initialized'

        # Timing and thread 'global'
        self._startMeringScans = time.clock()
        self._errorMessageEnsemble = ''

        # QSettings
        self.load_settings()

        return

    @property
    def controller(self):
        """ Parameter controller
        """
        assert self._myControl is not None, 'Controller cannot be None.'
        assert isinstance(self._myControl, r4c.CWSCDReductionControl), \
            'My controller must be of type %s, but not %s.' % ('CWSCDReductionControl',
                                                               self._myControl.__class__.__name__)

        return self._myControl

    def _init_widgets(self):
        """ Initialize the table widgets
        :return:
        """
        self._baseTitle = str(self.windowTitle())
        self.setWindowTitle('No Experiment Is Set')

        # detector geometry
        self.ui.lineEdit_detectorGeometry.setText('256, 256')

        # Table widgets
        self.ui.tableWidget_peaksCalUB.setup()
        self.ui.tableWidget_ubMatrix.setup()
        self.ui.tableWidget_surveyTable.setup()
        self.ui.tableWidget_mergeScans.setup()
        self.ui.tableWidget_ubInUse.setup()
        self.ui.tableWidget_kShift.setup()

        # Radio buttons
        self.ui.radioButton_ubFromTab1.setChecked(True)
        # group for the source of UB matrix to import
        ub_source_group = QtGui.QButtonGroup(self)
        ub_source_group.addButton(self.ui.radioButton_ubFromList)
        ub_source_group.addButton(self.ui.radioButton_ubFromTab1)
        # group for the UB matrix's style
        ub_style_group = QtGui.QButtonGroup(self)
        ub_style_group.addButton(self.ui.radioButton_ubMantidStyle)
        ub_style_group.addButton(self.ui.radioButton_ubSpiceStyle)

        self.ui.radioButton_qsample.setChecked(True)

        # combo-box
        self.ui.comboBox_kVectors.clear()
        self.ui.comboBox_kVectors.addItem('0: (0, 0, 0)')

        self.ui.comboBox_indexFrom.clear()
        self.ui.comboBox_indexFrom.addItem('By calculation')
        self.ui.comboBox_indexFrom.addItem('From SPICE')

        self.ui.comboBox_hklType.clear()
        self.ui.comboBox_hklType.addItem('SPICE')
        self.ui.comboBox_hklType.addItem('Calculated')

        # normalization to peak
        self.ui.comboBox_ptCountType.clear()
        self.ui.comboBox_ptCountType.addItem('Time')
        self.ui.comboBox_ptCountType.addItem('Monitor')
        self.ui.comboBox_ptCountType.addItem('Absolute')

        # tab
        self.ui.tabWidget.setCurrentIndex(0)

        self.ui.radioButton_ubMantidStyle.setChecked(True)
        self.ui.lineEdit_numSurveyOutput.setText('50')
        self.ui.checkBox_sortDescending.setChecked(False)
        self.ui.radioButton_sortByCounts.setChecked(True)
        self.ui.radioButton_ubSelectNoScan.setChecked(True)

        # Tab 'Access'
        self.ui.lineEdit_url.setText('http://neutron.ornl.gov/user_data/hb3a/')
        self.ui.comboBox_mode.setCurrentIndex(0)
        self.ui.lineEdit_localSpiceDir.setEnabled(True)
        self.ui.pushButton_browseLocalDataDir.setEnabled(True)

        # progress bars
        self.ui.progressBar_mergeScans.setRange(0, 20)
        self.ui.progressBar_mergeScans.setValue(0)

        # check boxes
        self.ui.graphicsView_detector2dPlot.set_parent_window(self)

        # background points
        self.ui.lineEdit_backgroundPts.setText('1, 1')

        return

    def _build_peak_info_list(self, zero_hkl, is_spice=True):
        """ Build a list of PeakInfo to build peak workspace
        peak HKL can be set to zero or from table
        :return: list of peak information, which is a PeakProcessRecord instance
        """
        # Collecting all peaks that will be used to refine UB matrix
        row_index_list = self.ui.tableWidget_peaksCalUB.get_selected_rows(True)
        if len(row_index_list) < 3:
            err_msg = 'At least 3 peaks must be selected to refine UB matrix.' \
                      'Now it is only %d selected.' % len(row_index_list)
            self.pop_one_button_dialog(err_msg)
            return

        # loop over all peaks for peak information
        peak_info_list = list()
        status, exp_number = gutil.parse_integers_editors(self.ui.lineEdit_exp)
        assert status
        for i_row in row_index_list:
            scan_num, pt_num = self.ui.tableWidget_peaksCalUB.get_exp_info(i_row)
            if pt_num < 0:
                pt_num = None
            peak_info = self._myControl.get_peak_info(exp_number, scan_num, pt_num)
            assert isinstance(peak_info, r4c.PeakProcessRecord)

            if zero_hkl:
                # set HKL to zero
                peak_info.set_hkl(0., 0., 0.)
            elif is_spice:
                # set from table
                spice_hkl = self.ui.tableWidget_peaksCalUB.get_hkl(i_row, True)
                peak_info.set_hkl_np_array(numpy.array(spice_hkl))
            else:
                calculated_hkl = self.ui.tableWidget_peaksCalUB.get_hkl(i_row, False)
                peak_info.set_hkl_np_array(numpy.array(calculated_hkl))
            # END-IF-ELSE

            peak_info_list.append(peak_info)
        # END-FOR

        return peak_info_list

    def _show_refined_ub_result(self):
        """
        Show the result from refined UB matrix
        :return:
        """
        # Deal with result
        ub_matrix, lattice, lattice_error = self._myControl.get_refined_ub_matrix()
        # ub matrix
        self.ui.tableWidget_ubMatrix.set_from_matrix(ub_matrix)

        # lattice parameter
        assert isinstance(lattice, list)
        assert len(lattice) == 6
        self.ui.lineEdit_aUnitCell.setText('%.5f' % lattice[0])
        self.ui.lineEdit_bUnitCell.setText('%.5f' % lattice[1])
        self.ui.lineEdit_cUnitCell.setText('%.5f' % lattice[2])
        self.ui.lineEdit_alphaUnitCell.setText('%.5f' % lattice[3])
        self.ui.lineEdit_betaUnitCell.setText('%.5f' % lattice[4])
        self.ui.lineEdit_gammaUnitCell.setText('%.5f' % lattice[5])

        assert isinstance(lattice_error, list)
        assert len(lattice_error) == 6
        self.ui.lineEdit_aError.setText('%.5f' % lattice_error[0])
        self.ui.lineEdit_bError.setText('%.5f' % lattice_error[1])
        self.ui.lineEdit_cError.setText('%.5f' % lattice_error[2])
        self.ui.lineEdit_alphaError.setText('%.5f' % lattice_error[3])
        self.ui.lineEdit_betaError.setText('%.5f' % lattice_error[4])
        self.ui.lineEdit_gammaError.setText('%.5f' % lattice_error[5])

        return

    def action_save_project(self):
        """
        Save project
        :return:
        """
        # read project file name
        project_file_name = str(QtGui.QFileDialog.getSaveFileName(self, 'Specify Project File', os.getcwd()))
        # NEXT ISSUE - consider to allow incremental project saving technique
        if os.path.exists(project_file_name):
            yes = gutil.show_message(self, 'Project file %s does exist. This is supposed to be '
                                           'an incremental save.' % project_file_name)
            if yes:
                print '[INFO] Save project in incremental way.'
            else:
                print '[INFO] Saving activity is cancelled.'
        else:
            print '[INFO] Saving current project to %s.' % project_file_name

        # gather some useful information
        ui_dict = dict()
        ui_dict['exp number'] = str(self.ui.lineEdit_exp.text())
        ui_dict['local spice dir'] = str(self.ui.lineEdit_localSpiceDir.text())
        ui_dict['work dir'] = str(self.ui.lineEdit_workDir.text())
        ui_dict['survey start'] = str(self.ui.lineEdit_surveyStartPt.text())
        ui_dict['survey stop'] = str(self.ui.lineEdit_surveyEndPt.text())

        # export/save project
        self._myControl.export_project(project_file_name, ui_dict)

        # register and make it as a queue for last n opened/saved project
        last_1_path = str(self.ui.label_last1Path.text())
        if last_1_path != project_file_name:
            self.ui.label_last3Path.setText(self.ui.label_last2Path.text())
            self.ui.label_last2Path.setText(self.ui.label_last1Path.text())
            self.ui.label_last1Path.setText(last_1_path)
        # END-IF

        return

    def action_load_project(self):
        """
        Load project
        :return:
        """
        project_file_name = str(QtGui.QFileDialog.getOpenFileName(self, 'Choose Project File', os.getcwd()))

        # make it as a queue for last n opened/saved project
        last_1_path = str(self.ui.label_last1Path.text())
        if last_1_path != project_file_name:
            self.ui.label_last3Path.setText(self.ui.label_last2Path.text())
            self.ui.label_last2Path.setText(self.ui.label_last1Path.text())
            self.ui.label_last1Path.setText(last_1_path)
        # END-IF

        self.load_project(project_file_name)

        return

    def load_project(self, project_file_name):
        """
        Load a saved project
        :param project_file_name:
        :return:
        """
        assert isinstance(project_file_name, str), 'Project file name %s must be a string but not %s.' \
                                                   '' % (str(project_file_name), type(project_file_name))
        assert os.path.exists(project_file_name), 'Project file "%s" cannot be found.' % project_file_name

        # load project
        ui_dict = self._myControl.load_project(project_file_name)

        # set the UI parameters to GUI
        try:
            self.ui.lineEdit_localSpiceDir.setText(ui_dict['local spice dir'])
            self.ui.lineEdit_workDir.setText(ui_dict['work dir'])
            self.ui.lineEdit_surveyStartPt.setText(ui_dict['survey start'])
            self.ui.lineEdit_surveyEndPt.setText(ui_dict['survey stop'])

            # now try to call some actions
            self.do_apply_setup()
            self.do_set_experiment()
        except KeyError:
            print '[Error] Some field cannot be found.'

        return

    def action_load_last_project(self):
        """
        Load last project
        :return:
        """
        project_file_name = str(self.ui.label_last1Path.text())
        if os.path.exists(project_file_name) is False:
            self.pop_one_button_dialog('Last saved project %s cannot be located.' % project_file_name)
        else:
            ui_dict = self._myControl.load_project(project_file_name)

            # set the UI parameters to GUI
            try:
                self.ui.lineEdit_localSpiceDir.setText(ui_dict['local spice dir'])
                self.ui.lineEdit_workDir.setText(ui_dict['work dir'])
                self.ui.lineEdit_surveyStartPt.setText(ui_dict['survey start'])
                self.ui.lineEdit_surveyEndPt.setText(ui_dict['survey stop'])

                # now try to call some actions
                self.do_apply_setup()
                self.do_set_experiment()
            except KeyError:
                print '[Error] Some field cannot be found.'

        return

    def closeEvent(self, QCloseEvent):
        """
        Close event
        :param QCloseEvent:
        :return:
        """
        self.menu_quit()

        return

    def do_accept_ub(self):
        """ Accept the calculated UB matrix and thus put to controller
        """
        # get the experiment number
        exp_number = int(str(self.ui.lineEdit_exp.text()))

        # get matrix
        curr_ub = self.ui.tableWidget_ubMatrix.get_matrix()

        # synchronize UB matrix to tableWidget_ubInUse
        self.ui.tableWidget_ubInUse.set_from_matrix(curr_ub)

        # set UB matrix to system
        self._myControl.set_ub_matrix(exp_number, curr_ub)

        return

    def do_add_peaks_for_ub(self):
        """ In tab-survey, merge selected scans, find peaks in merged data and
         switch to UB matrix calculation tab and add to table
        :return:
        """
        # get selected scans
        selected_row_index_list = self.ui.tableWidget_surveyTable.get_selected_rows(True)
        scan_number_list = self.ui.tableWidget_surveyTable.get_scan_numbers(selected_row_index_list)
        if len(scan_number_list) == 0:
            self.pop_one_button_dialog('No scan is selected.')
            return

        # get experiment number
        status, exp_number = gutil.parse_integers_editors(self.ui.lineEdit_exp)
        if not status:
            self.pop_one_button_dialog('Unable to get experiment number\n  due to %s.' % str(exp_number))
            return

        # switch to tab-3
        self.ui.tabWidget.setCurrentIndex(MainWindow.TabPage['Calculate UB'])

        # prototype for a new thread
        self.ui.progressBar_add_ub_peaks.setRange(0, len(scan_number_list))
        self._addUBPeaksThread = AddPeaksThread(self, exp_number, scan_number_list)
        self._addUBPeaksThread.start()

        # set the flag/notification where the indexing (HKL) from
        self.ui.lineEdit_peaksIndexedBy.setText(IndexFromSpice)

        return

    def add_scans_ub_table(self, scan_list):
        """

        :param scan_list:
        :return:
        """
        # TODO/FIXME/ISSUE/NOW - consider to refactor with do_add_peaks_for_ub() and
        # get experiment number
        status, exp_number = gutil.parse_integers_editors(self.ui.lineEdit_exp)
        if not status:
            self.pop_one_button_dialog('Unable to get experiment number\n  due to %s.' % str(exp_number))
            return

        # switch to tab-3
        # self.ui.tabWidget.setCurrentIndex(MainWindow.TabPage['Calculate UB'])

        # prototype for a new thread
        self.ui.progressBar_add_ub_peaks.setRange(0, len(scan_list))
        self._addUBPeaksThread = AddPeaksThread(self, exp_number, scan_list)
        self._addUBPeaksThread.start()

        # set the flag/notification where the indexing (HKL) from
        self.ui.lineEdit_peaksIndexedBy.setText(IndexFromSpice)

        return

    def do_add_roi(self):
        """ Add region of interest to 2D image
        :return:
        """
        # set the button to next mode
        if str(self.ui.pushButton_addROI.text()) == 'Edit ROI':
            # enter adding ROI mode
            self.ui.graphicsView_detector2dPlot.enter_roi_mode(state=True)
            # rename the button
            self.ui.pushButton_addROI.setText('Quit ROI')
        else:
            # quit editing ROI mode
            self.ui.graphicsView_detector2dPlot.enter_roi_mode(state=False)
            # rename the button
            self.ui.pushButton_addROI.setText('Edit ROI')
        # END-IF-ELSE

        return

    def do_add_scans_merge(self):
        """ Add scans to merge
        :return:
        """
        # Get list of scans
        scan_list = gutil.parse_integer_list(str(self.ui.lineEdit_listScansSliceView.text()))
        if len(scan_list) == 0:
            self.pop_one_button_dialog('Scan list is empty.')

        # Set table
        self.ui.tableWidget_mergeScans.append_scans(scans=scan_list, allow_duplicate_scans=False)

        return

    def do_add_ub_peaks(self):
        """
        Launch dialog to add UB peaks
        :return:
        """
        if self._addUBPeaksDialog is None:
            self._addUBPeaksDialog = FindUBUtility.AddScansForUBDialog(self)

        self._addUBPeaksDialog.show()

        return

    # def do_add_ub_peak(self):
    #     """ Add current to ub peaks
    #     :return:
    #     """
    #     # TODO/FIXME/ISSUE/NOW - Find out whether this method is still needed
    #     # Add peak
    #     status, int_list = gutil.parse_integers_editors([self.ui.lineEdit_exp,
    #                                                      self.ui.lineEdit_scanNumber])
    #     if status is False:
    #         self.pop_one_button_dialog(int_list)
    #         return
    #     exp_no, scan_no = int_list
    #
    #     # Get HKL from GUI
    #     status, float_list = gutil.parse_float_editors([self.ui.lineEdit_H,
    #                                                     self.ui.lineEdit_K,
    #                                                     self.ui.lineEdit_L])
    #     if status is False:
    #         err_msg = float_list
    #         self.pop_one_button_dialog(err_msg)
    #         return
    #     h, k, l = float_list
    #
    #     try:
    #         peak_info_obj = self._myControl.get_peak_info(exp_no, scan_no)
    #     except AssertionError as ass_err:
    #         self.pop_one_button_dialog(str(ass_err))
    #         return
    #
    #     assert isinstance(peak_info_obj, r4c.PeakProcessRecord)
    #     peak_info_obj.set_hkl(h, k, l)
    #     self.set_ub_peak_table(peak_info_obj)
    #
    #     # Clear
    #     self.ui.lineEdit_scanNumber.setText('')
    #
    #     self.ui.lineEdit_sampleQx.setText('')
    #     self.ui.lineEdit_sampleQy.setText('')
    #     self.ui.lineEdit_sampleQz.setText('')
    #
    #     self.ui.lineEdit_H.setText('')
    #     self.ui.lineEdit_K.setText('')
    #     self.ui.lineEdit_L.setText('')
    #
    #     # set the flag/notification where the indexing (HKL) from
    #     self.ui.lineEdit_peaksIndexedBy.setText(IndexFromSpice)
    #
    #     return

    def do_add_k_shift_vector(self):
        """ Add a k-shift vector
        :return:
        """
        # parse the k-vector
        status, ret_obj = gutil.parse_float_editors([self.ui.lineEdit_kX, self.ui.lineEdit_kY, self.ui.lineEdit_kZ],
                                                    allow_blank=False)
        if status is False:
            error_message = ret_obj
            self.pop_one_button_dialog(error_message)
            return
        else:
            k_x, k_y, k_z = ret_obj

        # add to controller
        k_index = self._myControl.add_k_shift_vector(k_x, k_y, k_z)

        # add to table and combo-box
        self.ui.tableWidget_kShift.add_k_vector(k_index, k_x, k_y, k_z)

        combo_message = '%d: (%.5f, %.5f, %.5f)' % (k_index, k_x, k_y, k_z)
        self.ui.comboBox_kVectors.addItem(combo_message)

        return

    def do_apply_k_shift(self):
        """ Apply k-shift to selected reflections
        :return:
        """
        # get the selected scans
        scan_list = list()
        selected_row_numbers = self.ui.tableWidget_mergeScans.get_selected_rows(True)
        for row_index in selected_row_numbers:
            scan_number = self.ui.tableWidget_mergeScans.get_scan_number(row_index)
            scan_list.append(scan_number)

        # get the k-vector
        k_shift_message = str(self.ui.comboBox_kVectors.currentText())
        k_index = int(k_shift_message.split(':')[0])

        # set to controller
        self._myControl.set_k_shift(scan_list, k_index)

        # set k-shift to table
        # exp_number = int(self.ui.lineEdit_exp.text())
        for row_index in selected_row_numbers:
            self.ui.tableWidget_mergeScans.set_k_shift_index(row_index, k_index)
            # scan_number = self.ui.tableWidget_mergeScans.get_scan_number(row_index)

        return

    def do_apply_roi(self):
        """ Save current selection of region of interest
        :return:
        """
        lower_left_c, upper_right_c = self.ui.graphicsView_detector2dPlot.get_roi()
        # at the very beginning, the lower left and upper right are same
        if lower_left_c[0] == upper_right_c[0] or lower_left_c[1] == upper_right_c[1]:
            return

        status, par_val_list = gutil.parse_integers_editors([self.ui.lineEdit_exp, self.ui.lineEdit_run])
        assert status, str(par_val_list)
        exp_number = par_val_list[0]
        scan_number = par_val_list[1]

        self._myControl.set_roi(exp_number, scan_number, lower_left_c, upper_right_c)

        return

    def do_apply_setup(self):
        """
        Purpose:
         - Apply the setup to controller.
        Requirements:
         - data directory, working directory must be given; but not necessarily correct
         - URL must be given; but not necessary to be correct
        :return:
        """
        # get data directory, working directory and data server URL from GUI
        local_data_dir = str(self.ui.lineEdit_localSpiceDir.text()).strip()
        working_dir = str(self.ui.lineEdit_workDir.text()).strip()
        data_server = str(self.ui.lineEdit_url.text()).strip()

        # set to my controller
        status, err_msg = self._myControl.set_local_data_dir(local_data_dir)
        if not status:
            raise RuntimeError(err_msg)
        self._myControl.set_working_directory(working_dir)
        self._myControl.set_server_url(data_server, check_link=False)

        # check
        error_message = ''

        # local data dir
        if local_data_dir == '':
            error_message += 'Local data directory is not specified!\n'
        elif os.path.exists(local_data_dir) is False:
            try:
                os.mkdir(local_data_dir)
            except OSError as os_error:
                error_message += 'Unable to create local data directory %s due to %s.\n' % (
                    local_data_dir, str(os_error))
                self.ui.lineEdit_localSpiceDir.setStyleSheet("color: red;")
            else:
                self.ui.lineEdit_localSpiceDir.setStyleSheet("color: green;")
        else:
            self.ui.lineEdit_localSpiceDir.setStyleSheet("color: green;")
        # END-IF-ELSE

        # working directory
        if working_dir == '':
            error_message += 'Working directory is not specified!\n'
        elif os.path.exists(working_dir) is False:
            try:
                os.mkdir(working_dir)
                self.ui.lineEdit_workDir.setStyleSheet("color: green;")
            except OSError as os_error:
                error_message += 'Unable to create working directory %s due to %s.\n' % (
                    working_dir, str(os_error))
                self.ui.lineEdit_workDir.setStyleSheet("color: red;")
        else:
            self.ui.lineEdit_workDir.setStyleSheet("color: green;")
        # END-IF-ELSE

        # Set the URL red as it is better not check at this stage. Leave it to user
        self.ui.lineEdit_url.setStyleSheet("color: black;")

        if len(error_message) > 0:
            self.pop_one_button_dialog(error_message)

        return

    def do_browse_local_cache_dir(self):
        """ Browse local cache directory
        :return:
        """
        local_cache_dir = str(QtGui.QFileDialog.getExistingDirectory(self,
                                                                     'Get Local Cache Directory',
                                                                     self._homeSrcDir))

        # Set local directory to control
        status, error_message = self._myControl.set_local_data_dir(local_cache_dir)
        if status is False:
            self.pop_one_button_dialog(error_message)
            return

        # Synchronize to local data/spice directory and local cache directory
        if str(self.ui.lineEdit_localSpiceDir.text()) != '':
            prev_dir = str(self.ui.lineEdit_localSrcDir.text())
            self.pop_one_button_dialog('Local data directory was set up as %s' %
                                       prev_dir)
        self.ui.lineEdit_localSrcDir.setText(local_cache_dir)
        self.ui.lineEdit_localSpiceDir.setText(local_cache_dir)

        return

    def do_browse_local_spice_data(self):
        """ Browse local source SPICE data directory
        """
        src_spice_dir = str(QtGui.QFileDialog.getExistingDirectory(self, 'Get Directory',
                                                                   self._homeSrcDir))
        # Set local data directory to controller
        status, error_message = self._myControl.set_local_data_dir(src_spice_dir)
        if status is False:
            self.pop_one_button_dialog(error_message)
            return

        self._homeSrcDir = src_spice_dir
        self.ui.lineEdit_localSpiceDir.setText(src_spice_dir)

        return

    def do_browse_working_dir(self):
        """
        Browse and set up working directory
        :return:
        """
        work_dir = str(QtGui.QFileDialog.getExistingDirectory(self, 'Get Working Directory', self._homeDir))
        status, error_message = self._myControl.set_working_directory(work_dir)
        if status is False:
            self.pop_one_button_dialog(error_message)
        else:
            self.ui.lineEdit_workDir.setText(work_dir)

        return

    def do_cal_ub_matrix(self):
        """ Calculate UB matrix by 2 or 3 reflections
        """
        # Get reflections selected to calculate UB matrix
        num_rows = self.ui.tableWidget_peaksCalUB.rowCount()
        peak_info_list = list()
        status, exp_number = gutil.parse_integers_editors(self.ui.lineEdit_exp)
        assert status
        for i_row in xrange(num_rows):
            if self.ui.tableWidget_peaksCalUB.is_selected(i_row) is True:
                scan_num, pt_num = self.ui.tableWidget_peaksCalUB.get_exp_info(i_row)
                if pt_num < 0:
                    pt_num = None
                peak_info = self._myControl.get_peak_info(exp_number, scan_num, pt_num)
                assert isinstance(peak_info, r4c.PeakProcessRecord)
                peak_info_list.append(peak_info)
        # END-FOR

        # Get lattice
        status, ret_obj = self._get_lattice_parameters()
        if status is True:
            a, b, c, alpha, beta, gamma = ret_obj
        else:
            err_msg = ret_obj
            self.pop_one_button_dialog(err_msg)
            return

        # Calculate UB matrix
        status, ub_matrix = self._myControl.calculate_ub_matrix(peak_info_list, a, b, c,
                                                                alpha, beta, gamma)

        # Deal with result
        if status is True:
            self.ui.tableWidget_ubMatrix.set_from_matrix(ub_matrix)

        else:
            err_msg = ub_matrix
            self.pop_one_button_dialog(err_msg)

        return

    def do_change_data_access_mode(self):
        """ Change data access mode between downloading from server and local
        Event handling methods
        :return:
        """
        new_mode = str(self.ui.comboBox_mode.currentText())
        self._dataAccessMode = new_mode

        if new_mode.startswith('Local') is True:
            self.ui.lineEdit_localSpiceDir.setEnabled(True)
            self.ui.pushButton_browseLocalDataDir.setEnabled(True)
            self.ui.lineEdit_url.setEnabled(False)
            self.ui.lineEdit_localSrcDir.setEnabled(False)
            self.ui.pushButton_browseLocalCache.setEnabled(False)
            self._allowDownload = False
        else:
            self.ui.lineEdit_localSpiceDir.setEnabled(False)
            self.ui.pushButton_browseLocalDataDir.setEnabled(False)
            self.ui.lineEdit_url.setEnabled(True)
            self.ui.lineEdit_localSrcDir.setEnabled(True)
            self.ui.pushButton_browseLocalCache.setEnabled(True)
            self._allowDownload = True

        return

    def do_change_instrument_name(self):
        """ Handing the event as the instrument name is changed
        :return:
        """
        new_instrument = str(self.ui.comboBox_instrument.currentText())
        self.pop_one_button_dialog('Change of instrument during data processing is dangerous.')
        status, error_message = self._myControl.set_instrument_name(new_instrument)
        if status is False:
            self.pop_one_button_dialog(error_message)

        return

    def do_clear_all_peaks_index_ub(self):
        """
        Set all peaks' indexes in UB matrix calculation tab to zero
        :return:
        """
        num_rows = self.ui.tableWidget_peaksCalUB.rowCount()
        for i_row in range(num_rows):
            self.ui.tableWidget_peaksCalUB.set_hkl(i_row, [0., 0., 0.], is_spice_hkl=False)

        return

    def do_clear_merge_table(self):
        """
        Clear the merge/peak-integration table
        :return:
        """
        # clear
        self.ui.tableWidget_mergeScans.remove_all_rows()

    def do_clear_peak_integration_canvas(self):
        """
        clear the peak integration canvas and the integrated values
        :return:
        """
        self.ui.graphicsView_integratedPeakView.clear_all_lines()

        self.ui.lineEdit_rawSinglePeakIntensity.setText('')
        self.ui.lineEdit_intensity2.setText('')
        self.ui.lineEdit_gaussianPeakIntensity.setText('')
        self.ui.lineEdit_errorIntensity1.setText('')
        self.ui.lineEdit_errorIntensity2.setText('')
        self.ui.lineEdit_errorIntensity3.setText('')

        return

    def do_clear_survey(self):
        """
        Clear survey and survey table.
        As myController does not store any survey information,
        there is no need to clear any data structure in myController
        :return:
        """
        # Clear table
        self.ui.tableWidget_surveyTable.remove_all_rows()
        self.ui.tableWidget_surveyTable.reset()

        return

    def do_clear_ub_peaks(self):
        """
        Clear all peaks in UB-Peak table
        :return:
        """
        num_rows = self.ui.tableWidget_peaksCalUB.rowCount()
        row_number_list = range(num_rows)
        self.ui.tableWidget_peaksCalUB.delete_rows(row_number_list)

        return

    def do_convert_merged_to_hkl(self):
        """
        convert merged workspace in Q-sample frame to HKL frame
        :return:
        """
        # get experiment number
        exp_number = int(str(self.ui.lineEdit_exp.text()))

        # get the lines that are selected
        selected_row_number_list = self.ui.tableWidget_mergeScans.get_selected_rows(True)

        for row_number in selected_row_number_list:
            scan_number = self.ui.tableWidget_mergeScans.get_scan_number(row_number)
            status, ret_obj = self._myControl.get_pt_numbers(exp_number, scan_number)
            if not status:
                raise RuntimeError('It is not possible to fail to get Pt number list at this stage.'
                                   'Error is due to %s.' % str(ret_obj))
            pt_number_list = ret_obj

            # set intensity to zero and error message if fails to get Pt.
            self._myControl.convert_merged_ws_to_hkl(exp_number, scan_number, pt_number_list)

        return

    def do_del_roi(self):
        """ Delete ROI
        :return:
        """
        self.ui.graphicsView_detector2dPlot.remove_roi()

        return

    def do_del_ub_peaks(self):
        """
        Delete a peak in UB-Peak table
        :return:
        """
        # Find out the lines to get deleted
        row_num_list = self.ui.tableWidget_peaksCalUB.get_selected_rows()

        # Delete
        self.ui.tableWidget_peaksCalUB.delete_rows(row_num_list)

        return

    def do_download_spice_data(self):
        """ Download SPICE data
        :return:
        """
        # Check scans to download
        scan_list_str = str(self.ui.lineEdit_downloadScans.text())
        if len(scan_list_str) > 0:
            # user specifies scans to download
            valid, scan_list = hb3a_util.parse_int_array(scan_list_str)
            if valid is False:
                error_message = scan_list
                self.pop_one_button_dialog(error_message)
        else:
            # Get all scans
            status, ret_obj = gutil.parse_integers_editors([self.ui.lineEdit_exp])
            if status is False:
                self.pop_one_button_dialog(ret_obj)
                return
            exp_no = ret_obj
            assert isinstance(exp_no, int)
            server_url = str(self.ui.lineEdit_url.text())
            scan_list = hb3a_util.get_scans_list(server_url, exp_no, return_list=True)
        self.pop_one_button_dialog('Going to download scans %s.' % str(scan_list))

        # Check location
        destination_dir = str(self.ui.lineEdit_localSrcDir.text())
        status, error_message = self._myControl.set_local_data_dir(destination_dir)
        if status is False:
            self.pop_one_button_dialog(error_message)
        else:
            self.pop_one_button_dialog('Spice files will be downloaded to %s.' % destination_dir)

        # Set up myControl for downloading data
        exp_no = int(self.ui.lineEdit_exp.text())
        self._myControl.set_exp_number(exp_no)

        server_url = str(self.ui.lineEdit_url.text())
        status, error_message = self._myControl.set_server_url(server_url)
        if status is False:
            self.pop_one_button_dialog(error_message)
            return

        # Download
        self._myControl.download_data_set(scan_list)

        return

    def find_peak_in_scan(self , scan_number, load_spice_hkl):
        """ Find peak in a given scan and record it
        """
        # Get experiment, scan and pt
        status, ret_obj = gutil.parse_integers_editors([self.ui.lineEdit_exp])
        if status is True:
            exp_no = ret_obj
        else:
            self.pop_one_button_dialog(ret_obj)
            return

        # merge peak if necessary
        if self._myControl.has_merged_data(exp_no, scan_number) is False:
            status, err_msg = self._myControl.merge_pts_in_scan(exp_no, scan_number, [])
            if status is False:
                self.pop_one_button_dialog(err_msg)

        # Find peak
        status, err_msg = self._myControl.find_peak(exp_no, scan_number)
        if status is False:
            self.pop_one_button_dialog(ret_obj)
            return

        # Get information from the latest (integrated) peak
        # if load_spice_hkl:
        #     # This is the first time that in the workflow to get HKL from MD workspace
        #     peak_info = self._myControl.get_peak_info(exp_no, scan_number)
        #     assert peak_info is not None, 'Unable to locate PeakProcessRecord (peak info).'
        # # END-IF

        # Set up correct values to table tableWidget_peaksCalUB
        peak_info = self._myControl.get_peak_info(exp_no, scan_number)
        assert peak_info is not None, 'Unable to locate PeakProcessRecord (peak info).'

        if load_spice_hkl:
            h, k, l = peak_info.get_hkl()
            hkl = (h, k, l)
        else:
            hkl = ()

        q_x, q_y, q_z = peak_info.get_peak_centre()
        vec_q = (q_x, q_y, q_z)

        return hkl, vec_q

    def do_export_selected_peaks_to_integrate(self):
        """
        export (to file or just print out) the scans that are selected for integration
        :param self:
        :return:
        """
        # get selected rows' scan numbers
        scan_tuple_list = self.ui.tableWidget_mergeScans.get_selected_scans()
        scan_number_list = list()
        for tup in scan_tuple_list:
            scan_number_list.append(tup[0])
        scan_number_list.sort()

        info_str = '# Selected scans: \n'
        info_str += '{0}'.format(scan_number_list)

        print '[TEMP] Selected scans:\n{0}'.format(info_str)

        return

    def do_export_to_fp(self):
        """ Export selected reflections to Fullprof single crystal data file for analysis
        :return:
        """
        # get selected lines
        selected_rows = self.ui.tableWidget_mergeScans.get_selected_rows(True)
        if len(selected_rows) == 0:
            self.pop_one_button_dialog('There isn\'t any peak selected.')
            return

        # get the file name
        fp_name = str(QtGui.QFileDialog.getSaveFileName(self, 'Save to Fullprof File'))

        # return due to cancel
        if len(fp_name) == 0:
            return

        # collect information
        exp_number = int(self.ui.lineEdit_exp.text())
        scan_number_list = list()
        for i_row in selected_rows:
            scan_number_list.append(self.ui.tableWidget_mergeScans.get_scan_number(i_row))

        # write
        user_header = str(self.ui.lineEdit_fpHeader.text())
        try:
            export_absorption = self.ui.checkBox_exportAbsorptionToFP.isChecked()

            status, file_content = self._myControl.export_to_fullprof(exp_number, scan_number_list,
                                                                      user_header, export_absorption, fp_name)
            self.ui.plainTextEdit_fpContent.setPlainText(file_content)
            if status is False:
                error_msg = file_content
                if error_msg.startswith('Peak index error'):
                    error_msg = 'You may forget to index peak\n' + error_msg
                self.pop_one_button_dialog(error_msg)
        except AssertionError as a_err:
            self.pop_one_button_dialog(str(a_err))
            return
        except KeyError as key_err:
            self.pop_one_button_dialog(str(key_err))

        return

    def do_filter_sort_survey_table(self):
        """
        Sort and filter survey table by specified field
        Requirements:
        Guarantees: the original table is cleared and a new list is appended
        :return:
        """
        # Get column name
        if self.ui.radioButton_sortByScan.isChecked():
            column_name = 'Scan'
        elif self.ui.radioButton_sortByCounts.isChecked():
            column_name = 'Max Counts'
        elif self.ui.radioButton_sortByTemp.isChecked():
            column_name = 'Sample Temp'
        else:
            self.pop_one_button_dialog('No column is selected to sort.')
            return

        # Get filters
        status, ret_obj = gutil.parse_integers_editors([self.ui.lineEdit_filterScanLower,
                                                        self.ui.lineEdit_filterScanUpper],
                                                       allow_blank=True)

        # return with error
        if status is False:
            self.pop_one_button_dialog(ret_obj)
            return

        # set up default with return as None
        start_scan_number = ret_obj[0]
        if start_scan_number is None:
            start_scan_number = 0
        end_scan_number = ret_obj[1]
        if end_scan_number is None:
            end_scan_number = sys.maxint

        status, ret_obj = gutil.parse_float_editors([self.ui.lineEdit_filterCountsLower,
                                                     self.ui.lineEdit_filterCountsUpper],
                                                    allow_blank=True)
        if status is False:
            # return with error message
            self.pop_one_button_dialog(ret_obj)
            return

        # set up default with return as None
        min_counts = ret_obj[0]
        if min_counts is None:
            min_counts = -0.0
        max_counts = ret_obj[1]
        if max_counts is None:
            max_counts = sys.float_info.max

        # filter and sort
        ascending_order = not self.ui.checkBox_sortDescending.isChecked()
        if ascending_order:
            sort_order = 0
        else:
            sort_order = 1
        self.ui.tableWidget_surveyTable.filter_and_sort(start_scan_number, end_scan_number,
                                                        min_counts, max_counts,
                                                        column_name, sort_order)

        return

    def do_integrate_single_scan(self):
        """
        integrate a single scan in 'Peak Integration' tab
        Note: this is an experimenntal replacement for do_integrate_per_pt
        :return:
        """
        # parse experiment and scan number
        status, ret_obj = gutil.parse_integers_editors([self.ui.lineEdit_exp,
                                                        self.ui.lineEdit_scanIntegratePeak])
        if not status:
            self.pop_one_button_dialog('Unable to integrate peak due to %s.' % ret_obj)
            return
        else:
            exp_number, scan_number = ret_obj

        # parse normalization type
        normalization = str(self.ui.comboBox_ptCountType.currentText())
        if normalization.count('Time') > 0:
            norm_type = 'time'
        elif normalization.count('Monitor') > 0:
            norm_type = 'monitor'
        else:
            norm_type = ''

        # parse scale factor
        try:
            intensity_scale_factor = float(self.ui.lineEdit_scaleFactorScan.text())
        except ValueError:
            intensity_scale_factor = 1.

        # calculate peak center (weighted)
        status, ret_obj = self._myControl.find_peak(exp_number, scan_number)
        if status is False:
            error_message = ret_obj
            self.pop_one_button_dialog(error_message)
            return
        else:
            this_peak_centre = ret_obj

        # mask workspace
        mask_name = str(self.ui.comboBox_maskNames2.currentText())
        if mask_name.lower() == 'no mask':
            mask_name = ''

        # ui.lineEdit_backgroundPts and set default in init_widgets
        bkgd_pt_tuple = gutil.parse_integer_list(str(self.ui.lineEdit_backgroundPts.text()), 2)

        # integrate peak
        try:
            int_peak_dict = self._myControl.integrate_scan_peak(exp_number=exp_number,
                                                                scan_number=scan_number,
                                                                peak_centre=this_peak_centre,
                                                                mask_name=mask_name,
                                                                normalization=norm_type,
                                                                scale_factor=intensity_scale_factor,
                                                                background_pt_tuple=bkgd_pt_tuple)
        except RuntimeError as run_error:
            self.pop_one_button_dialog('Unable to integrate peak for scan {0} due to {1}.'
                                       ''.format(scan_number, run_error))
            return

        # plot calculated motor position (or Pt.) - integrated intensity per Pts.
        motor_pos_vec = int_peak_dict['motor positions']
        pt_intensity_vec = int_peak_dict['pt intensities']
        self.ui.graphicsView_integratedPeakView.plot_raw_data(motor_pos_vec, pt_intensity_vec)

        # set calculated values
        try:
            self.ui.lineEdit_rawSinglePeakIntensity.setText('{0:.7f}'.format(int_peak_dict['simple intensity']))
            self.ui.lineEdit_errorIntensity1.setText('{0:.7f}'.format(int_peak_dict['simple error']))
            self.ui.lineEdit_avgBackground.setText('{0:.7f}'.format(int_peak_dict['simple background']))
            self.ui.lineEdit_intensity2.setText('{0:.7f}'.format(int_peak_dict['intensity 2']))
            if int_peak_dict['error 2'] is None:
                self.ui.lineEdit_errorIntensity2.setText('inf')
            else:
                self.ui.lineEdit_errorIntensity2.setText('{0:.7f}'.format(int_peak_dict['error 2']))
            self.ui.lineEdit_ptRange.setText('{0}'.format(int_peak_dict['pt_range']))
            self.ui.lineEdit_gaussianPeakIntensity.setText('{0:.7f}'.format(int_peak_dict['gauss intensity']))
            if int_peak_dict['gauss error'] is None:
                self.ui.lineEdit_errorIntensity3.setText('inf')
            else:
                self.ui.lineEdit_errorIntensity3.setText('{0:.7f}'.format(int_peak_dict['gauss error']))
            self.ui.tableWidget_covariance.set_matrix(int_peak_dict['covariance matrix'])

            fit_param_dict = int_peak_dict['gauss parameters']
            # {'A': 1208.4097237325959, 'x0': 32.175524426773507, 'B': 23.296505385975976, 's': 0.47196665622701633}
            self.ui.lineEdit_peakBackground.setText('{0:.4f}'.format(fit_param_dict['B']))
            self.ui.lineEdit_gaussA.setText('{0:.4f}'.format(fit_param_dict['A']))
            self.ui.lineEdit_gaussSigma.setText('{0:.4f}'.format(fit_param_dict['s']))
            self.ui.lineEdit_gaussB.setText('{0:.4f}'.format(fit_param_dict['B']))

            # plot fitted Gaussian
            fit_gauss_dict = int_peak_dict['gauss parameters']
        except KeyError as key_err:
            raise RuntimeError('Peak integration result dictionary has keys {0}. Error is caused by {1}.'
                               ''.format(int_peak_dict.keys(), key_err))

        self.plot_model_data(motor_pos_vec, fit_gauss_dict)

        return

    def plot_model_data(self, vec_x, params):
        """
        calculate the Y value by the model and plot them.
        the sparse X values will be expanded
        :return:
        """
        # check inputs
        assert isinstance(vec_x, numpy.ndarray), 'vec X {0} must be a numpy.ndarray but not a {1}.' \
                                                 ''.format(vec_x, type(vec_x))
        assert isinstance(params, dict), 'Model parameters {0} must be given by a dictionary but not by a {1}.' \
                                         ''.format(params, type(params))

        # get parameters
        x0 = params['x0']
        gauss_sigma = params['s']
        gauss_a = params['A']
        background = params['B']
        info_str = 'Gaussian fit'

        # plot the data
        # make modelX and modelY for more fine grids
        model_x = peak_integration_utility.get_finer_grid(vec_x, 10)
        model_y = peak_integration_utility.gaussian_linear_background(model_x, x0, gauss_sigma,
                                                                      gauss_a, background)

        # plot the model
        self.ui.graphicsView_integratedPeakView.plot_model(model_x, model_y, title=info_str)

        return

    def do_integrate_peaks(self):
        """ Integrate selected peaks tab-'scan processing'.
        If any scan is not merged, then it will merge the scan first.
        Integrate peaks from the table of merged peak.
        It will so the simple cuboid integration with region of interest and background subtraction.
        :return:
        """
        # get rows to merge
        row_number_list = self.ui.tableWidget_mergeScans.get_selected_rows(True)
        if len(row_number_list) == 0:
            self.pop_one_button_dialog('No scan is selected for scan')
            return

        # get experiment number
        status, ret_obj = gutil.parse_integers_editors(self.ui.lineEdit_exp, allow_blank=False)
        if status:
            exp_number = ret_obj
        else:
            self.pop_one_button_dialog('Unable to get valid experiment number due to %s.' % ret_obj)
            return

        # mask workspace
        selected_mask = str(self.ui.comboBox_maskNames1.currentText())
        if selected_mask.lower().startswith('no mask'):
            selected_mask = ''
            mask_det = False
        else:
            mask_det = True

        # normalization
        norm_str = str(self.ui.comboBox_mergePeakNormType.currentText())
        if norm_str.lower().count('time') > 0:
            norm_type = 'time'
        elif norm_str.lower().count('monitor') > 0:
            norm_type = 'monitor'
        else:
            norm_type = ''

        # background Pt.
        status, num_bg_pt = gutil.parse_integers_editors(self.ui.lineEdit_numPt4Background, allow_blank=False)
        if not status or num_bg_pt == 0:
            self.pop_one_button_dialog('Number of Pt number for background must be larger than 0: %s!' % str(num_bg_pt))
            return

        # get the merging information: each item should be a tuple as (scan number, pt number list, merged)
        scan_number_list = list()
        for row_number in row_number_list:
            # get scan number and pt numbers
            scan_number = self.ui.tableWidget_mergeScans.get_scan_number(row_number)
            status, pt_number_list = self._myControl.get_pt_numbers(exp_number, scan_number)

            # set intensity to zero and error message if fails to get Pt.
            if status is False:
                error_msg = 'Unable to get Pt. of experiment %d scan %d due to %s.' % (exp_number, scan_number,
                                                                                       str(pt_number_list))
                self.controller.set_zero_peak_intensity(exp_number, scan_number)
                self.ui.tableWidget_mergeScans.set_peak_intensity(row_number, scan_number, 0., False,
                                                                  integrate_method='')
                self.ui.tableWidget_mergeScans.set_status(scan_number, error_msg)
                continue

            # merge all Pt. of the scan if they are not merged.
            merged = self.ui.tableWidget_mergeScans.get_merged_status(row_number)

            # add to list
            scan_number_list.append((scan_number, pt_number_list, merged))
            self.ui.tableWidget_mergeScans.set_status(row_number, 'Waiting')
        # END-FOR

        # set the progress bar
        self.ui.progressBar_mergeScans.setRange(0, len(scan_number_list))
        self.ui.progressBar_mergeScans.setValue(0)
        self.ui.progressBar_mergeScans.setTextVisible(True)
        self.ui.progressBar_mergeScans.setStatusTip('Hello')

        # process background setup
        status, ret_obj = gutil.parse_integers_editors([self.ui.lineEdit_numPt4Background,
                                                        self.ui.lineEdit_numPt4BackgroundRight],
                                                       allow_blank=False)
        if not status:
            error_msg = str(ret_obj)
            self.pop_one_button_dialog(error_msg)
            return
        num_pt_bg_left = ret_obj[0]
        num_pt_bg_right = ret_obj[1]

        self._myIntegratePeaksThread = IntegratePeaksThread(self, exp_number, scan_number_list,
                                                            mask_det, selected_mask, norm_type,
                                                            num_pt_bg_left, num_pt_bg_right)
        self._myIntegratePeaksThread.start()

        return

    def do_index_ub_peaks(self):
        """ Index the peaks in the UB matrix peak table
        :return:
        """
        # Get UB matrix
        ub_matrix = self.ui.tableWidget_ubMatrix.get_matrix()
        print '[Info] Get UB matrix from table ', ub_matrix

        # Index all peaks
        num_peaks = self.ui.tableWidget_peaksCalUB.rowCount()
        err_msg = ''
        for i_peak in xrange(num_peaks):
            scan_no = self.ui.tableWidget_peaksCalUB.get_exp_info(i_peak)[0]
            status, ret_obj = self._myControl.index_peak(ub_matrix, scan_number=scan_no)
            if status is True:
                hkl_value = ret_obj[0]
                hkl_error = ret_obj[1]
                self.ui.tableWidget_peaksCalUB.set_hkl(i_peak, hkl_value, is_spice_hkl=False,
                                                       error=hkl_error)
            else:
                err_msg += ret_obj + '\n'
        # END-FOR

        # error message
        if len(err_msg) > 0:
            self.pop_one_button_dialog(err_msg)

        # update the message
        self.ui.lineEdit_peaksIndexedBy.setText(IndexFromUB)

        # enable/disable push buttons
        # self.ui.pushButton_setHKL2Int.setEnabled(True)
        # self.ui.pushButton_undoSetToInteger.setEnabled(True)

        return

    def do_list_scans(self):
        """ List all scans available
        :return:
        """
        # Experiment number
        exp_no = int(self.ui.lineEdit_exp.text())

        access_mode = str(self.ui.comboBox_mode.currentText())
        if access_mode == 'Local':
            spice_dir = str(self.ui.lineEdit_localSpiceDir.text())
            message = hb3a_util.get_scans_list_local_disk(spice_dir, exp_no)
        else:
            url = str(self.ui.lineEdit_url.text())
            message = hb3a_util.get_scans_list(url, exp_no)

        self.pop_one_button_dialog(message)

        return

    def do_load_scan_info(self):
        """ Load SIICE's scan file
        :return:
        """
        # Get scan number
        status, ret_obj = gutil.parse_integers_editors([self.ui.lineEdit_run])
        if status is True:
            scan_no = ret_obj[0]
        else:
            err_msg = ret_obj
            self.pop_one_button_dialog('Unable to get scan number in raw data tab due to %s.' % err_msg)
            return

        status, err_msg = self._myControl.load_spice_scan_file(exp_no=None, scan_no=scan_no)
        if status is False:
            self.pop_one_button_dialog(err_msg)

        return

    def do_load_survey(self):
        """ Load csv file containing experiment-scan survey's result.
        :return:
        """
        # check validity
        num_rows = int(self.ui.lineEdit_numSurveyOutput.text())

        # get the csv file
        file_filter = 'CSV Files (*.csv);;All Files (*)'
        csv_file_name = str(QtGui.QFileDialog.getOpenFileName(self, 'Open Exp-Scan Survey File', self._homeDir,
                                                              file_filter))
        if csv_file_name is None or len(csv_file_name) == 0:
            # return if file selection is cancelled
            return

        # call controller to load
        survey_tuple = self._myControl.load_scan_survey_file(csv_file_name)
        scan_sum_list = survey_tuple[1]
        assert isinstance(scan_sum_list, list), 'Returned value from load scan survey file must be a dictionary.'

        # set the table
        self.ui.tableWidget_surveyTable.set_survey_result(scan_sum_list)
        self.ui.tableWidget_surveyTable.remove_all_rows()
        self.ui.tableWidget_surveyTable.show_reflections(num_rows)

        return

    def do_plot_pt_raw(self):
        """ Plot the Pt.
        """
        # Get measurement pt and the file number
        status, ret_obj = gutil.parse_integers_editors([self.ui.lineEdit_exp,
                                                        self.ui.lineEdit_run,
                                                        self.ui.lineEdit_rawDataPtNo])
        if status is True:
            exp_no = ret_obj[0]
            scan_no = ret_obj[1]
            pt_no = ret_obj[2]
        else:
            self.pop_one_button_dialog(ret_obj)
            return

        # Call to plot 2D
        self._plot_raw_xml_2d(exp_no, scan_no, pt_no)

        return

    def evt_change_normalization(self):
        """
        Integrate Pt. vs integrated intensity of detectors of that Pt. if it is not calculated before
        and then plot pt vs. integrated intensity on
        :return:
        """
        # integrate any how
        # self.do_integrate_per_pt()
        self.do_integrate_single_scan()

        return

    def do_plot_prev_pt_raw(self):
        """ Plot the Pt.
        """
        # Get measurement pt and the file number
        status, ret_obj = gutil.parse_integers_editors([self.ui.lineEdit_exp,
                                                        self.ui.lineEdit_run,
                                                        self.ui.lineEdit_rawDataPtNo])
        if status is True:
            exp_no = ret_obj[0]
            scan_no = ret_obj[1]
            pt_no = ret_obj[2]
        else:
            self.pop_one_button_dialog(ret_obj)
            return

        # Previous one
        pt_no -= 1
        if pt_no <= 0:
            self.pop_one_button_dialog('Pt. = 1 is the first one.')
            return
        else:
            self.ui.lineEdit_rawDataPtNo.setText('%d' % pt_no)

        # Plot
        self._plot_raw_xml_2d(exp_no, scan_no, pt_no)

        return

    def do_plot_prev_scan(self):
        """ Plot the previous scan while keeping the same Pt.
        :return:
        """
        # get current exp number, scan number and pt number
        status, ret_obj = gutil.parse_integers_editors([self.ui.lineEdit_exp,
                                                        self.ui.lineEdit_run,
                                                        self.ui.lineEdit_rawDataPtNo])
        if status is False:
            error_msg = ret_obj
            self.pop_one_button_dialog(error_msg)
            return

        exp_number, scan_number, pt_number = ret_obj

        # get next scan
        scan_number -= 1
        if scan_number < 0:
            self.pop_one_button_dialog('Scan number cannot be negative!')
            return

        # plot
        try:
            self._plot_raw_xml_2d(exp_number, scan_number, pt_number)
        except RuntimeError as err:
            error_msg = 'Unable to plot next scan %d due to %s.' % (scan_number, str(err))
            self.pop_one_button_dialog(error_msg)
            return

        # update line edits
        self.ui.lineEdit_run.setText(str(scan_number))

        return

    def do_plot_next_pt_raw(self):
        """ Plot the Pt.
        """
        # Get measurement pt and the file number
        status, ret_obj = gutil.parse_integers_editors([self.ui.lineEdit_exp,
                                                        self.ui.lineEdit_run,
                                                        self.ui.lineEdit_rawDataPtNo])
        if status is True:
            exp_no = ret_obj[0]
            scan_no = ret_obj[1]
            pt_no = ret_obj[2]
        else:
            self.pop_one_button_dialog(ret_obj)
            return

        # Next Pt
        pt_no += 1
        # get last Pt. number
        status, last_pt_no = self._myControl.get_pt_numbers(exp_no, scan_no)
        if status is False:
            error_message = last_pt_no
            self.pop_one_button_dialog('Unable to access Spice table for scan %d. Reason" %s.' % (
                scan_no, error_message))
        if pt_no > last_pt_no:
            self.pop_one_button_dialog('Pt. = %d is the last one of scan %d.' % (pt_no, scan_no))
            return
        else:
            self.ui.lineEdit_rawDataPtNo.setText('%d' % pt_no)

        # Plot
        self._plot_raw_xml_2d(exp_no, scan_no, pt_no)

        return

    def do_plot_next_scan(self):
        """ Plot the next scan while keeping the same Pt.
        :return:
        """
        # get current exp number, scan number and pt number
        status, ret_obj = gutil.parse_integers_editors([self.ui.lineEdit_exp,
                                                        self.ui.lineEdit_run,
                                                        self.ui.lineEdit_rawDataPtNo])
        if status is False:
            error_msg = ret_obj
            self.pop_one_button_dialog(error_msg)
            return

        exp_number, scan_number, pt_number = ret_obj

        # get next scan
        scan_number += 1

        # plot
        try:
            self._plot_raw_xml_2d(exp_number, scan_number, pt_number)
        except RuntimeError as err:
            error_msg = 'Unable to plot next scan %d due to %s.' % (scan_number, str(err))
            self.pop_one_button_dialog(error_msg)
            return

        # update line edits
        self.ui.lineEdit_run.setText(str(scan_number))

        return

    def do_load_nth_project(self):
        """
        Load the n-th saved project listed in the last tab
        :return:
        """
        # from the radio buttons to find the project that is selected to load
        if self.ui.radioButton_useLast1.isChecked():
            project_file_name = str(self.ui.label_last1Path.text())
        elif self.ui.radioButton_useLast2.isChecked():
            project_file_name = str(self.ui.label_last2Path.text())
        elif self.ui.radioButton_useLast3.isChecked():
            project_file_name = str(self.ui.label_last3Path.text())
        else:
            raise RuntimeError('None of the saved project is selected.')

        # load project
        self.load_project(project_file_name)

        return

    def do_mask_pt_2d(self):
        """ Mask a Pt and re-plot
        :return:
        """
        # get experiment, scan
        status, ret_obj = gutil.parse_integers_editors([self.ui.lineEdit_exp, self.ui.lineEdit_run,
                                                        self.ui.lineEdit_rawDataPtNo],
                                                       allow_blank=False)
        if status:
            exp, scan, pt = ret_obj
        else:
            self.pop_one_button_dialog(ret_obj)
            return

        # get the mask
        status, ret_obj = self._myControl.get_region_of_interest(exp, scan)
        if status is False:
            self.pop_one_button_dialog(ret_obj)
            return

        # create mask workspace
        status, error = self._myControl.generate_mask_workspace(exp, scan, ret_obj[0], ret_obj[1])
        if status is False:
            self.pop_one_button_dialog(error)
            return

        # re-load data file and mask
        self._myControl.load_spice_xml_file(exp, scan, pt)
        self._myControl.apply_mask(exp, scan, pt)

        # plot
        self._plot_raw_xml_2d(exp, scan, pt)

        return

    def do_merge_multi_scans(self):
        """
        Merge several scans to a single MDWorkspace and give suggestion for re-binning
        :return:
        """
        # find the selected scans
        selected_rows = self.ui.tableWidget_mergeScans.get_selected_rows(True)
        if len(selected_rows) < 2:
            self.pop_one_button_dialog('Merging multiple scans requires more than 1 scan to be selected.')
            return

        # find out the merged workspace is in Q or hkl
        convert_to_hkl = self.ui.radioButton_hkl.isChecked()

        # get the information from table workspace
        exp_number = int(str(self.ui.lineEdit_exp.text()))
        md_ws_list = list()
        peak_center_list = list()
        for i_row in selected_rows:
            # get scan number and md workspace number
            scan_number = self.ui.tableWidget_mergeScans.get_scan_number(i_row)
            md_ws_name = self.ui.tableWidget_mergeScans.get_merged_ws_name(i_row)
            if convert_to_hkl:
                status, ret_obj = self._myControl.get_pt_numbers(exp_number, scan_number)
                if not status:
                    raise RuntimeError('It is not possible to fail to get Pt number list at this stage.'
                                       'Error is due to %s.' % str(ret_obj))
                pt_list = ret_obj
                md_ws_name = hb3a_util.get_merged_hkl_md_name(self._instrument, exp_number, scan_number, pt_list)
            md_ws_list.append(md_ws_name)
            # get peak center in 3-tuple
            peak_center = self._myControl.get_peak_info(exp_number, scan_number).get_peak_centre()
            assert peak_center is not None, 'Exp/Scan/Pt %s does not exist in PeakInfo dictionary.'
            peak_center_list.append(peak_center)
        # END-FOR

        # ask name for the merged workspace
        merged_ws_name, status = gutil.get_value(self)

        # call the controller to merge the scans
        message = self._myControl.merge_multiple_scans(md_ws_list, peak_center_list, merged_ws_name)

        # information
        self.pop_one_button_dialog(message)

        return

    def do_merge_scans(self):
        """ Merge each selected scans in the tab-merge-scans
        :return:
        """
        # Get UB matrix and set to control
        ub_matrix = self.ui.tableWidget_ubInUse.get_matrix()
        self._myControl.set_ub_matrix(exp_number=None, ub_matrix=ub_matrix)

        # Warning
        self.pop_one_button_dialog('Merging scans can take long time. Please be patient!')

        # Process
        row_number_list = self.ui.tableWidget_mergeScans.get_selected_rows(True)
        exp_number = int(str(self.ui.lineEdit_exp.text()))

        sum_error_msg = ''

        for row_number in row_number_list:
            # get row number
            scan_number = self.ui.tableWidget_mergeScans.get_scan_number(row_number)

            # check SPICE file's existence. if not, then download it
            self._myControl.download_spice_file(exp_number, scan_number, over_write=False)

            status, pt_list = self._myControl.get_pt_numbers(exp_number, scan_number)
            if status is False:
                # skip this row due to error
                sum_error_msg += '%s\n' % str(pt_list)
                continue

            self.ui.tableWidget_mergeScans.set_status(row_number, 'In Processing')
            status, ret_tup = self._myControl.merge_pts_in_scan(exp_no=exp_number, scan_no=scan_number,
                                                                pt_num_list=[])
            # find peaks too
            status, ret_obj = self._myControl.find_peak(exp_number, scan_number)

            # process output
            if status:
                assert len(ret_tup) == 2
                merge_status = 'Merged'
                merged_name = ret_tup[0]
            else:
                merge_status = 'Failed. Reason: %s' % ret_tup
                merged_name = 'x'

            # update table
            self.ui.tableWidget_mergeScans.set_status(row_number, merge_status)
            self.ui.tableWidget_mergeScans.set_ws_name(row_number, merged_name)
            # if peak_centre is not None:
            #     self.ui.tableWidget_mergeScans.set_peak_centre(row_number, peak_centre)

            # Sleep for a while
            time.sleep(0.1)
        # END-FOR

        return

    def do_merge_scans_survey(self):
        """
        Merge each selected scans in the 'List Scans' tab to Q-sample space
        :return:
        """
        # get the selected scans
        scan_run_list = self.ui.tableWidget_surveyTable.get_selected_run_surveyed(required_size=None)
        print '[DB...BAT] returned scan/run list = ', scan_run_list
        if len(scan_run_list) == 0:
            self.pop_one_button_dialog('There is no run that is selected.')

        # start to add scan/run to table
        # Set table
        scan_list = list()
        for scan, pt in scan_run_list:
            scan_list.append(scan)
        scan_list.sort()
        self.ui.tableWidget_mergeScans.append_scans(scans=scan_list, allow_duplicate_scans=False)

        # switch tab
        self.ui.tabWidget.setCurrentIndex(MainWindow.TabPage['Scans Processing'])

        return

    def do_refine_ub_indexed_peaks(self):
        """
        Refine UB matrix by indexed peaks
        :return:
        """
        # refine UB matrix by indexed peak
        peak_info_list = self._build_peak_info_list(zero_hkl=False)

        # Refine UB matrix
        try:
            self._myControl.refine_ub_matrix_indexed_peaks(peak_info_list)
        except AssertionError as error:
            self.pop_one_button_dialog(str(error))
            return

        # show result
        self._show_refined_ub_result()

        return

    def do_refine_ub_cal_indexed_peaks(self):
        """
        refine UB matrix by indexed peaks with HKL calculated
        :return:
        """
        # refine UB matrix by indexed peak
        peak_info_list = self._build_peak_info_list(zero_hkl=False, is_spice=False)

        # Refine UB matrix
        try:
            self._myControl.refine_ub_matrix_indexed_peaks(peak_info_list)
        except AssertionError as error:
            self.pop_one_button_dialog(str(error))
            return

        # show result
        self._show_refined_ub_result()

        return

    def do_refine_ub_lattice(self):
        """
        Calculate UB matrix constrained by lattice parameters
        :return:
        """
        # launch the set up window
        if self._refineConfigWindow is None:
            self._refineConfigWindow = ol_window.OptimizeLatticeWindow(self)

        self._refineConfigWindow.set_prev_ub_refine_method(False)
        self._refineConfigWindow.show()

        return

    # add slot for UB refinement configuration window's signal to connect to
    @QtCore.pyqtSlot(int)
    def refine_ub_lattice(self, val):
        """
        Refine UB matrix by constraining on lattice type.
        Required inputs:
          1. unit cell type
          2. peak information include
        :param val:
        :return:
        """
        # check signal for hand shaking
        if val != 1000:
            raise RuntimeError('Signal value %s is not an authorized signal value (1000).' % str(val))

        # it is supposed to get the information back from the window
        unit_cell_type = self._refineConfigWindow.get_unit_cell_type()

        # get peak information list
        peak_info_list = self._build_peak_info_list(zero_hkl=False)

        # get the UB matrix value
        ub_src_tab = self._refineConfigWindow.get_ub_source()
        if ub_src_tab == 3:
            print '[INFO] UB matrix comes from tab "Calculate UB".'
            ub_matrix = self.ui.tableWidget_ubMatrix.get_matrix_str()
        elif ub_src_tab == 4:
            print '[INFO] UB matrix comes from tab "UB Matrix".'
            ub_matrix = self.ui.tableWidget_ubInUse.get_matrix_str()
        else:
            self.pop_one_button_dialog('UB source tab %s is not supported.' % str(ub_src_tab))
            return

        # refine UB matrix by constraint on lattice parameters
        status, error_message = self._myControl.refine_ub_matrix_by_lattice(peak_info_list, ub_matrix, unit_cell_type)
        if status:
            # successfully refine the lattice and UB matrix
            self._show_refined_ub_result()
        else:
            self.pop_one_button_dialog(error_message)

        return

    def do_refine_ub_fft(self):
        """
        Refine UB matrix by calling FFT method
        :return:
        """
        import refineubfftsetup

        dlg = refineubfftsetup.RefineUBFFTSetupDialog(self)
        if dlg.exec_():
            # Do stuff with values
            min_d, max_d, tolerance = dlg.get_values()
        else:
            # case for cancel
            return

        # launch the dialog to get min D and max D
        if (0 < min_d < max_d) is False:
            self.pop_one_button_dialog('Range of d is not correct! FYI, min D = %.5f, max D = %.5f.'
                                       '' % (min_d, max_d))
            return

        # get PeakInfo list and check
        peak_info_list = self._build_peak_info_list(zero_hkl=True)
        assert isinstance(peak_info_list, list), \
            'PeakInfo list must be a list but not %s.' % str(type(peak_info_list))
        assert len(peak_info_list) >= 3, \
            'PeakInfo must be larger or equal to 3 (.now given %d) to refine UB matrix' % len(peak_info_list)

        # friendly suggestion
        if len(peak_info_list) <= 9:
            self.pop_one_button_dialog('It is recommended to use at least 9 reflections'
                                       'to refine UB matrix without prior knowledge.')

        # refine
        try:
            self._myControl.refine_ub_matrix_least_info(peak_info_list, min_d, max_d, tolerance)
        except RuntimeError as runtime_error:
            self.pop_one_button_dialog(str(runtime_error))
            return

        # set value
        self._show_refined_ub_result()

        # set HKL to zero
        self.do_clear_all_peaks_index_ub()

        return

    def do_refresh_merged_scans_table(self):
        """ Find the merged
        :return:
        """
        # find out the merged runs
        scan_info_tup_list = self._myControl.get_merged_scans()

        # get existing scan numbers
        existing_scan_number_list = self.ui.tableWidget_mergeScans.get_selected_scans()

        # append the row to the merged scan table
        for scan_info_tup in scan_info_tup_list:
            scan_number = scan_info_tup[1]
            # skip if existing
            if scan_number in existing_scan_number_list:
                continue

            exp_number = scan_info_tup[0]
            pt_number_list = scan_info_tup[2]
            ws_name = hb3a_util.get_merged_md_name('HB3A', exp_number, scan_number, pt_number_list)
            self.ui.tableWidget_mergeScans.add_new_merged_data(exp_number, scan_number, ws_name)

        return

    def do_reset_ub_peaks_hkl(self):
        """
        Reset user specified HKL value to peak table
        :return:
        """
        # get experiment number
        status, ret_obj = gutil.parse_integers_editors([self.ui.lineEdit_exp])
        if not status:
            raise RuntimeError(ret_obj)
        else:
            exp_number = ret_obj[0]

        # reset all rows back to SPICE HKL
        num_rows = self.ui.tableWidget_peaksCalUB.rowCount()
        for i_row in xrange(num_rows):
            scan, pt = self.ui.tableWidget_peaksCalUB.get_scan_pt(i_row)
            if pt < 0:
                pt = None
            peak_info = self._myControl.get_peak_info(exp_number, scan, pt)
            h, k, l = peak_info.get_hkl(user_hkl=False)
            self.ui.tableWidget_peaksCalUB.update_hkl(i_row, h, k, l)
        # END-FOR

        # set the flag right
        self.ui.lineEdit_peaksIndexedBy.setText(IndexFromSpice)

        return

    def do_save_roi(self):
        """
        Save region of interest to a specific name and reflects in combo boxes for future use,
        especially used as a general ROI for multiple scans
        :return:
        """
        # get the experiment and scan value
        status, par_val_list = gutil.parse_integers_editors([self.ui.lineEdit_exp, self.ui.lineEdit_run])
        assert status
        exp_number = par_val_list[0]
        scan_number = par_val_list[1]

        # get the user specified name from ...
        roi_name, ok = QtGui.QInputDialog.getText(self, 'Input Mask Name', 'Enter mask name:')

        # return if cancelled
        if not ok:
            return

        # get current ROI
        status, roi = self._myControl.get_region_of_interest(exp_number=exp_number, scan_number=scan_number)
        assert status, str(roi)
        roi_name = str(roi_name)
        self._myControl.save_roi(roi_name, roi)

        # set it to combo-box
        self.ui.comboBox_maskNames1.addItem(roi_name)
        self.ui.comboBox_maskNames2.addItem(roi_name)

        return

    def do_save_survey(self):
        """
        Save the survey to a file
        :return:
        """
        # Get file name
        file_filter = 'CSV Files (*.csv);;All Files (*)'
        out_file_name = str(QtGui.QFileDialog.getSaveFileName(self, 'Save scan survey result',
                                                              self._homeDir, file_filter))

        # Save file
        self._myControl.save_scan_survey(out_file_name)

        return

    def do_save_ub(self):
        """ Save the in-use Matrix to an ASCII file
        :return:
        """
        # get file name
        file_filter = 'Data Files (*.dat);;All Files (*)'
        ub_file_name = str(QtGui.QFileDialog.getSaveFileName(self, 'ASCII File To Save UB Matrix', self._homeDir,
                                                             file_filter))

        # early return if user cancels selecting a file name to save
        if ub_file_name is None:
            return

        # get UB matrix
        in_use_ub = self.ui.tableWidget_ubInUse.get_matrix()
        ub_shape = in_use_ub.shape
        assert len(ub_shape) == 2 and ub_shape[0] == ub_shape[1] == 3

        # construct string
        ub_str = '# UB matrix\n# %s\n' % str(self.ui.label_ubInfoLabel.text())
        for i_row in xrange(3):
            for j_col in xrange(3):
                ub_str += '%.15f  ' % in_use_ub[i_row][j_col]
            ub_str += '\n'

        # write to file
        ub_file = open(ub_file_name, 'w')
        ub_file.write(ub_str)
        ub_file.close()

        return

    def do_select_all_peaks(self):
        """
        Purpose: select all peaks in table tableWidget_peaksCalUB
        :return:
        """
        if self.ui.radioButton_ubSelectAllScans.isChecked() and self._ubPeakTableFlag != 0:
            self.ui.tableWidget_peaksCalUB.select_all_rows(True)
            self._ubPeakTableFlag = 0
        elif self.ui.radioButton_ubSelectNoScan.isChecked() and self._ubPeakTableFlag != 1:
            self.ui.tableWidget_peaksCalUB.select_all_rows(False)
            self._ubPeakTableFlag = 1
        elif self.ui.radioButton_ubAdvancedSelection.isChecked() and self._ubPeakTableFlag != 2:
            # advanced
            import FindUBUtility
            self._selectUBScanDialog = FindUBUtility.SelectUBMatrixScansDialog(self)
            self._selectUBScanDialog.show()
            self._ubPeakTableFlag = 2
        # END-IF

        # if not self._ubPeakTableFlag:
        #     # turn to deselect all
        #     self.ui.tableWidget_peaksCalUB.select_all_rows(self._ubPeakTableFlag)
        # elif self.ui.checkBox_ubNuclearPeaks.isChecked() is False:
        #     # all peaks are subjected to select
        #     self.ui.tableWidget_peaksCalUB.select_all_rows(self._ubPeakTableFlag)
        # else:
        #     # only nuclear peaks to get selected
        #     self.ui.tableWidget_peaksCalUB.select_all_nuclear_peaks()
        # # END-IF-ELSE
        #
        # # revert the flag
        # self._ubPeakTableFlag = not self._ubPeakTableFlag

        return

    def do_select_all_survey(self):
        """
        Select or de-select all rows in survey items
        :return:
        """
        if self._surveyTableFlag:
            # flag is turned on: select all peaks or all nuclear peaks
            if self.ui.checkBox_surveySelectNuclearPeaks.isChecked():
                # only select nuclear peaks
                num_rows = self.ui.tableWidget_surveyTable.rowCount()
                for i_row in range(num_rows):
                    peak_hkl = self.ui.tableWidget_surveyTable.get_hkl(i_row)
                    if peak_util.is_peak_nuclear(peak_hkl[0], peak_hkl[1], peak_hkl[2]):
                        self.ui.tableWidget_surveyTable.select_row(i_row, True)
                    else:
                        self.ui.tableWidget_surveyTable.select_row(i_row, False)
            else:
                # all peaks
                self.ui.tableWidget_surveyTable.select_all_rows(True)
        else:
            # de-select all peaks
            self.ui.tableWidget_surveyTable.select_all_rows(False)
        # END-IF-ELSE

        # flip the flag for next select
        self._surveyTableFlag = not self._surveyTableFlag

        return

    def do_select_merged_scans(self):
        """ Select or deselect all rows in the merged scan table
        :return:
        """
        # get current status
        curr_state = str(self.ui.pushButton_selectAllScans2Merge.text()).startswith('Select')

        # select/deselect all
        self.ui.tableWidget_mergeScans.select_all_rows(curr_state)

        # set the text to the push button
        if curr_state:
            self.ui.pushButton_selectAllScans2Merge.setText('Deselect All')
        else:
            self.ui.pushButton_selectAllScans2Merge.setText('Select All')

        return

    def do_set_detector_size(self):
        """
        set the detector size to controller
        :return:
        """
        try:
            ret_obj = gutil.parse_integer_list(str(self.ui.lineEdit_detectorGeometry.text()), expected_size=2)
            size_x, size_y = ret_obj
            self._myControl.set_detector_geometry(size_x, size_y)
            if size_x != size_y or (size_x != 256 and size_x != 512):
                self.pop_one_button_dialog('Detector geometry should be either 256 x 256 or 512 x 512.')
        except RuntimeError as run_err:
            self.pop_one_button_dialog('Detector geometry is not correct! Re-set it!  FYI: {0}'.format(run_err))

        return

    def do_set_experiment(self):
        """ Set experiment
        :return:
        """
        status, ret_obj = gutil.parse_integers_editors([self.ui.lineEdit_exp])
        if status:
            # new experiment number
            exp_number = ret_obj[0]
            # current experiment to be replaced: warning
            curr_exp_number = self._myControl.get_experiment()
            if curr_exp_number is not None and exp_number != curr_exp_number:
                self.pop_one_button_dialog('Changing experiment to %d.  Clean previous experiment %d\'s result'
                                           ' in Mantid manually.' % (exp_number, curr_exp_number))
            # set the new experiment number
            self._myControl.set_exp_number(exp_number)
            self.ui.lineEdit_exp.setStyleSheet('color: black')
            self.setWindowTitle('Experiment %d' % exp_number)

            # try to set the default
            default_data_dir = '/HFIR/HB3A/exp%d/Datafiles' % exp_number
            if os.path.exists(default_data_dir):
                self.ui.lineEdit_localSpiceDir.setText(default_data_dir)

        else:
            err_msg = ret_obj
            self.pop_one_button_dialog('Unable to set experiment as %s' % err_msg)
            self.ui.lineEdit_exp.setStyleSheet('color: red')
            return

        self.ui.tabWidget.setCurrentIndex(0)

        # set the instrument geometry constants
        status, ret_obj = gutil.parse_float_editors([self.ui.lineEdit_defaultSampleDetDistance,
                                                     self.ui.lineEdit_pixelSizeX,
                                                     self.ui.lineEdit_pixelSizeY],
                                                    allow_blank=False)
        if status:
            default_det_sample_distance, pixel_x_size, pixel_y_size = ret_obj
            self._myControl.set_default_detector_sample_distance(default_det_sample_distance)
            self._myControl.set_default_pixel_size(pixel_x_size, pixel_y_size)
        else:
            self.pop_one_button_dialog('[ERROR] Unable to parse default instrument geometry constants '
                                       'due to %s.' % str(ret_obj))
            return

        # set the detector center
        det_center_str = str(self.ui.lineEdit_defaultDetCenter.text())
        try:
            terms = det_center_str.split(',')
            center_row = int(terms[0])
            center_col = int(terms[1])
            self._myControl.set_detector_center(exp_number, center_row, center_col, default=True)
        except (IndexError, ValueError) as error:
            self.pop_one_button_dialog('[ERROR] Unable to parse default detector center %s due to %s.'
                                       '' % (det_center_str, str(error)))

        return

    def do_set_ub_tab_hkl_to_integers(self):
        """
        Set all peaks' indexing (HKL) to integer in the table in "UB matrix calculation" tab.
        Change to these HKL values is only related to GUI, i.e., the table
        :return:
        """
        # get the current index source
        hkl_type_str = str(self.ui.comboBox_hklType.currentText())
        if hkl_type_str.lower().count('spice') > 0:
            # set spice HKL to integer
            is_spice = True
        else:
            is_spice = False

        # store the current value
        self.ui.tableWidget_peaksCalUB .store_current_indexing()

        # set the index to integer
        num_rows = self.ui.tableWidget_peaksCalUB.rowCount()
        for row_index in range(num_rows):
            try:
                m_h, m_l, m_k = self.ui.tableWidget_peaksCalUB.get_hkl(row_index, is_spice_hkl=is_spice)
                peak_indexing, round_error = hb3a_util.convert_hkl_to_integer(m_h, m_l, m_k, MAGNETIC_TOL)
                self.ui.tableWidget_peaksCalUB.set_hkl(row_index, peak_indexing, is_spice, round_error)
            except RuntimeError as run_err:
                scan_number, pt_number = self.ui.tableWidget_peaksCalUB.get_scan_pt(row_index)
                print '[ERROR] Unable to convert HKL to integer for scan {0} due to {1}.' \
                      ''.format(scan_number, run_err)
        # END-FOR

        # disable the set to integer button and enable the revert/undo button
        # self.ui.pushButton_setHKL2Int.setEnabled(False)
        # self.ui.pushButton_undoSetToInteger.setEnabled(True)

        return

    def do_toggle_table_integration(self):
        """
        change the type
        :return:
        """
        exp_number = int(self.ui.lineEdit_exp.text())

        integrate_type = self.ui.tableWidget_mergeScans.get_integration_type()
        if integrate_type == 'simple':
            integrate_type = 'mixed'
        elif integrate_type == 'mixed':
            integrate_type = 'gaussian'
        else:
            integrate_type = 'simple'

        for i_row in range(self.ui.tableWidget_mergeScans.rowCount()):
            scan_number = self.ui.tableWidget_mergeScans.get_scan_number(i_row)
            peak_info_obj = self._myControl.get_peak_info(exp_number, scan_number)
            try:
                intensity1, error1 = peak_info_obj.get_intensity(integrate_type, False)
                intensity2, error2 = peak_info_obj.get_intensity(integrate_type, True)
                self.ui.tableWidget_mergeScans.set_peak_intensity(i_row, intensity1, intensity2, error2, integrate_type)
            except RuntimeError as run_err:
                print '[ERROR] Unable to get peak intensity of scan {0} due to {1}.' \
                      ''.format(self.ui.tableWidget_mergeScans.get_scan_number(i_row), run_err)
        # END-FOR

        return

    def do_undo_ub_tab_hkl_to_integers(self):
        """
        After the peaks' indexing are set to integer, undo the action (i.e., revert to the original value)
        :return:
        """
        # get the column
        hkl_type = str(self.ui.comboBox_hklType.currentText())
        if hkl_type.lower().count('spice') > 0:
            is_spice = True
        else:
            is_spice = False

        # restore the value
        self.ui.tableWidget_peaksCalUB.restore_cached_indexing(is_spice)

        # enable and disable the buttons
        # self.ui.pushButton_setHKL2Int.setEnabled(True)
        # self.ui.pushButton_undoSetToInteger.setEnabled(False)

        return

    def do_index_merged_scans_peaks(self):
        """ Index all peaks' HKL value in the merged-peak tab by UB matrix that is just calculated
        :return:
        """
        # get the parameters
        exp_number = int(self.ui.lineEdit_exp.text())
        hkl_src = str(self.ui.comboBox_indexFrom.currentText())

        # loop through all rows
        num_rows = self.ui.tableWidget_mergeScans.rowCount()
        for row_index in range(num_rows):
            # get scan number
            scan_i = self.ui.tableWidget_mergeScans.get_scan_number(row_index)
            peak_info_i = self._myControl.get_peak_info(exp_number, scan_number=scan_i)

            # skip non-merged sans
            if peak_info_i is None:
                continue

            # get or calculate HKL
            if hkl_src == 'From SPICE':
                # get HKL from SPICE (non-user-hkl)
                hkl_i = peak_info_i.get_hkl(user_hkl=False)
            else:
                # calculate HKL from SPICE
                try:
                    ub_matrix = self._myControl.get_ub_matrix(exp_number)
                except KeyError as key_err:
                    print '[Error] unable to get UB matrix: %s' % str(key_err)
                    self.pop_one_button_dialog('Unable to get UB matrix.\nCheck whether UB matrix is set.')
                    return
                index_status, ret_tup = self._myControl.index_peak(ub_matrix, scan_i, allow_magnetic=True)
                if index_status:
                    hkl_i = ret_tup[0]
                else:
                    # unable to index peak. use fake hkl and set error message
                    hkl_i = [0, 0, 0]
                    error_msg = 'Scan %d: %s' % (scan_i, str(ret_tup))
                    self.ui.tableWidget_mergeScans.set_status(scan_i, error_msg)
                # END-IF-ELSE(index)
            # END-IF-ELSE (hkl_from_spice)

            # set & show
            peak_info_i.set_hkl_np_array(hkl_i)
            # self._myControl.get_peak_info(exp_number, scan_i)
            # round HKL?
            if self.ui.checkBox_roundHKL.isChecked():
                hkl_i = [hb3a_util.round_miller_index(hkl_i[0], 0.2),
                         hb3a_util.round_miller_index(hkl_i[1], 0.2),
                         hb3a_util.round_miller_index(hkl_i[2], 0.2)]

            self.ui.tableWidget_mergeScans.set_hkl(row_index, hkl_i, hkl_src)
        # END-FOR

        return

    def do_setup_dir_default(self):
        """
        Set up default directory for storing data and working
        If directory /HFIR/HB3A exists, it means that the user can access HFIR archive server
        :return:
        """
        home_dir = os.path.expanduser('~')

        # Data cache directory
        project_cache_dir = os.path.join(home_dir, 'Temp/HB3ATest')
        if os.path.exists('/HFIR/HB3A/'):
            self.ui.lineEdit_localSrcDir.setText('/HFIR/HB3A/')
        else:
            self.ui.lineEdit_localSpiceDir.setText(project_cache_dir)

        # working directory
        work_dir = os.path.join(project_cache_dir, 'Workspace')
        self.ui.lineEdit_workDir.setText(work_dir)

        return

    def set_ub_from_file(self):
        """ Get UB matrix from an Ascii file
        :return:
        """
        file_filter = 'Data Files (*.dat);;Text Files (*.txt);;All Files (*)'
        file_name = QtGui.QFileDialog.getOpenFileName(self, 'Open UB ASCII File', self._homeDir,
                                                      file_filter)
        # quit if cancelled
        if file_name is None:
            return

        # parse file
        ub_file = open(file_name, 'r')
        raw_lines = ub_file.readlines()
        ub_file.close()

        # convert to ub string
        ub_str = ''
        for line in raw_lines:
            line = line.strip()
            if len(line) == 0:
                # empty line
                continue
            elif line[0] == '#':
                # comment line
                continue
            else:
                # regular line
                ub_str += '%s ' % line

        # convert to matrix
        ub_matrix = gutil.convert_str_to_matrix(ub_str, (3, 3))

        return ub_matrix

    def do_set_user_detector_distance(self):
        """
        Set up the user-defined detector distance for loading instrument with data
        :return:
        """
        user_det_distance_str = str(self.ui.lineEdit_userDetSampleDistance.text()).strip()
        if len(user_det_distance_str) == 0:
            return

        # convert to float
        try:
            user_det_distance = float(user_det_distance_str)
        except ValueError:
            self.pop_one_button_dialog('User detector-sample distance %s must be a float.' % user_det_distance_str)
            return

        # check distance value because it cannot be too far
        default_det_distance = float(str(self.ui.lineEdit_defaultSampleDetDistance.text()))
        distance_tol = float(str(self.ui.lineEdit_sampleDetDistTol.text()))
        if abs((user_det_distance - default_det_distance) / default_det_distance) > distance_tol:
            self.pop_one_button_dialog('User specified sample-detector distance is not reasonable.')
            return

        # set to controller
        exp_number = int(str(self.ui.lineEdit_exp.text()))
        self._myControl.set_detector_sample_distance(exp_number, user_det_distance)

        # update the GUI for information
        self.ui.lineEdit_infoDetSampleDistance.setText('%.5f' % user_det_distance)

        return

    def do_set_user_wave_length(self):
        """

        :return:
        """
        try:
            exp_number = int(str(self.ui.lineEdit_exp.text()))
            user_lambda = float(str(self.ui.lineEdit_userWaveLength.text()))
        except ValueError:
            self.pop_one_button_dialog('Unable to set user wave length with value %s.'
                                       '' % str(self.ui.lineEdit_infoWavelength.text()))
            return

        self._myControl.set_user_wave_length(exp_number, user_lambda)

        # set back to GUI
        self.ui.lineEdit_infoWavelength.setText('%.5f' % user_lambda)

        return

    def do_set_user_detector_center(self):
        """
        set the user-defined detector center
        :return:
        """
        # get information
        status, ret_obj = gutil.parse_integers_editors([self.ui.lineEdit_exp,
                                                        self.ui.lineEdit_detCenterPixHorizontal,
                                                        self.ui.lineEdit_detCenterPixVertical],
                                                       allow_blank=True)

        if not status:
            self.pop_one_button_dialog(str(ret_obj))
            return

        assert isinstance(ret_obj, list) and len(ret_obj) == 3, 'Error!'
        exp_number, user_center_row, user_center_col = ret_obj
        assert isinstance(exp_number, int), 'Experiment number must be set up.'

        self._myControl.set_detector_center(exp_number, user_center_row, user_center_col)

        # apply to the GUI
        self.ui.lineEdit_infoDetCenter.setText('%d, %d' % (user_center_row, user_center_col))

        return

    def do_show_integration_details(self):
        """
        show the details (in table) about the integration of scans
        :return:
        """
        import PeaksIntegrationReport

        # check whether the integration information table
        if self._peakIntegrationInfoWindow is None:
            self._peakIntegrationInfoWindow = PeaksIntegrationReport.PeaksIntegrationReportDialog(self)

        # show
        self._peakIntegrationInfoWindow.show()

        # report
        report_dict = self.generate_peaks_integration_report()
        self._peakIntegrationInfoWindow.set_report(report_dict)

        return

    def do_show_spice_file(self):
        """
        Show SPICE file in a window
        :return:
        """
        # get the files from the GUI
        exp_number = int(str(self.ui.lineEdit_exp.text()))

        row_id_list = self.ui.tableWidget_surveyTable.get_selected_rows(True)
        scan_number_list = self.ui.tableWidget_surveyTable.get_scan_numbers(row_id_list)
        if len(scan_number_list) == 0:
            return

        # read the spice file into list of lines
        spice_line_list = self._myControl.read_spice_file(exp_number, scan_number_list[0])

        self._spiceViewer = viewspicedialog.ViewSpiceDialog(self)

        # Write each line
        wbuf = ''
        for line in spice_line_list:
            wbuf += line
        self._spiceViewer.write_text(wbuf)

        # show the new window
        self._spiceViewer.show()

        return

    def do_show_spice_file_raw(self):
        """
        show SPICE file in a window from Raw-Tab
        :return:
        """
        # get the files from the GUI
        exp_number = int(str(self.ui.lineEdit_exp.text()))

        # get the scan number
        try:
            scan_number = int(str(self.ui.lineEdit_run.text()))
        except ValueError as val_err:
            error_msg = 'Scan number {0} in raw-data-view-tab is invalid. FYI: {1}.' \
                        ''.format(self.ui.lineEdit_run.text(), val_err)
            self.pop_one_button_dialog(error_msg)
            return

        # get spice file
        spice_line_list = self._myControl.read_spice_file(exp_number, scan_number)

        # launch SPICE view
        if self._spiceViewer is None:
            # create SPICE viewer if it does not exist
            self._spiceViewer = viewspicedialog.ViewSpiceDialog(self)

        # form the buffer
        spice_buffer = ''
        for line in spice_line_list:
            spice_buffer += line

        # write out the value
        self._spiceViewer.write_text(spice_buffer)

        # show
        self._spiceViewer.show()

        return

    def do_show_ub_in_box(self):
        """ Get UB matrix in table tableWidget_ubMergeScan and write to plain text edit plainTextEdit_ubInput
        :return:
        """
        ub_matrix = self.ui.tableWidget_ubInUse.get_matrix()

        text = ''
        for i in xrange(3):
            for j in xrange(3):
                text += '%.7f, ' % ub_matrix[i][j]
            text += '\n'

        self.ui.plainTextEdit_ubInput.setPlainText(text)

        return

    def do_show_workspaces(self):
        """
        pop out a dialog to show the workspace names that are selected
        :return:
        """
        # get number of rows that are selected
        row_number_list = self.ui.tableWidget_mergeScans.get_selected_rows(True)

        message = ''
        for row_number in row_number_list:
            scan_number = self.ui.tableWidget_mergeScans.get_scan_number(row_number)
            md_qample_ws_name = self.ui.tableWidget_mergeScans.get_merged_ws_name(row_number)
            message += 'Scan %03d: %s\n' % (scan_number, md_qample_ws_name)
        # END-FOR

        gutil.show_message(message=message)

        return

    def do_survey(self):
        """
        Purpose: survey for the strongest reflections
        :return:
        """
        # Get experiment number
        exp_number = int(self.ui.lineEdit_exp.text())
        status, ret_obj = gutil.parse_integers_editors([self.ui.lineEdit_surveyStartPt,
                                                        self.ui.lineEdit_surveyEndPt])
        if status is False:
            err_msg = ret_obj
            self.pop_one_button_dialog(err_msg)
        start_scan = ret_obj[0]
        end_scan = ret_obj[1]

        max_number = int(self.ui.lineEdit_numSurveyOutput.text())

        # Get value
        status, ret_obj, err_msg = self._myControl.survey(exp_number, start_scan, end_scan)
        if status is False:
            self.pop_one_button_dialog(ret_obj)
            return
        elif err_msg != '':
            self.pop_one_button_dialog(err_msg)
        scan_sum_list = ret_obj
        self.ui.tableWidget_surveyTable.set_survey_result(scan_sum_list)
        self.ui.tableWidget_surveyTable.show_reflections(max_number)

        return

    def do_switch_tab_peak_int(self):
        """ Switch to tab 'Peak Integration' to set up and learn how to do peak integration
        :return:
        """
        # switch tab
        self.ui.tabWidget.setCurrentIndex(MainWindow.TabPage['Peak Integration'])

        # set up value
        selected_scans = self.ui.tableWidget_mergeScans.get_selected_scans()
        if len(selected_scans) > 0:
            # set the first one.  remember that the return is a list of tuple
            self.ui.lineEdit_scanIntegratePeak.setText(str(selected_scans[0][0]))

        return

    def do_sync_ub(self):
        """ Purpose: synchronize UB matrix in use with UB matrix calculated.
        Requirements: One of these must be given
        1. a valid UB matrix from tableWidget_ubMatrix
        2. an ascii file that contains 9 float
        3. from text edit
        :return:
        """
        # get the radio button that is checked
        if self.ui.radioButton_ubFromTab1.isChecked():
            # get ub matrix from tab 'Calculate UB Matrix'
            ub_matrix = self.ui.tableWidget_ubMatrix.get_matrix()

        # elif self.ui.radioButton_loadUBmatrix.isChecked():
        #     # load ub matrix from a file
        # ISSUE 001 VZ-FUTURE: Implement this next!
        #     raise NotImplementedError('This tab is not implemented, because the file format has not been decided.')

        elif self.ui.radioButton_ubFromList.isChecked():
            # load ub matrix from text editor
            ub_matrix = self.get_ub_from_text()

        else:
            raise RuntimeError('None radio button is selected for UB')

        # set to in-use UB matrix and control
        self.ui.tableWidget_ubInUse.set_from_matrix(ub_matrix)

        exp_no = int(str(self.ui.lineEdit_exp.text()))
        self._myControl.set_ub_matrix(exp_number=exp_no, ub_matrix=ub_matrix)

        return

    def do_test_url(self):
        """ Test whether the root URL provided specified is good
        """
        url = str(self.ui.lineEdit_url.text())

        url_is_good, err_msg = hb3a_util.check_url(url)
        if url_is_good is True:
            self.pop_one_button_dialog("URL %s is valid." % url)
            self.ui.lineEdit_url.setStyleSheet("color: green;")
        else:
            self.pop_one_button_dialog(err_msg)
            self.ui.lineEdit_url.setStyleSheet("color: read;")

        return url_is_good

    def do_view_data_set_3d(self):
        """
        Launch the sub window to view merged data in 3D.
        :return:
        """
        # get a list of rows that are selected
        row_index_list = self.ui.tableWidget_peaksCalUB.get_selected_rows(True)
        assert len(row_index_list) > 0, 'There is no row that is selected to view.'

        # get the information from the selected row
        status, exp_number = gutil.parse_integers_editors(self.ui.lineEdit_exp)
        assert status, 'Experiment number is not a valid integer.'

        # create window
        if self._my3DWindow is None:
            self._my3DWindow = plot3dwindow.Plot3DWindow(self)

        for i_row in row_index_list:
            exp_info = self.ui.tableWidget_peaksCalUB.get_exp_info(i_row)
            scan_number = exp_info[0]

            # prepare data
            ret_obj = self._prepare_view_merged(exp_number, scan_number)
            assert len(ret_obj) == 5
            md_file_name, weight_peak_centers, weight_peak_intensities, avg_peak_centre, avg_peak_intensity = ret_obj

            # add the 3D window
            self._my3DWindow.initialize_group('%s' % scan_number)
            self._my3DWindow.add_plot_by_file(md_file_name)
            self._my3DWindow.add_plot_by_array(weight_peak_centers, weight_peak_intensities)
            self._my3DWindow.add_plot_by_array(avg_peak_centre, avg_peak_intensity)
            self._my3DWindow.close_session()

        # END-FOR

        # Show
        self._my3DWindow.show()

        return

    def do_view_data_3d(self):
        """
        View merged scan data in 3D after FindPeaks.
        :return:
        """
        # get experiment and scan number
        scan_number = self.ui.tableWidget_peaksCalUB.get_selected_scans()
        status, ret_obj = gutil.parse_integers_editors([self.ui.lineEdit_exp,
                                                        self.ui.lineEdit_scanNumber])
        if status:
            exp_number = ret_obj[0]
            scan_number = ret_obj[1]
        else:
            self.pop_one_button_dialog(ret_obj)
            return

        # Check
        if self._myControl.has_merged_data(exp_number, scan_number) is False:
            self.pop_one_button_dialog('No merged MD workspace found for %d, %d' % (exp_number, scan_number))
            return

        # Generate data by writing out temp file
        ret_obj = self._prepare_view_merged(exp_number, scan_number)
        assert len(ret_obj) == 5
        md_file_name, weight_peak_centers, weight_peak_intensities, avg_peak_centre, avg_peak_intensity = ret_obj

        # Plot
        if self._my3DWindow is None:
            self._my3DWindow = plot3dwindow.Plot3DWindow(self)

        print '[INFO] Write file to %s' % md_file_name
        self._my3DWindow.add_plot_by_file(md_file_name)
        self._my3DWindow.add_plot_by_array(weight_peak_centers, weight_peak_intensities)
        self._my3DWindow.add_plot_by_array(avg_peak_centre, avg_peak_intensity)

        # Show
        self._my3DWindow.show()

        return

    def _prepare_view_merged(self, exp_number, scan_number):
        """
        Prepare the data to view 3D for merged scan
        :return:
        """
        # check
        assert isinstance(exp_number, int) and isinstance(scan_number, int)

        # get file name for 3D data
        base_file_name = 'md_%d.dat' % random.randint(1, 1001)
        md_file_name = self._myControl.export_md_data(exp_number, scan_number, base_file_name)
        peak_info = self._myControl.get_peak_info(exp_number, scan_number)

        # peak center
        weight_peak_centers, weight_peak_intensities = peak_info.get_weighted_peak_centres()
        qx, qy, qz = peak_info.get_peak_centre()

        # convert from list to ndarray
        num_pt_peaks = len(weight_peak_centers)
        assert num_pt_peaks == len(weight_peak_intensities)

        pt_peak_centre_array = numpy.ndarray(shape=(num_pt_peaks, 3), dtype='float')
        pt_peak_intensity_array = numpy.ndarray(shape=(num_pt_peaks,), dtype='float')
        for i_pt in xrange(num_pt_peaks):
            for j in xrange(3):
                pt_peak_centre_array[i_pt][j] = weight_peak_centers[i_pt][j]
            pt_peak_intensity_array[i_pt] = weight_peak_intensities[i_pt]

        avg_peak_centre = numpy.ndarray(shape=(1, 3), dtype='float')
        avg_peak_intensity = numpy.ndarray(shape=(1,), dtype='float')
        avg_peak_centre[0][0] = qx
        avg_peak_centre[0][1] = qy
        avg_peak_centre[0][2] = qz
        # integrated peak intensity
        avg_peak_intensity[0] = sum(pt_peak_intensity_array)

        return md_file_name, pt_peak_centre_array, pt_peak_intensity_array, avg_peak_centre, avg_peak_intensity

    def do_view_merged_scans_3d(self):
        """ Get selected merged scan and plot them individually in 3D
        :return:
        """
        # collect the selected rows and thus workspace names
        row_index_list = self.ui.tableWidget_mergeScans.get_selected_rows(True)
        exp_scan_list = list()
        for row_index in row_index_list:
            exp_number, scan_number = self.ui.tableWidget_mergeScans.get_exp_scan(row_index)
            pt_number_list = self._myControl.get_pt_numbers(exp_number, scan_number)
            md_data = self._myControl.get_merged_data(exp_number, scan_number, pt_number_list)
            exp_scan_list.append((scan_number, md_data))

        # initialize 3D plot
        if self._my3DWindow is None:
            self._my3DWindow = plot3dwindow.Plot3DWindow(self)
        self._my3DWindow.set_merged_data_set(exp_scan_list)
        self._my3DWindow.show()

        return

    def do_view_ub(self):
        """ View UB matrix in tab 'UB matrix'
        :return:
        """
        self.ui.tabWidget.setCurrentIndex(MainWindow.TabPage['UB Matrix'])

        return

    def do_view_survey_peak(self):
        """ View selected peaks from survey table
        Requirements: one and only 1 run is selected
        Guarantees: the scan number and pt number that are selected will be set to
            tab 'View Raw' and the tab is switched.
        :return:
        """
        # get values
        try:
            scan_num, pt_num = self.ui.tableWidget_surveyTable.get_selected_run_surveyed()
        except RuntimeError, err:
            self.pop_one_button_dialog(str(err))
            return

        # clear selection
        self.ui.tableWidget_surveyTable.select_all_rows(False)

        # switch tab
        self.ui.tabWidget.setCurrentIndex(MainWindow.TabPage['View Raw Data'])
        self.ui.lineEdit_run.setText(str(scan_num))
        self.ui.lineEdit_rawDataPtNo.setText(str(pt_num))

        return

    def evt_show_survey(self):
        """
        Show survey result
        :return:
        """
        if self.ui.tableWidget_surveyTable.rowCount() == 0:
            # do nothing if the table is empty
            return

        max_number = int(self.ui.lineEdit_numSurveyOutput.text())

        # ignore the situation that this line edit is cleared
        if max_number <= 0:
            return
        if max_number != self.ui.tableWidget_surveyTable.rowCount():
            # re-show survey
            self.ui.tableWidget_surveyTable.remove_all_rows()
            self.ui.tableWidget_surveyTable.show_reflections(max_number)

        return

    def generate_peaks_integration_report(self):
        """
        generate a report for all integrated peaks
        :return:
        """
        # get experiment number
        exp_number = int(self.ui.lineEdit_exp.text())

        # get all the selected peaks from table
        row_number_list = self.ui.tableWidget_mergeScans.get_selected_rows()

        # collection all the information
        report_dict = dict()
        print '[DB] Selected rows: {0}'.format(row_number_list)
        for row_number in row_number_list:
            scan_number = self.ui.tableWidget_mergeScans.get_scan_number(row_number)
            peak_info = self._myControl.get_peak_info(exp_number, scan_number)
            peak_integrate_dict = peak_info.generate_integration_report()
            report_dict[scan_number] = peak_integrate_dict
            print '[DB] Report Scan {0}. Keys: {1}'.format(scan_number, peak_integrate_dict.keys())
        # END-FOR

        return report_dict

    def get_ub_from_text(self):
        """ Purpose: Set UB matrix in use from plain text edit plainTextEdit_ubInput.
        Requirements:
          1. the string in the plain text edit must be able to be split to 9 floats by ',', ' ', '\t' and '\n'
        Guarantees: the matrix will be set up the UB matrix in use
        :return:
        """
        # get the string for ub matrix
        ub_str = str(self.ui.plainTextEdit_ubInput.toPlainText())

        # check the float list string
        status, ret_obj = gutil.parse_float_array(ub_str)
        # check whether the ub matrix in text editor is valid
        if status is False:
            # unable to parse to float arrays
            self.pop_one_button_dialog(ret_obj)
            return
        elif len(ret_obj) != 9:
            # number of floats is not 9
            self.pop_one_button_dialog('Requiring 9 floats for UB matrix.  Only %d are given.' % len(ret_obj))
            return

        # in good UB matrix format
        if self.ui.radioButton_ubMantidStyle.isChecked():
            # UB matrix in mantid style
            mantid_ub = gutil.convert_str_to_matrix(ub_str, (3, 3))

        elif self.ui.radioButton_ubSpiceStyle.isChecked():
            # UB matrix in SPICE style
            spice_ub = gutil.convert_str_to_matrix(ub_str, (3, 3))
            mantid_ub = r4c.convert_spice_ub_to_mantid(spice_ub)

        else:
            # not defined
            self.pop_one_button_dialog('Neither Mantid or SPICE-styled UB is checked!')
            return

        return mantid_ub

    def load_session(self, filename=None):
        """
        To load a session, i.e., read it back:
        :param filename:
        :return:
        """
        if filename is None:
            filename = 'session_backup.csv'
            filename = os.path.join(os.path.expanduser('~/.mantid/'), filename)

        in_file = open(filename, 'r')
        reader = csv.reader(in_file)
        my_dict = dict(x for x in reader)

        # set the data from saved file
        for key, value in my_dict.items():
            if key.startswith('lineEdit') is True:
                self.ui.__getattribute__(key).setText(value)
            elif key.startswith('plainText') is True:
                self.ui.__getattribute__(key).setPlainText(value)
            elif key.startswith('comboBox') is True:
                self.ui.__getattribute__(key).setCurrentIndex(int(value))
            else:
                self.pop_one_button_dialog('Error! Widget name %s is not supported' % key)
        # END-FOR

        # set the experiment
        self._myControl.set_local_data_dir(str(self.ui.lineEdit_localSpiceDir.text()))
        self._myControl.set_working_directory(str(self.ui.lineEdit_workDir.text()))
        self._myControl.set_server_url(str(self.ui.lineEdit_url.text()))

        return

    # def ui_apply_lorentz_correction_mt(self):
    #     """
    #     Apply Lorentz corrections to the integrated peak intensities of all the selected peaks
    #     at the UI level
    #     :return:
    #     """
    #     # get experiment number
    #     exp_number = int(self.ui.lineEdit_exp.text())
    #
    #     # select rows
    #     selected_rows = self.ui.tableWidget_mergeScans.get_selected_rows(True)
    #
    #     # apply for each row selected for Lorentz correction
    #     error_message = ''
    #     for row_number in selected_rows:
    #         # get scan number
    #         scan_number = self.ui.tableWidget_mergeScans.get_scan_number(row_number)
    #         # get peak information object
    #         peak_info_obj = self._myControl.get_peak_info(exp_number, scan_number)
    #         if peak_info_obj is None:
    #             error_message += 'Unable to get peak information from scan %d\n' % scan_number
    #             continue
    #         # get intensity
    #         peak_intensity = peak_info_obj.get_intensity(simple_sum=True, lorentz_corrected=True)
    #         # self.ui.tableWidget_mergeScans.set_status(row_number, str(run_err))
    #
    #         # # get Q-vector of the peak center and calculate |Q| from it
    #         # peak_center_q = peak_info_obj.get_peak_centre_v3d().norm()
    #         # # get wave length
    #         wavelength = self._myControl.get_wave_length(exp_number, [scan_number])
    #         self.ui.tableWidget_mergeScans.set_wave_length(row_number, wavelength)
    #         # # get motor step (choose from omega, phi and chi)
    #         try:
    #             motor_move_tup = self._myControl.get_motor_step(exp_number, scan_number)
    #         except RuntimeError as run_err:
    #             self.ui.tableWidget_mergeScans.set_status(row_number, str(run_err))
    #             continue
    #         except AssertionError as ass_err:
    #             self.ui.tableWidget_mergeScans.set_status(row_number, str(ass_err))
    #             continue
    #         # set motor information (the moving motor)
    #         self.ui.tableWidget_mergeScans.set_motor_info(row_number, motor_move_tup)
    #         motor_step = motor_move_tup[1]
    #         # # apply the Lorentz correction to the intensity
    #         # # corrected = self._myControl.apply_lorentz_correction(peak_intensity, q, wavelength, motor_step)
    #
    #         # FIXME - Later need to
    #         self.ui.tableWidget_mergeScans.set_peak_intensity(row_number, peak_intensity, lorentz_corrected=True,
    #                                                           standard_error=
    #                                                           integrate_method='sum')
    #         self._myControl.set_peak_intensity(exp_number, scan_number, corrected)
    #     # END-FOR (row_number)
    #
    #     if len(error_message) > 0:
    #         self.pop_one_button_dialog(error_message)

        return

    def pop_one_button_dialog(self, message):
        """ Pop up a one-button dialog
        :param message:
        :return:
        """
        assert isinstance(message, str), 'Input message %s must a string but not %s.' \
                                         '' % (str(message), type(message))
        QtGui.QMessageBox.information(self, '4-circle Data Reduction', message)

        return

    def report_peak_addition(self, exp_number, error_message):
        """

        :param self:
        :param exp_number:
        :param error_message:
        :return:
        """
        self.pop_one_button_dialog('Exp: %d\n%s' % (exp_number, error_message))

        return

    def save_current_session(self, filename=None):
        """ Save current session/value setup to
        :return:
        """
        # Set up dictionary
        save_dict = dict()

        # Setup
        save_dict['lineEdit_localSpiceDir'] = str(self.ui.lineEdit_localSpiceDir.text())
        save_dict['lineEdit_url'] = str(self.ui.lineEdit_url.text())
        save_dict['lineEdit_workDir'] = str(self.ui.lineEdit_workDir.text())

        # Experiment
        save_dict['lineEdit_exp'] = str(self.ui.lineEdit_exp.text())

        # Lattice
        save_dict['lineEdit_a'] = str(self.ui.lineEdit_a.text())
        save_dict['lineEdit_b'] = str(self.ui.lineEdit_b.text())
        save_dict['lineEdit_c'] = str(self.ui.lineEdit_c.text())
        save_dict['lineEdit_alpha'] = str(self.ui.lineEdit_alpha.text())
        save_dict['lineEdit_beta'] = str(self.ui.lineEdit_beta.text())
        save_dict['lineEdit_gamma'] = str(self.ui.lineEdit_gamma.text())

        # Merge scan
        save_dict['lineEdit_listScansSliceView'] = str(self.ui.lineEdit_listScansSliceView.text())

        # Save to csv file
        if filename is None:
            # default
            save_dir = os.path.expanduser('~/.mantid/')
            if os.path.exists(save_dir) is False:
                os.mkdir(save_dir)
            filename = os.path.join(save_dir, 'session_backup.csv')
        # END-IF

        ofile = open(filename, 'w')
        writer = csv.writer(ofile)
        for key, value in save_dict.items():
            writer.writerow([key, value])
        ofile.close()

        return

    def menu_quit(self):
        """

        :return:
        """
        self.save_settings()
        self.close()

    def show_scan_pt_list(self):
        """ Show the range of Pt. in a scan
        :return:
        """
        # Get parameters
        status, inp_list = gutil.parse_integers_editors([self.ui.lineEdit_exp, self.ui.lineEdit_run])
        if status is False:
            self.pop_one_button_dialog(inp_list)
            return
        else:
            exp_no = inp_list[0]
            scan_no = inp_list[1]

        status, ret_obj = self._myControl.get_pt_numbers(exp_no, scan_no)

        # Form message
        if status is False:
            # Failed to get Pt. list
            error_message = ret_obj
            self.pop_one_button_dialog(error_message)
        else:
            # Form message
            pt_list = sorted(ret_obj)
            num_pts = len(pt_list)
            info = 'Exp %d Scan %d has %d Pt. ranging from %d to %d.\n' % (exp_no, scan_no, num_pts,
                                                                           pt_list[0], pt_list[-1])
            num_miss_pt = pt_list[-1] - pt_list[0] + 1 - num_pts
            if num_miss_pt > 0:
                info += 'There are %d Pt. skipped.\n' % num_miss_pt

            self.pop_one_button_dialog(info)

        return

    def set_ub_peak_table(self, peak_info):
        """
        Set up the table of peaks to calculate UB matrix
        Requirements: peak_info is a valid PeakInfo instance
        :param peak_info:
        :return:
        """
        # Check requirements
        assert isinstance(peak_info, r4c.PeakProcessRecord)

        # Get data
        exp_number, scan_number = peak_info.get_experiment_info()
        h, k, l = peak_info.get_hkl(user_hkl=False)
        q_x, q_y, q_z = peak_info.get_peak_centre()
        m1 = self._myControl.get_sample_log_value(exp_number, scan_number, 1, '_m1')
        wave_length = hb3a_util.convert_to_wave_length(m1_position=m1)

        # Set to table
        status, err_msg = self.ui.tableWidget_peaksCalUB.add_peak(scan_number, (h, k, l), (q_x, q_y, q_z), m1,
                                                                  wave_length)
        if status is False:
            self.pop_one_button_dialog(err_msg)

        return

    def save_settings(self):
        """
        Save settings (parameter set) upon quiting
        :return:
        """
        settings = QtCore.QSettings()

        # directories
        local_spice_dir = str(self.ui.lineEdit_localSpiceDir.text())
        settings.setValue("local_spice_dir", local_spice_dir)
        work_dir = str(self.ui.lineEdit_workDir.text())
        settings.setValue('work_dir', work_dir)

        # experiment number
        exp_num = str(self.ui.lineEdit_exp.text())
        settings.setValue('exp_number', exp_num)

        # lattice parameters
        lattice_a = str(self.ui.lineEdit_a.text())
        settings.setValue('a', lattice_a)
        lattice_b = str(self.ui.lineEdit_b.text())
        settings.setValue('b', lattice_b)
        lattice_c = str(self.ui.lineEdit_c.text())
        settings.setValue('c', lattice_c)
        lattice_alpha = str(self.ui.lineEdit_alpha.text())
        settings.setValue('alpha', lattice_alpha)
        lattice_beta = str(self.ui.lineEdit_beta.text())
        settings.setValue('beta', lattice_beta)
        lattice_gamma = str(self.ui.lineEdit_gamma.text())
        settings.setValue('gamma', lattice_gamma)

        # last project
        last_1_project_path = str(self.ui.label_last1Path.text())
        settings.setValue('last1path', last_1_project_path)

        return

    def load_settings(self):
        """
        Load QSettings from previous saved file
        :return:
        """
        settings = QtCore.QSettings()

        # directories
        try:
            spice_dir = settings.value('local_spice_dir', '')
            self.ui.lineEdit_localSpiceDir.setText(str(spice_dir))
            work_dir = settings.value('work_dir')
            self.ui.lineEdit_workDir.setText(str(work_dir))

            # experiment number
            exp_num = settings.value('exp_number')
            self.ui.lineEdit_exp.setText(str(exp_num))

            # lattice parameters
            lattice_a = settings.value('a')
            self.ui.lineEdit_a.setText(str(lattice_a))
            lattice_b = settings.value('b')
            self.ui.lineEdit_b.setText(str(lattice_b))
            lattice_c = settings.value('c')
            self.ui.lineEdit_c.setText(str(lattice_c))
            lattice_alpha = settings.value('alpha')
            self.ui.lineEdit_alpha.setText(str(lattice_alpha))
            lattice_beta = settings.value('beta')
            self.ui.lineEdit_beta.setText(str(lattice_beta))
            lattice_gamma = settings.value('gamma')
            self.ui.lineEdit_gamma.setText(str(lattice_gamma))

            # last project
            last_1_project_path = str(settings.value('last1path'))
            self.ui.label_last1Path.setText(last_1_project_path)

        except TypeError as err:
            self.pop_one_button_dialog(str(err))
            return

        return

    def _get_lattice_parameters(self):
        """
        Get lattice parameters from GUI
        :return: (Boolean, Object).  True, 6-tuple as a, b, c, alpha, beta, gamm
                                     False: error message
        """
        status, ret_list = gutil.parse_float_editors([self.ui.lineEdit_a,
                                                      self.ui.lineEdit_b,
                                                      self.ui.lineEdit_c,
                                                      self.ui.lineEdit_alpha,
                                                      self.ui.lineEdit_beta,
                                                      self.ui.lineEdit_gamma])
        if status is False:
            err_msg = ret_list
            err_msg = 'Unable to parse unit cell due to %s' % err_msg
            return False, err_msg

        a, b, c, alpha, beta, gamma = ret_list

        return True, (a, b, c, alpha, beta, gamma)

    def _plot_raw_xml_2d(self, exp_no, scan_no, pt_no):
        """ Plot raw workspace from XML file for a measurement/pt.
        """
        # Check and load SPICE table file
        does_exist = self._myControl.does_spice_loaded(exp_no, scan_no)
        if does_exist is False:
            # Download data
            status, error_message = self._myControl.download_spice_file(exp_no, scan_no, over_write=False)
            if status is True:
                status, error_message = self._myControl.load_spice_scan_file(exp_no, scan_no)
                if status is False and self._allowDownload is False:
                    self.pop_one_button_dialog(error_message)
                    return
            else:
                self.pop_one_button_dialog(error_message)
                return
        # END-IF(does_exist)

        # Load Data for Pt's xml file
        does_exist = self._myControl.does_raw_loaded(exp_no, scan_no, pt_no)

        if does_exist is False:
            # Check whether needs to download
            status, error_message = self._myControl.download_spice_xml_file(scan_no, pt_no, exp_no=exp_no)
            if status is False:
                self.pop_one_button_dialog(error_message)
                return
            # Load SPICE xml file
            status, error_message = self._myControl.load_spice_xml_file(exp_no, scan_no, pt_no)
            if status is False:
                self.pop_one_button_dialog(error_message)
                return

        # Convert a list of vector to 2D numpy array for imshow()
        # Get data and plot
        raw_det_data = self._myControl.get_raw_detector_counts(exp_no, scan_no, pt_no)
        # raw_det_data = numpy.rot90(raw_det_data, 1)
        self.ui.graphicsView_detector2dPlot.clear_canvas()
        # get the configuration of detector from GUI
        ret_obj = gutil.parse_integer_list(str(self.ui.lineEdit_detectorGeometry.text()), expected_size=2)
        x_max, y_max = ret_obj
        self.ui.graphicsView_detector2dPlot.add_plot_2d(raw_det_data, x_min=0, x_max=x_max, y_min=0, y_max=y_max,
                                                        hold_prev_image=False)
        status, roi = self._myControl.get_region_of_interest(exp_no, scan_number=None)
        if status:
            self.ui.graphicsView_detector2dPlot.add_roi(roi[0], roi[1])
        else:
            error_msg = roi
            # self.pop_one_button_dialog(error_msg)
            print '[Error] %s' % error_msg
        # END-IF

        # Information
        info = '%-10s: %d\n%-10s: %d\n%-10s: %d\n' % ('Exp', exp_no,
                                                      'Scan', scan_no,
                                                      'Pt', pt_no)
        self.ui.plainTextEdit_rawDataInformation.setPlainText(info)

        return

    def update_adding_peaks_status(self, exp_number, scan_number, progress):
        """
        Update the status for adding peak to UB matrix calculating
        :param exp_number:
        :param scan_number:
        :param progress:
        :return:
        """
        # show message to bar
        if scan_number < 0:
            message = 'Peak processing finished'
        else:
            message = 'Processing experiment %d scan %d starting from %s.' % (exp_number, scan_number,
                                                                              str(datetime.datetime.now()))
        self.ui.statusbar.showMessage(message)

        # update progress bar
        self.ui.progressBar_add_ub_peaks.setValue(progress)

        return

    def update_merge_value(self, exp_number, scan_number, sig_value, peak_centre, mode):
        """
        update the values of result from merging/integrating peaks
        :param exp_number:
        :param scan_number:
        :param sig_value:
        :param peak_centre:
        :param mode:
        :return:
        """
        print '[DB...BAT] Update merged value: ', exp_number, scan_number, sig_value, peak_centre, mode

        # Process signals according to mode
        if mode == 0:
            # start of processing one peak
            progress = int(sig_value - 0.5)
            if progress == 0:
                # run start
                self._startMeringScans = time.clock()
                self._errorMessageEnsemble = ''

            self.ui.progressBar_mergeScans.setValue(progress)

        elif mode == 1:
            # receive signal from the end of processing one peak: complete the row
            # get the peak object
            peak_info_obj = self._myControl.get_peak_info(exp_number, scan_number)

            # get row number to set up the table
            try:
                row_number = self.ui.tableWidget_mergeScans.get_row_by_scan(scan_number)
            except RuntimeError as run_err:
                raise RuntimeError('Unable to find scan {0} in Peak-Processing table due to {1}.'
                                   ''.format(scan_number, run_err))

            # get peak: simple summation intensity
            intensity, int_std_dev = peak_info_obj.get_intensity('simple intensity', False)

            # check intensity value
            is_error = False
            if intensity < 0:
                # set to status
                error_msg = 'Negative intensity (simple): %.3f' % intensity
                self.ui.tableWidget_mergeScans.set_status(row_number=row_number, status=error_msg)
                # reset intensity to 0.
                intensity = 0.
                is_error = True
                int_std_dev = 0.

            # get the corrected value
            corrected_intensity = intensity * peak_info_obj.lorentz_correction_factor
            corrected_std_dev = int_std_dev * peak_info_obj.lorentz_correction_factor

            # status, error_msg = self._myControl.set_peak_intensity(exp_number, scan_number, intensity)
            # if status:
            #     # set the value to table
            self.ui.tableWidget_mergeScans.set_peak_intensity(row_number=row_number,
                                                              peak_intensity=intensity,
                                                              corrected_intensity=corrected_intensity,
                                                              standard_error=corrected_std_dev,
                                                              integrate_method='simple')

            if is_error:
                self.ui.tableWidget_mergeScans.set_status(row_number, 'Integration Error')
            else:
                self.ui.tableWidget_mergeScans.set_status(row_number, 'Integrated')

        elif mode == 2:
            # get signal from the end of all selected scans being integrated

            # apply Lorentz correction
            # self.ui_apply_lorentz_correction_mt()

            # set progress bar
            progress = int(sig_value+0.5)
            self.ui.progressBar_mergeScans.setValue(progress)

            # set message to status bar
            merge_run_end = time.clock()
            elapsed = merge_run_end - self._startMeringScans
            message = 'Peak integration is over. Used %.2f seconds' % elapsed
            self.ui.statusbar.showMessage(message)

            # pop error message if there is any
            if len(self._errorMessageEnsemble) > 0:
                self.pop_one_button_dialog(self._errorMessageEnsemble)

            # delete thread
            del self._myIntegratePeaksThread
            self._myIntegratePeaksThread = None

        # END-IF-ELSE (mode)

        return

    def update_merge_message(self, exp_number, scan_number, mode, message):
        """
        Update the merge-scan table for message such as error or etc.
        Note: the string passed from PyQt message is of type unicode but not string!
        :param exp_number:
        :param scan_number:
        :param mode:
        :param message:
        :return:
        """
        # check
        assert isinstance(exp_number, int), 'Experiment number must be integer.'
        assert isinstance(scan_number, int), 'Scan number must be integer.'
        assert isinstance(mode, int), 'Mode %s must be integer but not %s.' \
                                      '' % (str(mode), type(mode))
        assert isinstance(message, str) or isinstance(message, unicode),\
            'Message %s must be a string/unicode but not %s.' % (str(message), type(message))

        # passed value from PyQt signal might be a unicode code
        message = str(message)

        try:
            row_number = self.ui.tableWidget_mergeScans.get_row_by_scan(scan_number)
        except RuntimeError as run_err:
            self.pop_one_button_dialog(str(run_err))
            return

        # set intensity, state to table
        if mode == 0:
            # error message
            self.ui.tableWidget_mergeScans.set_peak_intensity(row_number, peak_intensity=0., corrected_intensity=0.,
                                                              standard_error=0., integrate_method='simple')
            self.ui.tableWidget_mergeScans.set_status(row_number=row_number, status=message)

            # set peak value
            status, ret_message = self._myControl.set_zero_peak_intensity(exp_number, scan_number)
            if not status:
                self.pop_one_button_dialog(ret_message)

        elif mode == 1:
            # merged workspace name
            merged_ws_name = message
            self.ui.tableWidget_mergeScans.set_ws_name(row_number=row_number, merged_md_name=merged_ws_name)

        else:
            raise RuntimeError('Peak-merging mode %d is not supported.' % mode)

        return

    def update_peak_added_info(self, int_msg, int_msg2):
        """
        Update the peak-being-added information
        :param int_msg:
        :param int_msg2:
        :return:
        """
        # get parameters passed
        exp_number = int_msg
        scan_number = int_msg2

        # get PeakInfo
        peak_info = self._myControl.get_peak_info(exp_number, scan_number)
        assert isinstance(peak_info, r4c.PeakProcessRecord)

        # add to table
        self.set_ub_peak_table(peak_info)

        return

    @property
    def ub_matrix_processing_table(self):
        """
        return the handler to the UB matrix
        :return:
        """
        return self.ui.tableWidget_peaksCalUB

    @property
    def working_directory(self):
        """
        return the current working directory
        :return:
        """
        return self._myControl._workDir
