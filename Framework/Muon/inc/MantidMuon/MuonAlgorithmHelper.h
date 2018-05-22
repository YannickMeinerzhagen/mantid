#ifndef MANTID_MUON_MUONALGORITHMHELPER_H_
#define MANTID_MUON_MUONALGORITHMHELPER_H_

#include "MantidAPI/GroupingLoader.h"
#include "MantidAPI/MatrixWorkspace.h"
#include "MantidAPI/WorkspaceGroup.h"
#include "MantidKernel/System.h"

#include <string>
#include <vector>

namespace Mantid {
namespace Muon {
/// Types of entities we are dealing with
enum ItemType { Pair, Group };

/// Possible plot types users might request
enum PlotType { Asymmetry, Counts, Logarithm };

/// Parameters from parsed workspace name
struct DatasetParams {
  std::string label;
  std::string instrument;
  std::vector<int> runs;
  ItemType itemType;
  std::string itemName;
  PlotType plotType;
  std::string periods;
  size_t version;
};

/// Parameters for creating analysis workspace
struct AnalysisOptions {
  std::string summedPeriods;            /// Set of periods to sum
  std::string subtractedPeriods;        /// Set of periods to subtract
  double timeZero = 0;                  /// Value to use for t0 correction
  double loadedTimeZero = 0;            /// Time zero from data file
  std::pair<double, double> timeLimits; /// Min, max X values
  std::string rebinArgs;          /// Arguments for rebin (empty to not rebin)
  std::string groupPairName;      /// Name of group or pair to use
  Mantid::API::Grouping grouping; /// Grouping to use
  PlotType plotType = {};         /// Type of analysis to perform
  explicit AnalysisOptions() {}
};

/// Whether multiple fitting is enabled or disabled
enum class MultiFitState { Enabled, Disabled };
} // namespace Muon

namespace MuonAlgorithmHelper {

/// Returns a first period MatrixWorkspace in a run workspace
Mantid::API::MatrixWorkspace_sptr firstPeriod(API::Workspace_sptr ws);

/// Get a run label for the workspace
std::string getRunLabel(const API::Workspace_sptr &ws);

/// Get a run label for a list of workspaces
std::string getRunLabel(const std::vector<API::Workspace_sptr> &wsList);

/// Get a run label given instrument and run numbers
std::string getRunLabel(const std::string &instrument,
                        const std::vector<int> &runNumbers);

/// Makes sure the specified workspaces are in specified group
void groupWorkspaces(const std::string &groupName,
                     const std::vector<std::string> &inputWorkspaces);

/// Finds runs of consecutive numbers
std::vector<std::pair<int, int>>
findConsecutiveRuns(const std::vector<int> &runs);

/// Generate new analysis workspace name
std::string generateWorkspaceName(const Muon::DatasetParams &params);
} // namespace MuonAlgorithmHelper
} // namespace Mantid

#endif /* MANTIDQT_CUSTOMINTERFACES_MUONALGORITHMHELPER_H_ */
