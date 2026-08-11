############################################################
#  [*] Chart generator — matplotlib SVG renderers
#
#  Rendering layer of the stats pipeline. The chart flows
#  in blnstats/__init__.py (generateCoefficientCharts,
#  generateOverlappingCoefficientCharts,
#  generateCoefficientsOnSingleChart, generateLorenzCharts,
#  generateExampleLorenzCharts,
#  generateGeneralStatisticsCharts — driven by workflows.py
#  and main.py --calculate-ln-stats) and
#  CompareSources.plot_data (data_import/compare_sources.py)
#  feed prepared x/y series in; the rendered SVGs flow on
#  to /DATA/GENERATED/... via save_chart, where the
#  frontend picks them up.
#
#  All text renders through LaTeX (text.usetex) — the
#  backend container must ship a TeX installation or every
#  render call dies.
#
#  NOTE: mdates and the typing imports are unused (dead
#  imports, left untouched by the restyle).
############################################################


from matplotlib.ticker import PercentFormatter
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import io
import os
from datetime import datetime
from typing import List, Dict, Any, Optional








############################################################
# BaseChartGenerator
############################################################
#
# One-shot line-chart builder: construct with the series,
# stage styling with customize_axes / set_x_ticks, render
# with generate_line_chart, persist with save_chart.
# Instances are single-use — rendering closes the figure.
#
# Used by:
#   - generateCoefficientCharts,
#     generateOverlappingCoefficientCharts,
#     generateCoefficientsOnSingleChart,
#     generateGeneralStatisticsCharts (blnstats/__init__.py)
#   - CompareSources.plot_data
#     (blnstats/data_import/compare_sources.py)
#   - LorenzCurveChartGenerator (below) — subclass reusing
#     the styling/serialization helpers
############################################################

