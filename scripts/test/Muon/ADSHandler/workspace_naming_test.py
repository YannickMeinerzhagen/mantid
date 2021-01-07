# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2020 ISIS Rutherford Appleton Laboratory UKRI,
#   NScD Oak Ridge National Laboratory, European Spallation Source,
#   Institut Laue - Langevin & CSNS, Institute of High Energy Physics, CAS
# SPDX - License - Identifier: GPL - 3.0 +
from Muon.GUI.Common.ADSHandler.workspace_naming import *
import unittest


class WorkspaceNamingTest(unittest.TestCase):

    def test_create_fitted_workspace_name(self):
        input_workspace_name = 'MUSR22725; Group; top; Asymmetry; #1'
        trial_function_name = "GausOsc"
        expected_directory_name = 'MUSR22725; Group; top; Asymmetry; #1; Fitted;GausOsc/'
        expected_workspace_name = 'MUSR22725; Group; top; Asymmetry; #1; Fitted;GausOsc; Workspace'

        name, directory = create_fitted_workspace_name(input_workspace_name, trial_function_name)

        self.assertEqual(name, expected_workspace_name)
        self.assertEqual(directory, expected_directory_name)

    def test_create_parameter_table_name(self):
        input_workspace_name = 'MUSR22725; Group; top; Asymmetry; #1'
        trial_function_name = "GausOsc"
        expected_directory_name = 'MUSR22725; Group; top; Asymmetry; #1; Fitted;GausOsc/'
        expected_workspace_name = 'MUSR22725; Group; top; Asymmetry; #1; Fitted Parameters;GausOsc'

        name, directory = create_parameter_table_name(input_workspace_name, trial_function_name)

        self.assertEqual(name, expected_workspace_name)
        self.assertEqual(directory, expected_directory_name)

    def test_create_multi_domain_fitted_workspace_name(self):
        input_workspace_name = 'MUSR22725; Group; top; Asymmetry; #1'
        trial_function_name = 'Polynomial'
        expected_directory_name = 'MUSR22725; Group; top; Asymmetry; #1; Fitted;Polynomial/'
        expected_workspace_name = 'MUSR22725; Group; top; Asymmetry; #1+ ...; Fitted;Polynomial'

        name, directory = create_multi_domain_fitted_workspace_name(input_workspace_name, trial_function_name)

        self.assertEqual(name, expected_workspace_name)
        self.assertEqual(directory, expected_directory_name)

    def test_get_run_numbers_as_string_from_workspace_name(self):
        instrument = "MUSR"
        runs = "62260"

        # test formatting
        workspace_name = "MUSR62260_raw_data MA"
        self.assertEqual(runs, get_run_numbers_as_string_from_workspace_name(
            workspace_name, instrument))
        workspace_name = "MUSR62260; GROUP; fwd; Asymmetry; MA"
        self.assertEqual(runs, get_run_numbers_as_string_from_workspace_name(
            workspace_name, instrument))

        # test multiple run numbers
        runs = "62260-62261,62263"
        workspace_name = "MUSR62260-62261,62263; GROUP; fwd; Asymmetry; MA"
        self.assertEqual(runs, get_run_numbers_as_string_from_workspace_name(
            workspace_name, instrument))


if __name__ == '__main__':
    unittest.main(buffer=False, verbosity=2)
