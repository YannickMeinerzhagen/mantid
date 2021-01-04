// Mantid Repository : https://github.com/mantidproject/mantid
//
// Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
//   NScD Oak Ridge National Laboratory, European Spallation Source,
//   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
// SPDX - License - Identifier: GPL - 3.0 +

#include "MantidCrystal/SCDCalibratePanels2.h"
#include "MantidAPI/Algorithm.h"
#include "MantidAPI/AnalysisDataService.h"
#include "MantidAPI/ConstraintFactory.h"
#include "MantidAPI/ExperimentInfo.h"
#include "MantidAPI/FileProperty.h"
#include "MantidAPI/FunctionFactory.h"
#include "MantidAPI/Sample.h"
#include "MantidAPI/WorkspaceFactory.h"
#include "MantidCrystal/SCDCalibratePanels2ObjFunc.h"
#include "MantidDataObjects/PeaksWorkspace.h"
#include "MantidDataObjects/Workspace2D.h"
#include "MantidGeometry/Crystal/OrientedLattice.h"
#include "MantidKernel/BoundedValidator.h"
#include "MantidKernel/Logger.h"
#include <boost/container/flat_set.hpp>
#include <boost/property_tree/ptree.hpp>
#include <boost/property_tree/xml_parser.hpp>

namespace Mantid {
namespace Crystal {

  using namespace Mantid::API;
  using namespace Mantid::DataObjects;
  using namespace Mantid::Geometry;
  using namespace Mantid::Kernel;

  /// Config logger
  namespace {
  Logger logger("SCDCalibratePanels2");
  }

  DECLARE_ALGORITHM(SCDCalibratePanels2)

  /**
   * @brief Initialization
   * 
   */
  void SCDCalibratePanels2::init() {
    // Input peakworkspace
    declareProperty(
      std::make_unique<WorkspaceProperty<PeaksWorkspace>>(
        "PeakWorkspace", 
        "",
        Kernel::Direction::Input),
      "Workspace of Indexed Peaks");

    // Lattice constant group
    auto mustBePositive = std::make_shared<BoundedValidator<double>>();
    mustBePositive->setLower(0.0);
    declareProperty("a", EMPTY_DBL(), mustBePositive,
                    "Lattice Parameter a (Leave empty to use lattice constants "
                    "in peaks workspace)");
    declareProperty("b", EMPTY_DBL(), mustBePositive,
                    "Lattice Parameter b (Leave empty to use lattice constants "
                    "in peaks workspace)");
    declareProperty("c", EMPTY_DBL(), mustBePositive,
                    "Lattice Parameter c (Leave empty to use lattice constants "
                    "in peaks workspace)");
    declareProperty("alpha", EMPTY_DBL(), mustBePositive,
                    "Lattice Parameter alpha in degrees (Leave empty to use "
                    "lattice constants in peaks workspace)");
    declareProperty("beta", EMPTY_DBL(), mustBePositive,
                    "Lattice Parameter beta in degrees (Leave empty to use "
                    "lattice constants in peaks workspace)");
    declareProperty("gamma", EMPTY_DBL(), mustBePositive,
                    "Lattice Parameter gamma in degrees (Leave empty to use "
                    "lattice constants in peaks workspace)");
    const std::string LATTICE("Lattice Constants");
    setPropertyGroup("a", LATTICE);
    setPropertyGroup("b", LATTICE);
    setPropertyGroup("c", LATTICE);
    setPropertyGroup("alpha", LATTICE);
    setPropertyGroup("beta", LATTICE);
    setPropertyGroup("gamma", LATTICE);

    // Calibration options group
    declareProperty("CalibrateT0", false, "Calibrate the T0 (initial TOF)");
    declareProperty("CalibrateL1", true, "Change the L1(source to sample) distance");
    declareProperty("CalibrateBanks", true, "Calibrate position and orientation of each bank.");
    // TODO:
    //     Once the core functionality of calibration is done, we can consider adding the
    //     following control calibration parameters.
    // declareProperty("EdgePixels", 0, "Remove peaks that are at pixels this close to edge. ");
    // declareProperty("ChangePanelSize", true, 
    //                 "Change the height and width of the "
    //                 "detectors.  Implemented only for "
    //                 "RectangularDetectors.");
    // declareProperty("CalibrateSNAPPanels", false,
    //                 "Calibrate the 3 X 3 panels of the "
    //                 "sides of SNAP.");
    const std::string PARAMETERS("Calibration Parameters");
    setPropertyGroup("CalibrateT0" ,PARAMETERS);
    setPropertyGroup("CalibrateL1" ,PARAMETERS);
    setPropertyGroup("CalibrateBanks" ,PARAMETERS);

    // Output options group
    const std::vector<std::string> detcalExts{".DetCal", ".Det_Cal"};
    declareProperty(
        std::make_unique<FileProperty>("DetCalFilename", "SCDCalibrate2.DetCal",
                                        FileProperty::OptionalSave, detcalExts),
        "Path to an ISAW-style .detcal file to save.");

    declareProperty(
        std::make_unique<FileProperty>("XmlFilename", "SCDCalibrate2.xml",
                                        FileProperty::OptionalSave, ".xml"),
        "Path to an Mantid .xml description(for LoadParameterFile) file to "
        "save.");
    // NOTE: we need to make some significant changes to the output interface considering
    //       50% of the time is spent on writing to file for the version 1.
    // Tentative options: all calibration output should be stored as a group workspace
    //                    for interactive analysis
    //  - peak positions comparison between theoretical and measured
    //  - TOF comparision between theoretical and measured
    const std::string OUTPUT("Output");
    setPropertyGroup("DetCalFilename", OUTPUT);
    setPropertyGroup("XmlFilename", OUTPUT);
  }