class BaseChartGenerator:
    # Shared font sizing for every chart on the site;
    # callers/subclasses override single values (Lorenz
    # shrinks the axis labels, CompareSources the y label)
    title_fontsize = 15
    x_label_fontsize = 24
    y_label_fontsize = 24
    tick_label_fontsize = 15
    legend_fontsize = 15
    footer_fontsize = 10






    ############################################################
    # __init__
    ############################################################
    #
    # One shared x series; y_data_list carries one list per
    # line and is zipped with labels at plot time. x_ticks
    # stays None until set_x_ticks — None means "matplotlib
    # picks the ticks".
    #
    # Used by:
    #   - every chart flow listed on the class banner
    ############################################################

    def __init__(self, x_data, y_data_list, labels):
        self.x_data = x_data
        self.y_data_list = y_data_list
        self.labels = labels
        self.x_ticks = None






    ############################################################
    # customize_axes
    ############################################################
    #
    # Stages axis styling on the instance — nothing touches
    # matplotlib until _customize_axes applies it at render
    # time. When y_lim is omitted the limits are derived
    # from the data with padding (_find_y_lim_dynamically).
    #
    # BUG (documented, not fixed): the x_ticks parameter is
    # accepted but never stored — only set_x_ticks can set
    # ticks.
    #
    # Used by:
    #   - all BaseChartGenerator flows listed on the class
    #     banner
    #   - generate_lorenz_curves /
    #     generate_example_lorenz_curve (below), which then
    #     apply it via _customize_axes
    ############################################################

    def customize_axes(self, x_label: str, y_label: str, title=None, x_formatter=None, y_formatter=None,
                        x_lim=None, y_lim=None, x_ticks=None, y_ticks=None, grid: bool = True):
        # DEAD CODE (documented, not fixed): this early y_lim
        # computation is overwritten by the identical branch at
        # the end of the method
        if y_lim is None:
            self.y_lim = self._find_y_lim_dynamically(self.y_data_list)

        self.title = title
        self.x_label = x_label
        self.y_label = y_label
        self.x_formatter = x_formatter
        self.y_formatter = y_formatter
        self.x_lim = x_lim
        self.y_ticks = y_ticks
        self.grid = grid

        if y_lim is None:
            self.y_lim = self._find_y_lim_dynamically(self.y_data_list)
        else:
            self.y_lim = y_lim






    ############################################################
    # set_x_ticks
    ############################################################
    #
    # Chooses which x positions get ticks: an explicit
    # x_ticks list wins; otherwise dates whose YYYY-MM-DD
    # form ends with ends_with are kept. exclude_ends_with
    # then removes matches (used to thin crowded month
    # labels).
    #
    # GOTCHA: calling with only exclude_ends_with while
    # self.x_ticks is still None raises TypeError (the
    # exclusion loop iterates None). Current callers always
    # pass ends_with, so it never triggers today.
    #
    # Used by:
    #   - generateCoefficientCharts,
    #     generateOverlappingCoefficientCharts,
    #     generateCoefficientsOnSingleChart,
    #     generateGeneralStatisticsCharts
    #     (blnstats/__init__.py)
    #   - CompareSources.plot_data
    #     (blnstats/data_import/compare_sources.py)
    #   - never called for Lorenz charts (percent axes)
    ############################################################

    def set_x_ticks(self, ends_with=None, x_ticks=None, exclude_ends_with=None):
        if x_ticks:
            self.x_ticks = x_ticks

        elif ends_with:
            self.x_ticks = [
                date for date in self.x_data
                if date.strftime('%Y-%m-%d').endswith(ends_with)
            ]

            # First/last data points are forced in so the axis
            # always shows its true extent
            if self.x_data[0] not in self.x_ticks:
                self.x_ticks.insert(0, self.x_data[0])

            if self.x_data[-1] not in self.x_ticks:
                self.x_ticks.append(self.x_data[-1])


        # Runs on top of whichever branch above filled x_ticks
        # (TypeError if neither did — see banner)
        if exclude_ends_with:
            self.x_ticks = [
                date for date in self.x_ticks
                if not any(date.strftime('%Y-%m-%d').endswith(pattern) for pattern in exclude_ends_with)
            ]






    ############################################################
    # _customize_axes
    ############################################################
    #
    # Applies the staged styling to the live fig/ax. Tick
    # labels are always rendered as YYYY-MM-DD, so non-date
    # x_ticks would crash on strftime here — every current
    # chart is a date series.
    #
    # Used by:
    #   - generate_line_chart (below)
    #   - generate_lorenz_curves /
    #     generate_example_lorenz_curve (below)
    ############################################################

    def _customize_axes(self):
        if self.x_label:
            self.ax.set_xlabel(self.x_label, fontsize=self.x_label_fontsize)
        if self.y_label:
            self.ax.set_ylabel(self.y_label, fontsize=self.y_label_fontsize)
        if self.x_formatter:
            self.ax.xaxis.set_major_formatter(self.x_formatter)
        if self.y_formatter:
            self.ax.yaxis.set_major_formatter(self.y_formatter)
        if self.x_lim:
            self.ax.set_xlim(*self.x_lim)
        if self.y_lim:
            self.ax.set_ylim(*self.y_lim)

        self.ax.tick_params(axis='both', which='major', labelsize=self.tick_label_fontsize)

        if self.x_ticks is not None:
            # set_x_ticks may have left strings in x_ticks —
            # convert in place so set_xticks gets datetimes
            if isinstance(self.x_data[0], datetime):
                self.x_ticks = [datetime.strptime(tick, '%Y-%m-%d') if isinstance(tick, str) else tick for tick in self.x_ticks]
            self.ax.set_xticks(self.x_ticks)
            self.ax.set_xticklabels([tick.strftime('%Y-%m-%d') for tick in self.x_ticks], fontsize=self.tick_label_fontsize)

        if self.y_ticks is not None:
            self.ax.set_yticks(self.y_ticks)
            self.ax.set_yticklabels(self.y_ticks, fontsize=self.tick_label_fontsize)

        if self.grid:
            self.ax.grid(True)
        self.fig.tight_layout()






    ############################################################
    # _find_y_lim_dynamically
    ############################################################
    #
    # (min, max) over all series with 2% padding below and
    # 25% headroom above — the headroom keeps the
    # upper-left legend off the curves. A minimum below 20%
    # of the maximum snaps to 0 so the baseline reads
    # naturally.
    #
    # GOTCHA: an empty/None y_data_list returns
    # (inf, -inf) — the Lorenz subclass keeps
    # y_data_list=None and only avoids this because its
    # flows always pass an explicit y_lim.
    #
    # Used by:
    #   - customize_axes (above) — when y_lim is omitted
    ############################################################

    def _find_y_lim_dynamically(self, y_data_list):
        overall_y_min = float('inf')
        overall_y_max = float('-inf')

        if y_data_list:
            for y_data in y_data_list:
                current_y_min = min(y_data) - (0.02 * (max(y_data) - min(y_data)))
                current_y_max = max(y_data) + (0.25 * (max(y_data) - min(y_data)))

                overall_y_min = min(overall_y_min, current_y_min)
                overall_y_max = max(overall_y_max, current_y_max)

        # A floor near zero reads better as exactly zero
        if overall_y_min < 0.2 * overall_y_max:
            overall_y_min = 0

        return (overall_y_min, overall_y_max)






    ############################################################
    # _add_footer_texts
    ############################################################
    #
    # Copyright bottom-right, generation timestamp
    # bottom-left. The timestamp makes every regenerated
    # SVG differ byte-wise even when the data is unchanged.
    #
    # Used by:
    #   - generate_line_chart (below)
    #   - generate_lorenz_curves /
    #     generate_example_lorenz_curve (below)
    ############################################################

    def _add_footer_texts(self):
        self.fig.text(0.99, 0.01, '© Vilnius university Kaunas faculty', ha='right', fontsize=self.footer_fontsize)
        self.fig.text(0.01, 0.01, 'Updated: ' + datetime.now().strftime('%Y-%m-%d %H:%M:%S'), ha='left', fontsize=self.footer_fontsize)






    ############################################################
    # generate_line_chart
    ############################################################
    #
    # Renders the staged series as a multi-line chart and
    # returns the SVG as BytesIO (also kept on
    # self.virtual_file for save_chart). print_header
    # toggles the title, print_footer the
    # copyright/timestamp strip — the flows render each
    # chart repeatedly with these off for embed variants.
    #
    # DEAD CODE (documented, not fixed): the (6, 6) figsize
    # legend special-case — both branches are identical.
    #
    # Used by:
    #   - generateCoefficientCharts,
    #     generateOverlappingCoefficientCharts,
    #     generateCoefficientsOnSingleChart,
    #     generateGeneralStatisticsCharts
    #     (blnstats/__init__.py)
    #   - CompareSources.plot_data
    #     (blnstats/data_import/compare_sources.py)
    ############################################################

    def generate_line_chart(self, figsize=None, print_header=True, print_footer=True):
        # STEP 1: set up the figure — LaTeX text rendering,
        # near-zero x margins so curves span the full width
        # =================================================
        with plt.rc_context({'text.usetex': True, 'font.family': 'serif'}):

            self.figsize = figsize
            self.fig, self.ax = plt.subplots(figsize=self.figsize)

            self.ax.margins(x=0.01, y=0)


            # STEP 2: optional header title
            # =============================
            if self.title and print_header:
                self.ax.set_title(self.title, fontsize=self.title_fontsize)


            # STEP 3: one line per series, zipped with labels
            # ===============================================
            for y_data, label in zip(self.y_data_list, self.labels):
                self.ax.plot(self.x_data, y_data, label=label)

            # Both branches identical — dead special-case,
            # kept as-is (see banner)
            if(self.figsize == (6, 6)):
                self.ax.legend(loc='upper left', fontsize=self.legend_fontsize)
            else:
                self.ax.legend(loc='upper left', fontsize=self.legend_fontsize)


            # STEP 4: apply the staged styling, then slant the
            # date labels for readability
            # ================================================
            self._customize_axes()

            self.fig.autofmt_xdate()


            # STEP 5: footer strip, reserving 3% of the height
            # for it in the layout
            # ================================================
            if print_footer:
                self._add_footer_texts()

            gap_bottom = 0.03 if print_footer else 0.0
            self.fig.tight_layout(rect=[0, gap_bottom, 1, 1])


            # STEP 6: serialize to SVG and hand the buffer back
            # =================================================
            self.virtual_file = self.get_virtual_file()

            return self.virtual_file






    ############################################################
    # get_virtual_file
    ############################################################
    #
    # Serializes the current figure to an in-memory SVG and
    # CLOSES it — nothing can be drawn afterwards. SVG
    # keeps the LaTeX text crisp at any zoom (a dpi=1000
    # PNG export was tried and dropped — see the commented
    # line).
    #
    # Used by:
    #   - generate_line_chart (above)
    #   - generate_lorenz_curves /
    #     generate_example_lorenz_curve (below)
    ############################################################

    def get_virtual_file(self):
        virtual_file = io.BytesIO()
        # self.fig.savefig(virtual_file, format='png', dpi=1000)
        self.fig.savefig(virtual_file, format='svg')
        plt.close(self.fig)
        virtual_file.seek(0)
        return virtual_file






    ############################################################
    # save_chart
    ############################################################
    #
    # Writes the last rendered SVG (self.virtual_file) to
    # disk, creating the target folder. Only valid after a
    # generate_* call — virtual_file does not exist before.
    #
    # Used by:
    #   - every chart flow listed on the class banner —
    #     each figsize/header/footer variant is saved right
    #     after its generate_* call
    ############################################################

    def save_chart(self, filename: str):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'wb') as f:
            f.write(self.virtual_file.getbuffer())
        return filename








