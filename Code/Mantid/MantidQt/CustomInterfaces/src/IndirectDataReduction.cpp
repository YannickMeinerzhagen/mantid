//----------------------
// Includes
//----------------------
#include "MantidQtCustomInterfaces/IndirectDataReduction.h"
#include "MantidQtCustomInterfaces/Indirect.h" // user interface for Indirect instruments
#include "MantidQtAPI/ManageUserDirectories.h"

#include "MantidKernel/ConfigService.h"
#include "MantidAPI/AlgorithmManager.h"
#include "MantidAPI/AnalysisDataService.h"
#include "MantidAPI/ExperimentInfo.h"

#include <QMessageBox>
#include <QDir>

#include <QDesktopServices>
#include <QUrl>

//Add this class to the list of specialised dialogs in this namespace
namespace MantidQt
{
  namespace CustomInterfaces
  {
    DECLARE_SUBWINDOW(IndirectDataReduction);
  }
}

using namespace MantidQt::CustomInterfaces;
//----------------------
// Public member functions
//----------------------

/**
 * Default constructor for class. Initialises interface pointers to NULL values.
 * @param parent :: This is a pointer to the "parent" object in Qt, most likely the main MantidPlot window.
 */
IndirectDataReduction::IndirectDataReduction(QWidget *parent) :
  UserSubWindow(parent), m_indirectInstruments(NULL), 
  m_curInterfaceSetup(""), m_settingsGroup("CustomInterfaces/IndirectDataReduction"),
  m_algRunner(new MantidQt::API::AlgorithmRunner(this))
{
  //Signals to report load instrument algo progress
  connect(m_algRunner, SIGNAL(algorithmComplete(bool)), this, SLOT(instrumentLoadingDone(bool)));
  connect(m_algRunner, SIGNAL(algorithmProgress(double, const std::string &)), this, SLOT(instrumentLoadProgress(double, const std::string &)));
}

/**
 * Destructor
 */
IndirectDataReduction::~IndirectDataReduction()
{
  //Make sure no algos are sunning after the window has been closed
  m_algRunner->cancelRunningAlgorithm();

  saveSettings();
}

/**
 * On user clicking the "help" button on the interface, directs their request to the relevant
 * interface's helpClicked() function.
 */
void IndirectDataReduction::helpClicked()
{
  m_indirectInstruments->helpClicked();
}

/**
 * This is the function called when the "Run" button is clicked. It will call the relevent function
 * in the subclass.
 */
void IndirectDataReduction::runClicked()
{
  m_indirectInstruments->runClicked();
}

/**
 * Sets up Qt UI file and connects signals, slots. 
 */
void IndirectDataReduction::initLayout()
{
  m_uiForm.setupUi(this);
  m_curInterfaceSetup = "";

  // Assume we get a incompatiable instrument to start with
  m_uiForm.pbRun->setEnabled(false);

  // Signal / Slot Connections Set Up Here

  // signal/slot connections to respond to changes in instrument selection combo boxes
  connect(m_uiForm.cbInst, SIGNAL(instrumentSelectionChanged(const QString&)), this, SLOT(userSelectInstrument(const QString&)));

  // connect "?" (Help) Button
  connect(m_uiForm.pbHelp, SIGNAL(clicked()), this, SLOT(helpClicked()));
  // connect the "Run" button
  connect(m_uiForm.pbRun, SIGNAL(clicked()), this, SLOT(runClicked()));
  // connect the "Manage User Directories" Button
  connect(m_uiForm.pbManageDirectories, SIGNAL(clicked()), this, SLOT(openDirectoryDialog()));
}

/**
 * This function is ran after initLayout(), and runPythonCode is unavailable before this function
 * has run (because of the setup of the base class). For this reason, "setup" functions that require
 * Python scripts are located here.
 */
void IndirectDataReduction::initLocalPython()
{
  // select starting instrument
  readSettings();

  if ( m_curInterfaceSetup == "" )
  {
    userSelectInstrument(m_uiForm.cbInst->currentText());
  }
}

/**
 * Read settings from the persistent store
 */
void IndirectDataReduction::readSettings()
{
  QSettings settings;
  settings.beginGroup(m_settingsGroup);
  QString instrName = settings.value("instrument-name", "").toString();
  settings.endGroup();

  setDefaultInstrument(instrName);
}

/**
 * Save settings to a persistent storage
 */
void IndirectDataReduction::saveSettings()
{
  QSettings settings;
  settings.beginGroup(m_settingsGroup);
  QString instrName;

  instrName = m_uiForm.cbInst->currentText();

  settings.setValue("instrument-name", instrName);
  settings.endGroup();
}