  /**
   * @brief validate inputs
   * 
   * @return std::map<std::string, std::string> 
   */
  std::map<std::string, std::string>
  SCDCalibratePanels2::validateInputs() {
      std::map<std::string, std::string> issues;

      return issues;
  }

  /**
   * @brief execute calibration
   * 
   */
  void SCDCalibratePanels2::exec() {
    // parse all inputs
    PeaksWorkspace_sptr m_pws = getProperty("PeakWorkspace");

    parseLatticeConstant(m_pws);

    bool calibrateT0 = getProperty("CalibrateT0");
    bool calibrateL1 = getProperty("CalibrateL1");
    bool calibrateBanks = getProperty("CalibrateBanks");

    const std::string DetCalFilename = getProperty("DetCalFilename");
    const std::string XmlFilename = getProperty("XmlFilename");

    // STEP_0: sort the peaks
    // NOTE: why??
    std::vector<std::pair<std::string, bool>> criteria{{"BankName", true}};
    m_pws->sort(criteria);

    // STEP_1: preparation
    // get names of banks that can be calibrated
    getBankNames(m_pws);

    // STEP_2: optimize T0,L1,L2,etc.
    if (calibrateT0)
      optimizeT0(m_pws);
    if (calibrateL1)
      optimizeL1(m_pws);
    if (calibrateBanks)
      optimizeBanks(m_pws);

    // STEP_3: Write to disk if required
    Instrument_sptr instCalibrated =
        std::const_pointer_cast<Geometry::Instrument>(m_pws->getInstrument());

    if (!XmlFilename.empty())
      saveXmlFile(XmlFilename, m_BankNames, instCalibrated);

    if (!DetCalFilename.empty())
        saveIsawDetCal(DetCalFilename, m_BankNames, instCalibrated, m_T0);

    // STEP_4: Cleanup
  }

  /// ------------------------------------------- ///
  /// Core functions for Calibration&Optimizatoin ///
  /// ------------------------------------------- ///

  /**
   * @brief 
   * 
   * @param pws 
   */
  void SCDCalibratePanels2::optimizeT0(std::shared_ptr<PeaksWorkspace> pws){

  }

