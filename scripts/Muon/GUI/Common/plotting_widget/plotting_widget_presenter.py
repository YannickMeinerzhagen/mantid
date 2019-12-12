# Mantid Repository : https://github.com/mantidproject/mantid
#
# Copyright &copy; 2018 ISIS Rutherford Appleton Laboratory UKRI,
#     NScD Oak Ridge National Laboratory, European Spallation Source
#     & Institut Laue - Langevin
# SPDX - License - Identifier: GPL - 3.0 +
from __future__ import (absolute_import, division, print_function)
import re
from Muon.GUI.Common.home_tab.home_tab_presenter import HomeTabSubWidget
from mantidqt.utils.observer_pattern import GenericObservable, GenericObserver, GenericObserverWithArgPassing
from Muon.GUI.Common.utilities.run_string_utils import run_list_to_string
from Muon.GUI.FrequencyDomainAnalysis.frequency_context import FREQUENCY_EXTENSIONS

COUNTS_PLOT_TYPE = 'Counts'
ASYMMETRY_PLOT_TYPE = 'Asymmetry'
FREQ_PLOT_TYPE = "Frequency "
workspace_index = 0


class PlotWidgetPresenter(HomeTabSubWidget):

    def __init__(self, view, model, context):
        """
        :param view: A reference to the QWidget object for plotting
        :param model: A refence to a model which contains the plotting logic
        :param context: A reference to the Muon context object
        """
        self._view = view
        self._model = model
        self.context = context
        self._view.on_plot_button_clicked(self.handle_data_updated)
        self._view.on_rebin_options_changed(self.handle_use_raw_workspaces_changed)
        self._view.on_plot_type_changed(self.handle_plot_type_changed)
        self._view.on_tiled_by_type_changed(self.handle_tiled_by_changed_on_view)
        self._view.on_plot_tiled_changed(self.handle_plot_tiled_changed)

        self.input_workspace_observer = GenericObserver(self.handle_data_updated)
        self.added_group_or_pair_observer = GenericObserverWithArgPassing(
            self.handle_added_or_removed_group_or_pair_to_plot)
        self.fit_observer = GenericObserver(self.handle_fit_completed)
        self.removed_group_pair_observer = GenericObserver(self.handle_removed_group_or_pair_to_plot)

        self.rebin_options_set_observer = GenericObserver(self.handle_rebin_options_set)
        self.plot_guess_observer = GenericObserver(self.handle_plot_guess_changed)
        self.workspace_deleted_from_ads_observer = GenericObserverWithArgPassing(self.handle_workspace_deleted_from_ads)
        self.workspace_replaced_in_ads_observer = GenericObserverWithArgPassing(self.handle_workspace_replaced_in_ads)

        self.plot_type_changed_notifier = GenericObservable()

        if self.context._frequency_context:
            for ext in FREQUENCY_EXTENSIONS.keys():
                self._view.addItem(FREQ_PLOT_TYPE + FREQUENCY_EXTENSIONS[ext])
            self._view.addItem(FREQ_PLOT_TYPE + "All")
        self.instrument_observer = GenericObserver(self.handle_instrument_changed)

    def show(self):
        """
        Calls show on the view QtWidget
        """
        self._view.show()

    def update_view_from_model(self):
        """
        This is required in order for this presenter to match the base class interface
        """
        pass

    # ------------------------------------------------------------------------------------------------------------------
    # Handle user making plotting related changes from GUI
    # ------------------------------------------------------------------------------------------------------------------

    def handle_data_updated(self):
        """
        Handles the group, pair calculation finishing. Checks whether the list of workspaces has changed before doing
        anything as workspaces being modified in place is handled by the ADS handler observer.
        """
        if self._model.plotted_workspaces == self.get_workspaces_to_plot(self._view.if_raw(),
                                                                         self._view.get_selected()):
            # If the workspace names have not changed the ADS observer should
            # handle any updates
            return

        if self._view.is_tiled_plot():
            self.update_model_tile_plot_positions(self._view.get_tiled_by_type())
            # update view based on number of axis
            self._view.new_plot_figure(self._model.number_of_axes)

        self.plot_all_selected_workspaces()

    def handle_workspace_deleted_from_ads(self, workspace):
        """
        Handles the workspace being deleted from ads
        """
        if workspace in self._model.plotted_workspaces:
            self._model.remove_workspaces_from_plotted_workspaces(workspace)

        self.plot_all_selected_workspaces()

    def handle_workspace_replaced_in_ads(self, workspace):
        """
        Handles the use raw workspaces being changed (e.g rebinned) in ads
        """
        if not self._view.if_raw():
            if workspace in self._model.plotted_workspaces:
                # if one of the plotted_workspaces has been changed
                # we should plot everything again (ONCE)
                self._model.remove_workspace_from_plot(workspace, self._view.get_fig().axes)
                ax = self.get_workspace_plot_axis(workspace)
                label = self.get_workspace_legend_label(workspace)
                self._model.add_workspace_to_plot(ax, workspace, workspace_index, label)
                # add workspace to tracked workspaces
                self._model.add_workspace_to_plotted_workspaces(workspace)
                self._view.force_redraw()

    def handle_use_raw_workspaces_changed(self):
        """
        Handles the use raw workspaces being changed.
        """
        if not self._view.if_raw() and not self.context._do_rebin():
            self._view.set_raw_checkbox_state(True)
            self._view.warning_popup('No rebin options specified')
            return
        # plot workspaces
        self.plot_all_selected_workspaces()

    def handle_plot_type_changed(self):
        """
        Handles the plot type being changed on the view
        """
        current_plot_type = self._view.get_selected()
        if len(self.context.group_pair_context.selected_pairs) != 0 and current_plot_type == COUNTS_PLOT_TYPE:
            self._view.plot_selector.blockSignals(True)
            self._view.plot_selector.setCurrentText(ASYMMETRY_PLOT_TYPE)
            self._view.plot_selector.blockSignals(False)
            self._view.warning_popup(
                'Pair workspaces have no counts workspace, remove pairs from analysis and retry')
            return
        # force the plot to update
        if self.context._frequency_context:
            self.context._frequency_context.plot_type = self._view.get_selected()[len(FREQ_PLOT_TYPE):]
        self.plot_type_changed_notifier.notify_subscribers()

        self.plot_all_selected_workspaces()

    def handle_plot_tiled_changed(self, state):
        """
        Handles the plot tiled checkbox being changed
        """
        # get the number of groups from groups and pair selector
        if state == 2:  # tiled plot
            self.update_model_tile_plot_positions(self._view.get_tiled_by_type())
            self._view.new_plot_figure(self._model.number_of_axes)
            self.plot_all_selected_workspaces()
        if state == 0:  # not tiled plot
            self._view.new_plot_figure(num_axes=1)
            self._model.number_of_axes = 1
            self.plot_all_selected_workspaces()

    def handle_added_or_removed_group_or_pair_to_plot(self, is_added):
        """
        Handles a group or pair being added or removed from
        the grouping widget analysis table
        """

        if is_added:
            self.handle_added_group_or_pair_to_plot()
        else:
            self.handle_removed_group_or_pair_to_plot()

    def handle_added_group_or_pair_to_plot(self):
        """
        Handles a group or pair being added from the view
        """
        # if tiled by group, we will need to recreate the tiles
        if self._view.is_tiled_plot() and self._view.get_tiled_by_type() == 'group':
            self.update_model_tile_plot_positions(self._view.get_tiled_by_type())
            self._view.new_plot_figure(self._model.number_of_axes)
            self.plot_all_selected_workspaces()
            return

        # check if we already have it plotted
        if self.context.group_pair_context.selected_pairs + \
                self.context.group_pair_context.selected_groups == self._model.plotted_group:
            return
        workspace_list = self.get_workspace_list_to_plot()

        # if the plot window is empty - plot all sel
        if len(self._model.plotted_workspaces) == 0:
            self.plot_all_selected_workspaces()
        else:  # add plot to previously generated axis
            for ws in workspace_list:
                if ws not in self._model.plotted_workspaces:
                    ax = self.get_workspace_plot_axis(ws)
                    label = self.get_workspace_legend_label(ws)
                    self._model.add_workspace_to_plot(ax, ws, workspace_index, label)
                    # add workspace to tracked workspaces
                    self._model.add_workspace_to_plotted_workspaces(ws)

        self._view.force_redraw()

    def handle_removed_group_or_pair_to_plot(self):
        """
        Handles a group or pair being removed in grouping widget analysis table
        """

        # if tiled by group, we will need to recreate the tiles
        if self._view.is_tiled_plot() and self._view.get_tiled_by_type():
            self.update_model_tile_plot_positions(self._view.get_tiled_by_type())
            self._view.new_plot_figure(self._model.number_of_axes)
            self.plot_all_selected_workspaces()
            return

        workspace_list = self.get_workspace_list_to_plot()
        for ws in self._model.plotted_workspaces:
            if ws not in workspace_list:
                self._model.remove_workspace_from_plot(ws, self._view.get_fig().axes)

        self._view.force_redraw()

    def handle_fit_completed(self):
        """
        When a new fit is done adds the fit to the plotted workspaces if appropriate
        """
        if self.context.fitting_context.number_of_fits <= 1:
            for workspace_name in self._model.plotted_fit_workspaces:
                self._model.remove_workspace_from_plot(workspace_name, self._view.get_fig().axes)

        if self.context.fitting_context.fit_list:
            current_fit = self.context.fitting_context.fit_list[-1]
            combined_ws_list = self._model.plotted_workspaces + list(
                self._model.plotted_workspaces_inverse_binning.values())
            list_of_output_workspaces_to_plot = [output for output, input in
                                                 zip(current_fit.output_workspace_names, current_fit.input_workspaces)
                                                 if input in combined_ws_list]
            list_of_output_workspaces_to_plot = list_of_output_workspaces_to_plot if list_of_output_workspaces_to_plot \
                else [current_fit.output_workspace_names[-1]]
        else:
            list_of_output_workspaces_to_plot = []
        for workspace_name in list_of_output_workspaces_to_plot:
            label = self.get_workspace_legend_label(workspace_name)
            ax = self.get_workspace_plot_axis(workspace_name)
            fit_function = workspace_name.rsplit(';')[6]
            # add fit workspace to tracked workspaces in model
            self._model.add_workspace_to_plotted_fit_workspaces(workspace_name)
            # plot fit and diff workspaces
            self._model.add_workspace_to_plot(ax, workspace_name, 1,
                                              label + fit_function + ': Fit')
            self._model.add_workspace_to_plot(ax, workspace_name, 2,
                                              label + fit_function + ': Diff')

        self._view.force_redraw()

    def handle_rebin_options_set(self):
        if self.context._do_rebin():
            self._view.set_raw_checkbox_state(False)
        else:
            self._view.set_raw_checkbox_state(True)

    def handle_tiled_by_changed_on_view(self, index):
        # make sure we are currently a tiled plot -  else do nothing
        if self._view.is_tiled_plot():
            if index == 0:
                self.update_model_tile_plot_positions('group')
            else:
                self.update_model_tile_plot_positions('run')
            self._view.new_plot_figure(self._model.number_of_axes)
            self.plot_all_selected_workspaces()

    def handle_instrument_changed(self):
        # generate a new blank plot_figure
        self._view.new_plot_figure(1)

    def handle_plot_guess_changed(self):

        for guess in [ws for ws in self._model.plotted_fit_workspaces if '_guess' in ws]:
            self._model.remove_workspace_from_plot(guess, self._view.get_fig().axes)

            if self.context.fitting_context.plot_guess and self.context.fitting_context.guess_ws is not None:
                self._model.add_workspace_to_plot(self._view.get_fig().axes[0], self.context.fitting_context.guess_ws,
                                                  workspace_index=1,
                                                  label='Fit Function Guess')
            self._view.force_redraw()

    # ------------------------------------------------------------------------------------------------------------------
    # Plotting controls
    # ------------------------------------------------------------------------------------------------------------------

    def plot_all_selected_workspaces(self):
        """
        Plots all the selected workspaces (from grouping tab) in the plot window,
        clearing any previous plots
        """
        tiled = self._view.is_tiled_plot()
        # get the workspace list, formed from the selected groups / pairs
        workspace_list = self.get_workspace_list_to_plot()

        # clear previous plots and fitting
        self._model.clear_plot_model(self._view.get_fig().axes)
        self.context.fitting_context.clear()
        # plot new workspaces
        workspace_titles = self.get_plot_title(tiled, self._view.get_tiled_by_type())
        for workspace in workspace_list:
            ax = self.get_workspace_plot_axis(workspace)
            label = self.get_workspace_legend_label(workspace)
            self._model.add_workspace_to_plot(ax, workspace, 0, label)
            self._model.add_workspace_to_plotted_workspaces(workspace)

        # scale the axis and set title
        self._view.set_fig_titles(workspace_titles)
        self._model.set_x_lim(self.get_domain(), self._view.get_fig().axes)
        self._view.force_redraw()

        self._model.plotted_workspaces_inverse_binning = {
            workspace: self.context.group_pair_context.get_equivalent_group_pair(workspace)
            for workspace in workspace_list
            if self.context.group_pair_context.get_equivalent_group_pair(workspace)}

    def update_model_tile_plot_positions(self, tiled_type):
        """
        Updates tile dictionary in the model, which maps workspaces to
        the axis which they are to be plotted on
        :param tiled_type: A string which states whether the tiling is performed by run, or by group
        """
        self._model.tiled_plot_positions.clear()
        if tiled_type == 'run':  # tile by run
            flattened_run_list = [item for sublist in self.context.data_context.current_runs for item in sublist]
            instrument = self.context.data_context.instrument
            for i, run in enumerate(flattened_run_list):
                self._model.tiled_plot_positions[instrument + str(run)] = i
        else:  # tile by group or pair
            for i, grppair in enumerate(self.context.group_pair_context.selected_groups +
                                        self.context.group_pair_context.selected_pairs):
                self._model.tiled_plot_positions[grppair] = i
        # update number of axis in model
        self._model.number_of_axes = len(self._model.tiled_plot_positions)

    def get_workspace_list_to_plot(self):
        """
         :return: a list of workspace names to plot
         """
        # get the list of workspaces to plot
        workspace_list = self.get_workspaces_to_plot(self._view.if_raw(), self._view.get_selected())
        return workspace_list

    def get_workspaces_to_plot(self, is_raw, plot_type):
        """
        :param is_raw: Whether to use raw or rebinned data
        :param plot_type: plotting type, e.g Counts, Frequency Re
        :return: a list of workspace names
        """
        currently_selected_groups = self.context.group_pair_context.selected_groups
        currently_selected_pairs = self.context.group_pair_context.selected_pairs
        workspace_list = []
        if FREQ_PLOT_TYPE in plot_type:
            for grouppair in currently_selected_groups + currently_selected_pairs:
                workspace_list += self.get_freq_workspaces_to_plot(grouppair, plot_type)
            return workspace_list
        else:
            for grouppair in currently_selected_groups + currently_selected_pairs:
                workspace_list += self.get_time_workspaces_to_plot(grouppair, is_raw, plot_type)
            return workspace_list

    def get_freq_workspaces_to_plot(self, current_group_pair, plot_type):
        """
        :param current_group_pair: The group/pair currently selected
        :param plot_type: Whether to plot counts or asymmetry
        :return: a list of workspace names
        """
        try:
            runs = ""
            seperator = ""
            for run in self.context.data_context.current_runs:
                runs += seperator + str(run[0])
                seperator = ", "
            workspace_list = self.context.get_names_of_frequency_domain_workspaces_to_fit(
                runs, current_group_pair, True, plot_type[len(FREQ_PLOT_TYPE):])

            return workspace_list
        except AttributeError:
            return []

    def get_time_workspaces_to_plot(self, current_group_pair, is_raw, plot_type):
        """
        :param current_group_pair: The group/pair currently selected
        :param is_raw: Whether to use raw or rebinned data
        :param plot_type: Whether to plot counts or asymmetry
        :return: a list of workspace names
        """
        try:
            if is_raw:
                workspace_list = self.context.group_pair_context[current_group_pair].get_asymmetry_workspace_names(
                    self.context.data_context.current_runs)
            else:
                workspace_list = self.context.group_pair_context[
                    current_group_pair].get_asymmetry_workspace_names_rebinned(
                    self.context.data_context.current_runs)

            if plot_type == COUNTS_PLOT_TYPE:
                workspace_list = [item.replace(ASYMMETRY_PLOT_TYPE, COUNTS_PLOT_TYPE)
                                  for item in workspace_list if ASYMMETRY_PLOT_TYPE in item]

            return workspace_list
        except AttributeError:
            return []

    def get_plot_title(self, tiled, tiled_type):
        """
        Generates a title for the plot based on current instrument group and run numbers
        :param tiled: True or false as to whether this is a tiled plot
        :param tiled_type: Whether we are tiling by group or by run
        :return: Plot titles
        """
        flattened_run_list = [
            item for sublist in self.context.data_context.current_runs for item in sublist]
        instrument = self.context.data_context.instrument

        plot_titles = []
        # if tiled we need to create a plot title for each plot
        if tiled:
            if tiled_type == 'run':
                for run in flattened_run_list:
                    plot_titles.append(instrument + str(run))
            else:
                for grouppair in self.context.group_pair_context.selected_groups + \
                                 self.context.group_pair_context.selected_pairs:
                    title = self.context.data_context.instrument + ' ' + run_list_to_string(flattened_run_list) + \
                            ' ' + str(grouppair)
                    plot_titles.append(title)
            return plot_titles
        else:
            return [self.context.data_context.instrument + ' ' + run_list_to_string(flattened_run_list)]

    def get_workspace_legend_label(self, workspace_name):
        """
        Generates a label for the workspace
        :return: workspace label
        """
        if self._view.is_tiled_plot():
            if self._view.get_tiled_by_type() == 'group':
                label = self.context.data_context.instrument + self._get_run_number_from_workspace(workspace_name)
            else:
                label = self._get_group_or_pair_from_name_workspace(workspace_name)
        else:
            label = workspace_name
        return label

    def get_workspace_plot_axis(self, workspace_name):
        """
        Gets the axis from the view, which is the model with then use to plot the workspace onto
        :return: axis
        """
        if self._view.is_tiled_plot():
            if self._view.get_tiled_by_type() == 'group':
                tiled_key = self._get_group_or_pair_from_name_workspace(workspace_name)
            else:
                tiled_key = self.context.data_context.instrument + self._get_run_number_from_workspace(workspace_name)
            position = self._model.tiled_plot_positions[tiled_key]
            ax = self._view.get_fig().axes[position]
        else:
            ax = self._view.get_fig().axes[0]
        return ax

    def get_domain(self):
        if FREQ_PLOT_TYPE in self._view.get_selected():
            return "Frequency"
        else:
            return "Time"

    # Note: This should be implemented as a lower level property
    # as currently they are specialised methods dependent on the workspace name format
    # the number following the instrument name is the run
    def _get_run_number_from_workspace(self, workspace_name):
        instrument = self.context.data_context.instrument
        run = re.findall(r'%s(\d+)' % instrument, workspace_name)
        return run[0]

    # the string following either 'Pair Asym; %s' or  Group; "
    def _get_group_or_pair_from_name_workspace(self, workspace_name):
        for grppair in self.context.group_pair_context.selected_groups + self.context.group_pair_context.selected_pairs:
            grp = re.findall(r'%s' % grppair, workspace_name)
            if len(grp) > 0:
                return grp[0]