############################################################
# LorenzCurveChartGenerator
############################################################
#
# Lorenz-curve charts (cumulative % of population vs
# cumulative % of wealth) on 0-100 percent axes, plus the
# dashed perfect-equality diagonal. datasets is a list of
# dicts with 'percentiles', 'cumulative_percentages' and
# 'label' keys, prepared by generateLorenzCharts.
#
# GOTCHA: __init__ does NOT call super().__init__ —
# x_data/labels never exist and y_data_list stays None, so
# inherited helpers that touch them (set_x_ticks,
# _find_y_lim_dynamically) only work because the Lorenz
# flows never reach those paths (explicit y_lim, no tick
# filtering).
#
# Used by:
#   - generateLorenzCharts (blnstats/__init__.py)
#   - generateExampleLorenzCharts (blnstats/__init__.py)
############################################################

class LorenzCurveChartGenerator(BaseChartGenerator):
    # Percent axes carry long labels — shrink them from the
    # base class's 24
    x_label_fontsize = 20
    y_label_fontsize = 20






    ############################################################
    # __init__
    ############################################################
    #
    # Stores the datasets and chart texts. Everything is
    # optional: generateExampleLorenzCharts constructs with
    # no arguments at all (the example chart synthesizes
    # its own curve). y_data_list is only a placeholder so
    # the attribute exists for inherited code — it stays
    # None (see the class banner GOTCHA).
    #
    # Used by:
    #   - generateLorenzCharts / generateExampleLorenzCharts
    #     (blnstats/__init__.py)
    ############################################################

    def __init__(self, datasets=None, title=None, x_label=None, y_label=None):
        # Deliberately no super().__init__ — there is no
        # single x/y series here
        self.x_ticks = None

        self.title = title
        self.x_label = x_label
        self.y_label = y_label
        self.datasets = datasets
        self.y_data_list = None






    ############################################################
    # _plot_perfect_equality_line
    ############################################################
    #
    # Draws the dashed 0-100 diagonal and its label. The
    # label angle is computed from the axes' DISPLAY aspect
    # ratio (plt.draw() first forces transforms current) so
    # the text hugs the diagonal even on non-square
    # figures.
    #
    # Used by:
    #   - generate_lorenz_curves /
    #     generate_example_lorenz_curve (below) — called
    #     after tight_layout so the angle matches the final
    #     geometry
    ############################################################

    def _plot_perfect_equality_line(self):
        plt.plot([0, 100], [0, 100], 'k--')

        # Force the plot to update transformations before
        # measuring the axes
        plt.draw()

        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()

        # Axes size in display coordinates (inches)
        bbox = self.ax.get_window_extent().transformed(plt.gcf().dpi_scale_trans.inverted())
        width_display, height_display = bbox.width, bbox.height

        # Data-to-display scaling per axis
        xscale = width_display / (xlim[1] - xlim[0])
        yscale = height_display / (ylim[1] - ylim[0])

        # Angle of the diagonal as actually displayed
        angle_rad = np.arctan2(yscale * (ylim[1] - ylim[0]), xscale * (xlim[1] - xlim[0]))
        angle_deg = np.degrees(angle_rad)

        # Slightly above the line (y=55) so the text does not
        # sit on the dashes
        self.ax.text(50, 55, 'Perfect Equality Line',
                rotation=angle_deg,
                ha='center', va='center',
                transform=self.ax.transData,
                fontsize=15)






    ############################################################
    # generate_lorenz_curves
    ############################################################
    #
    # Renders one Lorenz curve per dataset on percent axes
    # and returns the SVG BytesIO. Plots through the pyplot
    # state machine (plt.plot/plt.legend) rather than
    # self.ax — works only because the figure created here
    # is the current one.
    #
    # Used by:
    #   - generateLorenzCharts (blnstats/__init__.py) —
    #     full and headerless/footerless variants per
    #     figsize
    ############################################################

    def generate_lorenz_curves(self, figsize=None, print_header=True, print_footer=True):
        # STEP 1: set up the figure — LaTeX text rendering,
        # near-zero x margins
        # =================================================
        with plt.rc_context({'text.usetex': True, 'font.family': 'serif'}):

            self.figsize = figsize
            self.fig, self.ax = plt.subplots(figsize=self.figsize)

            self.ax.margins(x=0.01, y=0)


            # STEP 2: optional header title
            # =============================
            if self.title and print_header:
                self.ax.set_title(self.title, fontsize=self.title_fontsize)


            # STEP 3: one curve per dataset
            # =============================
            for data in self.datasets:
                percentiles = data['percentiles']
                cumulative_percentages = data['cumulative_percentages']
                label = data['label']
                plt.plot(percentiles, cumulative_percentages, label=label)


            # STEP 4: fixed 0-100 percent axes, staged then
            # applied
            # =============================================
            self.customize_axes(
                x_label=self.x_label,
                y_label=self.y_label,
                title=self.title,
                x_formatter=PercentFormatter(),
                y_formatter=PercentFormatter(),
                x_lim=(0, 100),
                y_lim=(0, 100),
                grid=True
            )
            self._customize_axes()

            # The small square variant gets a smaller legend so
            # it does not cover the curves
            if(self.figsize == (6, 6)):
                plt.legend(loc='upper left', fontsize=11)
            else:
                plt.legend(loc='upper left', fontsize=self.legend_fontsize)


            # STEP 5: footer strip and layout
            # ===============================
            if print_footer:
                self._add_footer_texts()

            gap_bottom = 0.03 if print_footer else 0.0
            self.fig.tight_layout(rect=[0, gap_bottom, 1, 1])


            # STEP 6: equality diagonal AFTER tight_layout so
            # its label angle matches the final axes geometry
            # ===============================================
            self._plot_perfect_equality_line()


            # STEP 7: serialize to SVG and hand the buffer back
            # =================================================
            self.virtual_file = self.get_virtual_file()

            return self.virtual_file






    ############################################################
    # generate_example_lorenz_curve
    ############################################################
    #
    # Textbook illustration chart: a synthetic Lorenz curve
    # (x/100)^4, hatched A/B areas and a "Gini Coefficient"
    # label — no real data involved.
    #
    # BUG (documented, not fixed): print_header is accepted
    # but never used — unlike the other generators nothing
    # calls ax.set_title here, so the 'Lorenz Curve
    # Example' title staged via customize_axes is never
    # drawn.
    #
    # Used by:
    #   - generateExampleLorenzCharts (blnstats/__init__.py)
    ############################################################

    def generate_example_lorenz_curve(self, figsize=None, print_header=True, print_footer=True):
        # STEP 1: set up the figure — LaTeX text rendering
        # ================================================
        with plt.rc_context({'text.usetex': True, 'font.family': 'serif'}):

            self.figsize = figsize
            self.fig, self.ax = plt.subplots(figsize=self.figsize)


            # STEP 2: synthetic curve — (x/100)^4 bows the
            # example nicely away from the diagonal
            # ============================================
            x_lorenz = np.linspace(0, 100, 100)
            y_lorenz = (x_lorenz / 100) ** 4 * 100
            self.ax.plot(x_lorenz, y_lorenz, label='Lorenz Curve', linewidth=3, color='black')


            # STEP 3: hatched areas — A between the equality
            # line and the curve, B under the curve — plus
            # labels on white patches so hatching stays legible
            # =================================================
            self.ax.fill_between(x_lorenz, y_lorenz, x_lorenz, hatch='///\\\\\\', edgecolor='black', facecolor='white')
            self.ax.text(55, 35, 'Gini Coefficient', ha='center', va='center', fontsize=15,
                    bbox=dict(facecolor='white', alpha=1))
            self.ax.text(85, 70, 'A', ha='center', va='center', fontsize=25, bbox=dict(facecolor='white', alpha=1))

            self.ax.fill_between(x_lorenz, y_lorenz, hatch='++', edgecolor='black', facecolor='white')
            self.ax.text(85, 25, 'B', ha='center', va='center', fontsize=25, bbox=dict(facecolor='white', alpha=1))


            # STEP 4: percent axes; the title staged here is
            # never drawn (see banner)
            # ==============================================
            self.customize_axes(
                x_label='Cumulative Percentage of Population',
                y_label='Cumulative Percentage of Wealth',
                title='Lorenz Curve Example',
                x_formatter=PercentFormatter(),
                y_formatter=PercentFormatter(),
                x_lim=(0, 100),
                y_lim=(0, 100),
                grid=False
            )
            self._customize_axes()
            self.ax.legend(loc='upper left', fontsize=15)


            # STEP 5: footer strip and layout
            # ===============================
            if print_footer:
                self._add_footer_texts()

            gap_bottom = 0.03 if print_footer else 0.0
            self.fig.tight_layout(rect=[0, gap_bottom, 1, 1])


            # STEP 6: equality diagonal AFTER tight_layout so
            # its label angle matches the final axes geometry
            # ===============================================
            self._plot_perfect_equality_line()


            # STEP 7: serialize to SVG and hand the buffer back
            # =================================================
            self.virtual_file = self.get_virtual_file()

            return self.virtual_file