  /**
   * @brief 
   * 
   * @param pws 
   */
  void SCDCalibratePanels2::optimizeL1(std::shared_ptr<PeaksWorkspace> pws) {
    // cache starting L1 position
    double original_L1 = -pws->getInstrument()->getSource()->getPos().Z();
    int npks = pws->getNumberPeaks();
    MatrixWorkspace_sptr l1ws = std::dynamic_pointer_cast<MatrixWorkspace>(
        WorkspaceFactory::Instance().create(
            "Workspace2D", // use workspace 2D to mock a histogram
            1,             // one vector
            3 * npks,      // X :: anything is fine
            3 * npks));    // Y :: flattened Q vector

    auto &measured = l1ws->getSpectrum(0);
    auto &xv = measured.mutableX();
    auto &yv = measured.mutableY();
    auto &ev = measured.mutableE();

    for (int i = 0; i < npks; ++i) {
      const Peak &pk = pws->getPeak(i);
      V3D qv = pk.getQSampleFrame();
      for (int j = 0; j < 3; ++j) {
        xv[i * 3 + j] = i * 3 + j;
        yv[i * 3 + j] = qv[j];
        ev[i * 3 + j] = 1;
      }
    }

    // fit algorithm for the optimization of L1
    IAlgorithm_sptr fitL1_alg = createChildAlgorithm("Fit", -1, -1, false);
    //-- obj func def
    std::ostringstream fun_str;
    fun_str << "name=SCDCalibratePanels2ObjFunc,Workspace=" << pws->getName()
            << ",ComponentName=moderator";
    //-- bounds&constraints def
    std::ostringstream tie_str;
    tie_str << "dx=0.0,dy=0.0,drotx=0.0,droty=0.0,drotz=0.0,dT0=" << m_T0;
    //-- set and go
    fitL1_alg->setPropertyValue("Function", fun_str.str());
    fitL1_alg->setProperty("Ties", tie_str.str());
    fitL1_alg->setProperty("InputWorkspace", l1ws);
    fitL1_alg->setProperty("CreateOutput", true);
    fitL1_alg->setProperty("Output", "fit");
    fitL1_alg->executeAsChildAlg();
    //-- parse output
    std::string status = fitL1_alg->getProperty("OutputStatus");
    double chi2OverDOF = fitL1_alg->getProperty("OutputChi2overDoF");
    ITableWorkspace_sptr rst = fitL1_alg->getProperty("OutputParameters");
    double dL1_optimized = rst->getRef<double>("Value", 2);
    adjustComponent(0, 0, dL1_optimized, 0, 0, 0,
                    pws->getInstrument()->getSource()->getName(), pws);

    //-- log
    g_log.notice() << "-- Fit L1 rst:\n"
                   << "    dL1: " << dL1_optimized << " \n"
                   << "    L1 " << original_L1 << " -> "
                   << -pws->getInstrument()->getSource()->getPos().Z() << " \n"
                   << "    chi2/DOF = " << chi2OverDOF << "\n";
  }

