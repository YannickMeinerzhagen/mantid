// Mantid Repository : https://github.com/mantidproject/mantid
//
// Copyright &copy; 2018 ISIS Rutherford Appleton Laboratory UKRI,
//     NScD Oak Ridge National Laboratory, European Spallation Source
//     & Institut Laue - Langevin
// SPDX - License - Identifier: GPL - 3.0 +
#ifndef MANTID_CUSTOMINTERFACES_MOCKRUNSTABLEVIEW_H_
#define MANTID_CUSTOMINTERFACES_MOCKRUNSTABLEVIEW_H_
#include "DllConfig.h"
#include "GUI/RunsTable/IRunsTableView.h"
#include "MantidKernel/WarningSuppressions.h"
#include <gmock/gmock.h>

GNU_DIAG_OFF_SUGGEST_OVERRIDE

namespace MantidQt {
namespace CustomInterfaces {

class MockRunsTableView : public IRunsTableView {
public:
  MOCK_METHOD1(subscribe, void(RunsTableViewSubscriber *));
  MOCK_METHOD1(setProgress, void(int));
  MOCK_METHOD0(jobs, MantidQt::MantidWidgets::Batch::IJobTreeView &());
  MOCK_METHOD0(resetFilterBox, void());

  MOCK_METHOD0(invalidSelectionForCopy, void());
  MOCK_METHOD0(invalidSelectionForPaste, void());
  MOCK_METHOD0(invalidSelectionForCut, void());

  MOCK_METHOD0(mustSelectRow, void());
  MOCK_METHOD0(mustSelectGroup, void());
  MOCK_METHOD0(mustNotSelectGroup, void());
  MOCK_METHOD0(mustSelectGroupOrRow, void());

  MOCK_CONST_METHOD0(getInstrumentName, std::string());
  MOCK_METHOD1(setInstrumentName, void(std::string const &));
};
} // namespace CustomInterfaces
} // namespace MantidQt
GNU_DIAG_ON_SUGGEST_OVERRIDE
#endif // MANTID_CUSTOMINTERFACES_MOCKRUNSTABLEVIEW_H_
