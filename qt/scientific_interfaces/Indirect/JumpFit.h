// Mantid Repository : https://github.com/mantidproject/mantid
//
// Copyright &copy; 2018 ISIS Rutherford Appleton Laboratory UKRI,
//   NScD Oak Ridge National Laboratory, European Spallation Source,
//   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
// SPDX - License - Identifier: GPL - 3.0 +
#pragma once

#include "IndirectFitAnalysisTab.h"
#include "JumpFitModel.h"
#include "ui_IndirectFitTab.h"

#include "IFQFitObserver.h"
#include "MantidAPI/IFunction.h"
#include "MantidAPI/TextAxis.h"

namespace MantidQt {
namespace CustomInterfaces {
namespace IDA {
class IDAFunctionParameterEstimation;

class DLLExport JumpFit : public IndirectFitAnalysisTab {
  Q_OBJECT

public:
  JumpFit(QWidget *parent = nullptr);

  std::string tabName() const override { return "FQFit"; }

  bool hasResolution() const override { return false; }

  void setupFitTab() override;

protected slots:
  void updateModelFitTypeString();
  void runClicked();

protected:
  void setRunIsRunning(bool running) override;
  void setRunEnabled(bool enable) override;

private:
  EstimationDataSelector getEstimationDataSelector() const override;
  IDAFunctionParameterEstimation createParameterEstimation() const;

  JumpFitModel *m_jumpFittingModel;
  std::unique_ptr<Ui::IndirectFitTab> m_uiForm;
  std::string fitTypeString() const;
};
} // namespace IDA
} // namespace CustomInterfaces
} // namespace MantidQt