  /**
   * @brief Calibrate the position and rotation of each Bank, one at a time
   *
   * @param pws
   */
  void SCDCalibratePanels2::optimizeBanks(std::shared_ptr<PeaksWorkspace> pws) {

    PARALLEL_FOR_IF(Kernel::threadSafe(*pws))
    for (int i = 0; i < static_cast<int>(m_BankNames.size()); ++i) {
      PARALLEL_START_INTERUPT_REGION
      // prepare local copies to work with
      const std::string bankname = *std::next(m_BankNames.begin(), i);

      //-- step 0: extract peaks that lies on the current bank
      // NOTE: We are cloning the whole pws, then subtracting
      //       those that are not on the current bank.
      PeaksWorkspace_sptr pwsBanki = pws->clone();
      const std::string pwsBankiName = "_pws_" + bankname;
      AnalysisDataService::Instance().addOrReplace(pwsBankiName, pwsBanki);
      std::vector<Peak> &allPeaks = pwsBanki->getPeaks();
      auto notMyPeaks = std::remove_if(
          allPeaks.begin(), allPeaks.end(),
          [&bankname](const Peak &pk) { return pk.getBankName() != bankname; });
      allPeaks.erase(notMyPeaks, allPeaks.end());

      // Do not attempt correct panels with less than 6 peaks as the system will
      // be under-determined
      int nBankPeaks = pwsBanki->getNumberPeaks();
      if (nBankPeaks < MINIMUM_PEAKS_PER_BANK) {
        g_log.notice() << "-- Bank " << bankname << " have only " << nBankPeaks
                       << " (<" << MINIMUM_PEAKS_PER_BANK
                       << ") Peaks, skipping\n";
        continue;
      }

      //-- step 1: prepare a mocked workspace with QSample as its yValues
      MatrixWorkspace_sptr wsBankCali =
          std::dynamic_pointer_cast<MatrixWorkspace>(
              WorkspaceFactory::Instance().create(
                  "Workspace2D",    // use workspace 2D to mock a histogram
                  1,                // one vector
                  3 * nBankPeaks,   // X :: anything is fine
                  3 * nBankPeaks)); // Y :: flattened Q vector
      auto &measured = wsBankCali->getSpectrum(0);
      auto &xv = measured.mutableX();
      auto &yv = measured.mutableY();
      auto &ev = measured.mutableE();
      // TODO: non-uniform weighting (ev) will be implemented at a later date
      for (int i = 0; i < nBankPeaks; ++i) {
        const Peak &pk = pwsBanki->getPeak(i);
        V3D qv = pk.getQSampleFrame();
        for (int j = 0; j < 3; ++j) {
          xv[i * 3 + j] = i * 3 + j;
          yv[i * 3 + j] = qv[j];
          ev[i * 3 + j] = 1;
        }
      }
      //-- step 2&3: invoke fit to find both traslation and rotation
      IAlgorithm_sptr fitBank_alg = createChildAlgorithm("Fit", -1, -1, false);
      //---- setup obj fun def
      std::ostringstream fun_str;
      fun_str << "name=SCDCalibratePanels2ObjFunc,Workspace=" << pwsBankiName
              << ",ComponentName=" << bankname;
      //---- bounds&constraints def
      std::ostringstream tie_str;
      tie_str << "dT0=" << m_T0;
      std::ostringstream constraint_str;
      constraint_str << "-5 < drotx < 5, -5 < droty < 5, -5 < drotz < 5";
      //---- set&go
      fitBank_alg->setPropertyValue("Function", fun_str.str());
      fitBank_alg->setProperty("Ties", tie_str.str());
      fitBank_alg->setProperty("Constraints", constraint_str.str());
      fitBank_alg->setProperty("InputWorkspace", wsBankCali);
      fitBank_alg->setProperty("CreateOutput", true);
      fitBank_alg->setProperty("Output", "fit");
      fitBank_alg->executeAsChildAlg();
      //---- cache results
      double chi2OverDOF = fitBank_alg->getProperty("OutputChi2overDoF");
      ITableWorkspace_sptr rstFitBank =
          fitBank_alg->getProperty("OutputParameters");
      double dx = rstFitBank->getRef<double>("Value", 0);
      double dy = rstFitBank->getRef<double>("Value", 1);
      double dz = rstFitBank->getRef<double>("Value", 2);
      double drotx = rstFitBank->getRef<double>("Value", 3);
      double droty = rstFitBank->getRef<double>("Value", 4);
      double drotz = rstFitBank->getRef<double>("Value", 5);

      // //-- step 2: invoke Fit to find the translation
      // IAlgorithm_sptr fitBankTrans_alg =
      //     createChildAlgorithm("Fit", -1, -1, false);
      // //---- setup obj fun def
      // std::ostringstream fun_str;
      // fun_str << "name=SCDCalibratePanels2ObjFunc,Workspace=" << pwsBankiName
      //         << ",ComponentName=" << bankname;
      // //---- bounds&constraints def
      // std::ostringstream tie_str;
      // tie_str << "drotx=0.0,droty=0.0,drotz=0.0,dT0=" << m_T0;
      // //---- set&go
      // fitBankTrans_alg->setPropertyValue("Function", fun_str.str());
      // fitBankTrans_alg->setProperty("Ties", tie_str.str());
      // fitBankTrans_alg->setProperty("InputWorkspace", wsBankCali);
      // fitBankTrans_alg->setProperty("CreateOutput", true);
      // fitBankTrans_alg->setProperty("Output", "fit");
      // fitBankTrans_alg->executeAsChildAlg();
      // //---- cache results
      // double chi2OverDOFTrans =
      //     fitBankTrans_alg->getProperty("OutputChi2overDoF");
      // ITableWorkspace_sptr rstFitBankTrans =
      //     fitBankTrans_alg->getProperty("OutputParameters");
      // double dx = rstFitBankTrans->getRef<double>("Value", 0);
      // double dy = rstFitBankTrans->getRef<double>("Value", 1);
      // double dz = rstFitBankTrans->getRef<double>("Value", 2);
      // adjustComponent(dx, dy, dz, 0.0, 0.0, 0.0, bankname, pwsBanki);

      // //-- step 3: invoki Fit to find the rotation
      // IAlgorithm_sptr fitBankRot_alg =
      //     createChildAlgorithm("Fit", -1, -1, false);
      // //---- reuse the fun def since it should be the same
      // //---- bounds&constraints def
      // std::ostringstream tie2_str;
      // tie_str << "dx=0.0,dy=0.0,dz=0.0,dT0=" << m_T0;
      // // tie2_str << "dx=" << dx << ",dy=" << dy << ",dz=" << dz
      // //          << ",dT0=" << m_T0;
      // //----set&go
      // fitBankRot_alg->setPropertyValue("Function", fun_str.str());
      // fitBankRot_alg->setProperty("Ties", tie2_str.str());
      // fitBankRot_alg->setProperty("InputWorkspace", wsBankCali);
      // fitBankRot_alg->setProperty("CreateOutput", true);
      // fitBankRot_alg->setProperty("Output", "fit");
      // fitBankRot_alg->executeAsChildAlg();
      // double chi2OverDOFRot =
      // fitBankRot_alg->getProperty("OutputChi2overDoF"); ITableWorkspace_sptr
      // rstFitBankRot =
      //     fitBankRot_alg->getProperty("OutputParameters");
      // double drotx = rstFitBankRot->getRef<double>("Value", 3);
      // double droty = rstFitBankRot->getRef<double>("Value", 4);
      // double drotz = rstFitBankRot->getRef<double>("Value", 5);

      //-- step 4: update the instrument with optimization results
      adjustComponent(dx, dy, dz, drotx, droty, drotz, bankname, pws);

      //-- step 5: logging
      g_log.notice() << "-- Fit " << bankname << " results:\n"
                     << "    d(x,y,z) = (" << dx << "," << dy << "," << dz
                     << ")\n"
                     << "    drot(x,y,z) = (" << drotx << "," << droty << ","
                     << drotz << ")\n"
                     << "    chi2/DOF = " << chi2OverDOF << "\n";
      // g_log.notice() << "-- Fit " << bankname << " results:\n"
      //           << "    d(x,y,z) = (" << dx << "," << dy << "," << dz
      //           << ") with chi2/DOF=" << chi2OverDOFTrans   << "\n"
      //           << "    drot(x,y,z) = (" << drotx << "," << droty << ","
      //           << drotz << ") with chi2/DOF=" << chi2OverDOFRot << "\n";

      // -- cleanup
      AnalysisDataService::Instance().remove(pwsBankiName);

      PARALLEL_END_INTERUPT_REGION
    }
    PARALLEL_CHECK_INTERUPT_REGION
  }

