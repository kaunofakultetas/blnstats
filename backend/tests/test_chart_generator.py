############################################################
#  [*] Chart generator tests — the SVG render path + bugs
#
#  Exercises charts/chart_generator.py without touching the
#  DB: a real LaTeX-rendered SVG for the line chart and the
#  example Lorenz curve (slow — LaTeX runs per chart, only
#  three renders total), the tick-selection and dynamic
#  y-limit logic, and regression guards for the chart bugs
#  found during the restyle — all FIXED: the x_ticks
#  parameter is stored, exclusion-only calls filter the
#  full series, forced endpoint ticks survive exclusion,
#  degenerate y-limits stay finite and ordered, and the
#  example curve draws its title. Title assertions read the
#  matplotlib Axes object, not the SVG — usetex outputs
#  text as paths, so the SVG carries no literal strings.
#
#  Used by:
#    - runTests.sh (repo root) — "python3 -m unittest discover"
#      over tests/test_*.py
############################################################


import unittest
from datetime import datetime
from blnstats.charts.chart_generator import BaseChartGenerator, LorenzCurveChartGenerator


DATES = [datetime(2018, 2, 1), datetime(2018, 3, 1), datetime(2018, 4, 1)]








############################################################
# TestTickSelection
############################################################
#
#   test_ends_with_selects_and_forces_endpoints — the
#     documented selection + forced-extent behavior
#   test_explicit_ticks_win
#   test_customize_axes_x_ticks_stored
#   test_exclude_only_filters_full_series
#   test_exclusion_keeps_forced_endpoints
############################################################

class TestTickSelection(unittest.TestCase):






    ############################################################
    # setUp
    ############################################################
    #
    # One three-point date series — enough for selection,
    # forcing and exclusion to all differ.
    #
    # Used by:
    #   - the unittest runner, before every test method
    ############################################################

    def setUp(self):
        self.gen = BaseChartGenerator(DATES, [[1, 2, 3]], ['series'])






    ############################################################
    # test_ends_with_selects_and_forces_endpoints
    ############################################################
    #
    # Proves: ends_with keeps matching dates and the first and
    # last data points are forced in so the axis shows its
    # true extent.
    ############################################################

    def test_ends_with_selects_and_forces_endpoints(self):
        self.gen.set_x_ticks(ends_with='-03-01')
        self.assertEqual(self.gen.x_ticks, DATES)  # match + both forced endpoints






    ############################################################
    # test_explicit_ticks_win
    ############################################################
    #
    # Proves: an explicit x_ticks list overrides ends_with and
    # is used verbatim (no endpoint forcing).
    ############################################################

    def test_explicit_ticks_win(self):
        self.gen.set_x_ticks(ends_with='-03-01', x_ticks=[DATES[1]])
        self.assertEqual(self.gen.x_ticks, [DATES[1]])






    ############################################################
    # test_customize_axes_x_ticks_stored
    ############################################################
    #
    # Proves: x_ticks passed to customize_axes is stored like
    # every other parameter of that method (it used to be
    # silently dropped).
    ############################################################

    def test_customize_axes_x_ticks_stored(self):
        self.gen.customize_axes('X', 'Y', x_ticks=[DATES[1]])
        self.assertEqual(self.gen.x_ticks, [DATES[1]])






    ############################################################
    # test_exclude_only_filters_full_series
    ############################################################
    #
    # Proves: exclusion without a prior selection acts on the
    # full date series (it used to die on a bare TypeError
    # iterating x_ticks = None).
    ############################################################

    def test_exclude_only_filters_full_series(self):
        self.gen.set_x_ticks(exclude_ends_with=['-02-01'])
        self.assertEqual(self.gen.x_ticks, [DATES[1], DATES[2]])






    ############################################################
    # test_exclusion_keeps_forced_endpoints
    ############################################################
    #
    # Proves: the first/last data points are forced in AFTER
    # the exclusion pass, so the axis always shows its true
    # extent. This fires in production —
    # generateCoefficientsOnSingleChart excludes '-02-01'
    # while its series starts 2018-02-01, and that start label
    # used to vanish from every published chart.
    ############################################################

    def test_exclusion_keeps_forced_endpoints(self):
        self.gen.set_x_ticks(ends_with='-03-01', exclude_ends_with=['-02-01'])
        self.assertEqual(self.gen.x_ticks, DATES)  # match + both endpoints back in








############################################################
# TestDynamicYLimits
############################################################
#
#   test_known_padding          — 2% below, 25% headroom,
#                                 near-zero floor snaps to 0
#   test_explicit_limit_wins
#   test_empty_data_is_finite         — the (0, 1) fallback
#   test_negative_data_limits_ordered — no zero snap below 0
############################################################