/**
 * Sets up the initial instrument for the interface. This value is taken from the users'
 * settings in the menu View -> Preferences -> Mantid -> Instrument
 * @param name :: The name of the default instrument
 */
void IndirectDataReduction::setDefaultInstrument(const QString & name)
{
  if( name.isEmpty() ) return;

  int index = m_uiForm.cbInst->findText(name);
  if( index >= 0 )
  {
    m_uiForm.cbInst->setCurrentIndex(index);
  }
}

/**
 * This function: 1. loads the instrument and gets the value of deltaE-mode parameter
 *				 2. Based on this value, makes the necessary changes to the form setup (direct or indirect).
 * @param name :: name of the instrument from the QComboBox
 */
void IndirectDataReduction::instrumentSelectChanged(const QString& name)
{
  m_uiForm.instLoadProgressLabel->setVisible(true);

  QString defFile = (Mantid::API::ExperimentInfo::getInstrumentFilename(name.toStdString())).c_str();
  if((defFile == "") || !m_uiForm.cbInst->isVisible())
  {
    m_uiForm.instLoadProgressLabel->setText(QString("Instument loading failed!"));
    m_uiForm.cbInst->setEnabled(true);
    m_uiForm.pbRun->setEnabled(true);
    return;
  }

  QString outWS = "__empty_" + m_uiForm.cbInst->currentText();

  m_curInterfaceSetup = name;

  //Load the empty instrument into the workspace __empty_[name]
  //This used to be done in Python
  Mantid::API::Algorithm_sptr instLoader = Mantid::API::AlgorithmManager::Instance().createUnmanaged("LoadEmptyInstrument", -1);
  instLoader->initialize();
  instLoader->setProperty("Filename", defFile.toStdString());
  instLoader->setProperty("OutputWorkspace", outWS.toStdString());

  //Ensure no other algorithm is running
  m_algRunner->cancelRunningAlgorithm();
  m_algRunner->startAlgorithm(instLoader);
}

/**
 * Tasks to be carried out after an empty instument has finished loading
 */
void IndirectDataReduction::instrumentLoadingDone(bool error)
{
  QString curInstPrefix = m_uiForm.cbInst->itemData(m_uiForm.cbInst->currentIndex()).toString();
  if((curInstPrefix == "") || error)
  {
    m_uiForm.instLoadProgressLabel->setText(QString("Instument loading failed!"));
    m_uiForm.cbInst->setEnabled(true);
    m_uiForm.pbRun->setEnabled(true);
    return;
  }

  if(!m_indirectInstruments)
  {
    m_indirectInstruments = new Indirect(qobject_cast<QWidget*>(this->parent()), m_uiForm);
    m_indirectInstruments->initLayout();
    connect(m_indirectInstruments, SIGNAL(runAsPythonScript(const QString&, bool)),
        this, SIGNAL(runAsPythonScript(const QString&, bool)));
    m_indirectInstruments->initializeLocalPython();
  }
  m_indirectInstruments->performInstSpecific();
  m_indirectInstruments->setIDFValues(curInstPrefix);

  m_uiForm.pbRun->setEnabled(true);
  m_uiForm.cbInst->setEnabled(true);

  m_uiForm.instLoadProgressLabel->setVisible(false);
}

/**
 * Task carried out when the instrument load algorithm reports it's progress
 *
 * \param p Progress between 0 and 1
 *
 * \param msg String message
 */
void IndirectDataReduction::instrumentLoadProgress(double p, const std::string &msg)
{
  UNUSED_ARG(msg)

  QString percentage;
  percentage.setNum((int) (p * 100));
  QString progressMessage = "Loading: " + percentage + " %";
  m_uiForm.instLoadProgressLabel->setText(progressMessage);
}

/**
 * If the instrument selection has changed, calls instrumentSelectChanged
 * @param prefix :: instrument name from QComboBox object
 */
void IndirectDataReduction::userSelectInstrument(const QString& prefix) 
{
  if ( prefix != m_curInterfaceSetup )
  {
    // Remove the old empty instrument workspace if it is there
    std::string ws_name = "__empty_" + m_curInterfaceSetup.toStdString();
    Mantid::API::AnalysisDataServiceImpl& dataStore = Mantid::API::AnalysisDataService::Instance();
    if( dataStore.doesExist(ws_name) )
    {
      dataStore.remove(ws_name);
    }

    m_uiForm.pbRun->setEnabled(false);
    m_uiForm.cbInst->setEnabled(false);
    instrumentSelectChanged(prefix);
  }
}

void IndirectDataReduction::openDirectoryDialog()
{
  MantidQt::API::ManageUserDirectories *ad = new MantidQt::API::ManageUserDirectories(this);
  ad->show();
  ad->setFocus();
}