  /// ---------------- ///
  /// helper functions ///
  /// ---------------- ///

  /**
   * @brief get lattice constants from either inputs or the
   *        input peak workspace
   *
   */
  void SCDCalibratePanels2::parseLatticeConstant(std::shared_ptr<PeaksWorkspace> pws) {
    m_a = getProperty("a");
    m_b = getProperty("b");
    m_c = getProperty("c");
    m_alpha = getProperty("alpha");
    m_beta = getProperty("beta");
    m_gamma = getProperty("gamma");
    // if any one of the six lattice constants is missing, try to get
    // one from the workspace
    if((m_a == EMPTY_DBL() ||
        m_b == EMPTY_DBL() ||
        m_c == EMPTY_DBL() ||
        m_alpha == EMPTY_DBL() ||
        m_beta == EMPTY_DBL() ||
        m_gamma == EMPTY_DBL()) &&
        (pws->sample().hasOrientedLattice())) {
        OrientedLattice lattice = pws->mutableSample().getOrientedLattice();
        m_a = lattice.a();
        m_b = lattice.b();
        m_c = lattice.c();
        m_alpha = lattice.alpha();
        m_beta = lattice.beta();
        m_gamma = lattice.gamma();
    }
  }

  /**
   * @brief Gather names for bank for calibration
   * 
   * @param pws 
   */
  void SCDCalibratePanels2::getBankNames(std::shared_ptr<PeaksWorkspace> pws) {
    int npeaks = static_cast<int>(pws->getNumberPeaks());
    for (int i=0; i<npeaks; ++i){
      std::string bname = pws->getPeak(i).getBankName();
      if (bname != "None")
        m_BankNames.insert(bname);
    }
  }