class TestDynamicYLimits(unittest.TestCase):






    ############################################################
    # setUp
    ############################################################
    #
    # Generator whose data the individual tests override via
    # direct _find_y_lim_dynamically calls.
    #
    # Used by:
    #   - the unittest runner, before every test method
    ############################################################

    def setUp(self):
        self.gen = BaseChartGenerator(DATES, [[0, 5, 10]], ['series'])






    ############################################################
    # test_known_padding
    ############################################################
    #
    # Proves: [0,10] pads to max 12.5 (25% headroom for the
    # legend) and the min, 2% below zero, snaps to exactly 0
    # (the near-zero floor rule).
    ############################################################

    def test_known_padding(self):
        low, high = self.gen._find_y_lim_dynamically([[0, 10]])
        self.assertEqual(low, 0)
        self.assertAlmostEqual(high, 12.5, places=12)






    ############################################################
    # test_explicit_limit_wins
    ############################################################
    #
    # Proves: an explicit y_lim passes through customize_axes
    # untouched — no padding applied.
    ############################################################

    def test_explicit_limit_wins(self):
        self.gen.customize_axes('X', 'Y', y_lim=(3, 7))
        self.assertEqual(self.gen.y_lim, (3, 7))






    ############################################################
    # test_empty_data_is_finite
    ############################################################
    #
    # Proves: no data yields the neutral (0, 1) default
    # instead of (inf, -inf) and a broken matplotlib axis.
    ############################################################

    def test_empty_data_is_finite(self):
        self.assertEqual(self.gen._find_y_lim_dynamically([]), (0, 1))
        self.assertEqual(self.gen._find_y_lim_dynamically(None), (0, 1))






    ############################################################
    # test_negative_data_limits_ordered
    ############################################################
    #
    # Proves: limits satisfy low <= high for ANY input — the
    # near-zero floor snap only applies when the chart rises
    # above zero, so an all-negative series keeps its padded
    # ordered limits instead of inverting the axis.
    ############################################################

    def test_negative_data_limits_ordered(self):
        low, high = self.gen._find_y_lim_dynamically([[-10, -5]])
        self.assertLessEqual(low, high)
        self.assertAlmostEqual(low, -10.1, places=12)
        self.assertAlmostEqual(high, -3.75, places=12)








############################################################
# TestRenderPath
############################################################
#
# Real renders through LaTeX — kept to three total.
#
#   test_line_chart_renders    — SVG bytes + title + legend
#   test_line_chart_no_header  — title suppressed
#   test_example_lorenz_title  — title drawn when the
#                                header is on
############################################################

class TestRenderPath(unittest.TestCase):






    ############################################################
    # test_line_chart_renders
    ############################################################
    #
    # Proves: the full staging -> render -> SVG path works —
    # the buffer is real SVG, the header title is applied, and
    # the legend carries the series label.
    ############################################################

    def test_line_chart_renders(self):
        gen = BaseChartGenerator(DATES, [[1, 2, 3]], ['channels'])
        gen.customize_axes('Date', 'Count', title='Test Chart')
        gen.set_x_ticks(ends_with='-01')
        buffer = gen.generate_line_chart(figsize=(6, 6))

        self.assertTrue(buffer.getvalue().lstrip().startswith(b'<?xml') or b'<svg' in buffer.getvalue()[:400])
        self.assertEqual(gen.ax.get_title(), 'Test Chart')
        legend_texts = [t.get_text() for t in gen.ax.get_legend().get_texts()]
        self.assertEqual(legend_texts, ['channels'])






    ############################################################
    # test_line_chart_no_header
    ############################################################
    #
    # Proves: print_header=False suppresses the title (the
    # embed variant the flows render).
    ############################################################

    def test_line_chart_no_header(self):
        gen = BaseChartGenerator(DATES, [[1, 2, 3]], ['channels'])
        gen.customize_axes('Date', 'Count', title='Test Chart')
        gen.set_x_ticks(ends_with='-01')
        gen.generate_line_chart(figsize=(6, 6), print_header=False)
        self.assertEqual(gen.ax.get_title(), '')






    ############################################################
    # test_example_lorenz_title
    ############################################################
    #
    # Proves: the example Lorenz curve draws its staged
    # 'Lorenz Curve Example' title when print_header is on —
    # the same header contract as the other generators (the
    # published example SVG used to ship untitled).
    ############################################################

    def test_example_lorenz_title(self):
        gen = LorenzCurveChartGenerator()
        buffer = gen.generate_example_lorenz_curve(figsize=(6, 6), print_header=True)
        self.assertGreater(len(buffer.getvalue()), 0)
        self.assertEqual(gen.ax.get_title(), 'Lorenz Curve Example')








if __name__ == '__main__':
    unittest.main()