  void SCDCalibratePanels2::adjustComponent(double dx, double dy, double dz,
                                            double drotx, double droty,
                                            double drotz, std::string cmptName,
                                            PeaksWorkspace_sptr &pws) {
    // translation
    IAlgorithm_sptr mv_alg = Mantid::API::AlgorithmFactory::Instance().create(
        "MoveInstrumentComponent", -1);
    mv_alg->initialize();
    mv_alg->setChild(true);
    mv_alg->setLogging(LOGCHILDALG);
    mv_alg->setProperty<Workspace_sptr>("Workspace", pws);
    mv_alg->setProperty("ComponentName", cmptName);
    mv_alg->setProperty("X", dx);
    mv_alg->setProperty("Y", dy);
    mv_alg->setProperty("Z", dz);
    mv_alg->setProperty("RelativePosition", true);
    mv_alg->executeAsChildAlg();

    // orientation
    IAlgorithm_sptr rot_alg = Mantid::API::AlgorithmFactory::Instance().create(
        "RotateInstrumentComponent", -1);
    //-- rotAngX@(1,0,0)
    rot_alg->initialize();
    rot_alg->setChild(true);
    rot_alg->setLogging(LOGCHILDALG);
    rot_alg->setProperty<Workspace_sptr>("Workspace", pws);
    rot_alg->setProperty("ComponentName", cmptName);
    rot_alg->setProperty("X", 1.0);
    rot_alg->setProperty("Y", 0.0);
    rot_alg->setProperty("Z", 0.0);
    rot_alg->setProperty("Angle", drotx);
    rot_alg->setProperty("RelativeRotation", true);
    rot_alg->executeAsChildAlg();
    //-- rotAngY@(0,1,0)
    rot_alg->initialize();
    rot_alg->setChild(true);
    rot_alg->setLogging(LOGCHILDALG);
    rot_alg->setProperty<Workspace_sptr>("Workspace", pws);
    rot_alg->setProperty("ComponentName", cmptName);
    rot_alg->setProperty("X", 0.0);
    rot_alg->setProperty("Y", 1.0);
    rot_alg->setProperty("Z", 0.0);
    rot_alg->setProperty("Angle", droty);
    rot_alg->setProperty("RelativeRotation", true);
    rot_alg->executeAsChildAlg();
    //-- rotAngZ@(0,0,1)
    rot_alg->initialize();
    rot_alg->setChild(true);
    rot_alg->setLogging(LOGCHILDALG);
    rot_alg->setProperty<Workspace_sptr>("Workspace", pws);
    rot_alg->setProperty("ComponentName", cmptName);
    rot_alg->setProperty("X", 0.0);
    rot_alg->setProperty("Y", 0.0);
    rot_alg->setProperty("Z", 1.0);
    rot_alg->setProperty("Angle", drotz);
    rot_alg->setProperty("RelativeRotation", true);
    rot_alg->executeAsChildAlg();
  }

  /**
   * Saves the new instrument to an xml file that can be used with the
   * LoadParameterFile Algorithm. If the filename is empty, nothing gets
   * done.
   *
   * @param FileName     The filename to save this information to
   *
   * @param AllBankNames The names of the banks in each group whose values
   * are to be saved to the file
   *
   * @param instrument   The instrument with the new values for the banks
   * in Groups
   *
   * TODO:
   *  - Need to find a way to add the information regarding calibrated T0
   */
  void SCDCalibratePanels2::saveXmlFile(
    const std::string &FileName,
    boost::container::flat_set<std::string> &AllBankNames,
    std::shared_ptr<Instrument> &instrument) {
    g_log.notice() << "Generating xml tree"
                   << "\n";

    using boost::property_tree::ptree;
    ptree root;
    ptree parafile;

    // configure root node
    parafile.put("<xmlattr>.instrument", instrument->getName());
    parafile.put("<xmlattr>.valid-from",
                 instrument->getValidFromDate().toISO8601String());

    // cnofigure and add each bank
    for (auto bankName : AllBankNames) {
      // Prepare data for node
      if (instrument->getName().compare("CORELLI") == 0)
        bankName.append("/sixteenpack");
      std::shared_ptr<const IComponent> bank =
          instrument->getComponentByName(bankName);
      Quat relRot = bank->getRelativeRot();
      std::vector<double> relRotAngles = relRot.getEulerAngles("XYZ");
      V3D pos1 = bank->getRelativePos();
      // TODO: no handling of scaling for now, will add back later
      double scalex = 1.0;
      double scaley = 1.0;

      // prepare node
      ptree bank_root;
      ptree bank_dx, bank_dy, bank_dz;
      ptree bank_dx_val, bank_dy_val, bank_dz_val;
      ptree bank_drotx, bank_droty, bank_drotz;
      ptree bank_drotx_val, bank_droty_val, bank_drotz_val;
      ptree bank_sx, bank_sy;
      ptree bank_sx_val, bank_sy_val;

      // add data to node
      bank_dx_val.put("<xmlattr>.val", pos1.X());
      bank_dy_val.put("<xmlattr>.val", pos1.Y());
      bank_dz_val.put("<xmlattr>.val", pos1.Z());
      bank_dx.put("<xmlattr>.name", "x");
      bank_dy.put("<xmlattr>.name", "y");
      bank_dz.put("<xmlattr>.name", "z");

      bank_drotx_val.put("<xmlattr>.val", relRot[0]);
      bank_droty_val.put("<xmlattr>.val", relRot[1]);
      bank_drotz_val.put("<xmlattr>.val", relRot[2]);
      bank_drotx.put("<xmlattr>.name", "rotx");
      bank_droty.put("<xmlattr>.name", "roty");
      bank_drotz.put("<xmlattr>.name", "rotz");

      bank_sx_val.put("<xmlattr>.val", scalex);
      bank_sy_val.put("<xmlattr>.val", scaley);
      bank_sx.put("<xmlattr>.name", "scalex");
      bank_sy.put("<xmlattr>.name", "scaley");

      bank_root.put("<xmlattr>.name", bankName);

      // configure structure
      bank_dx.add_child("value", bank_dx_val);
      bank_dy.add_child("value", bank_dy_val);
      bank_dz.add_child("value", bank_dz_val);

      bank_drotx.add_child("value", bank_drotx_val);
      bank_droty.add_child("value", bank_droty_val);
      bank_drotz.add_child("value", bank_drotz_val);

      bank_sx.add_child("value", bank_sx_val);
      bank_sy.add_child("value", bank_sy_val);

      bank_root.add_child("parameter", bank_drotx);
      bank_root.add_child("parameter", bank_droty);
      bank_root.add_child("parameter", bank_drotz);
      bank_root.add_child("parameter", bank_dx);
      bank_root.add_child("parameter", bank_dy);
      bank_root.add_child("parameter", bank_dz);
      bank_root.add_child("parameter", bank_sx);
      bank_root.add_child("parameter", bank_sy);

      parafile.add_child("component-link", bank_root);
    }

    // get L1 info for source
    ptree src;
    ptree src_dx, src_dy, src_dz;
    ptree src_dx_val, src_dy_val, src_dz_val;
    // -- get positional data from source
    IComponent_const_sptr source = instrument->getSource();
    V3D sourceRelPos = source->getRelativePos();
    // -- add date to node
    src_dx_val.put("<xmlattr>.val", sourceRelPos.X());
    src_dy_val.put("<xmlattr>.val", sourceRelPos.Y());
    src_dz_val.put("<xmlattr>.val", sourceRelPos.Z());
    src_dx.put("<xmlattr>.name", "x");
    src_dy.put("<xmlattr>.name", "y");
    src_dz.put("<xmlattr>.name", "z");
    src.put("<xmlattr>.name", source->getName());

    src_dx.add_child("value", src_dx_val);
    src_dy.add_child("value", src_dy_val);
    src_dz.add_child("value", src_dz_val);
    src.add_child("parameter", src_dx);
    src.add_child("parameter", src_dy);
    src.add_child("parameter", src_dz);

    parafile.add_child("component-link", src);

    // give everything to root
    root.add_child("parameter-file", parafile);
    // write the xml tree to disk
    g_log.notice() << "\tSaving parameter file as " << FileName << "\n";
    boost::property_tree::write_xml(
        FileName, root, std::locale(),
        boost::property_tree::xml_writer_settings<std::string>(' ', 2));
  }

  /**
   * Really this is the operator SaveIsawDetCal but only the results of the given
   * banks are saved.  L1 and T0 are also saved.
   *
   * @param filename     -The name of the DetCal file to save the results to
   * @param AllBankName  -the set of the NewInstrument names of the banks(panels)
   * @param instrument   -The instrument with the correct panel geometries
   *                      and initial path length
   * @param T0           -The time offset from the DetCal file
   */
  void SCDCalibratePanels2::saveIsawDetCal(
    const std::string &filename,
    boost::container::flat_set<std::string> &AllBankName,
    std::shared_ptr<Instrument> &instrument,
    double T0) {
    g_log.notice() << "Saving DetCal file in " << filename << "\n";

    // create a workspace to pass to SaveIsawDetCal
    const size_t number_spectra = instrument->getNumberDetectors();
    Workspace2D_sptr wksp =
        std::dynamic_pointer_cast<Workspace2D>(
            WorkspaceFactory::Instance().create("Workspace2D", number_spectra, 2,
                                                1));
    wksp->setInstrument(instrument);
    wksp->rebuildSpectraMapping(true /* include monitors */);

    // convert the bank names into a vector
    std::vector<std::string> banknames(AllBankName.begin(), AllBankName.end());

    // call SaveIsawDetCal
    API::IAlgorithm_sptr alg = createChildAlgorithm("SaveIsawDetCal");
    alg->setProperty("InputWorkspace", wksp);
    alg->setProperty("Filename", filename);
    alg->setProperty("TimeOffset", T0);
    alg->setProperty("BankNames", banknames);
    alg->executeAsChildAlg();
  }

} // namespace Crystal
} // namespace Mantid
