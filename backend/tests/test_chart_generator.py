############################################################
#  [*] Chart generator tests — the SVG render path + bugs
#
#  Exercises charts/chart_generator.py without touching the
#  DB: a real LaTeX-rendered SVG for the line chart and the
#  example Lorenz curve (slow — LaTeX runs per chart, only
#  three renders total), the tick-selection and dynamic
#  y-limit logic, and — under @unittest.expectedFailure —
#  every chart bug found during the restyle: the ignored
#  x_ticks parameter, the exclude-only TypeError, the
#  excluded forced endpoint, the (inf,-inf) empty y-limits,
#  the inverted limits on negative data, and the example
#  curve's never-drawn title. Title assertions read the
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
#   test_customize_axes_x_ticks_ignored   (expectedFailure)
#   test_exclude_only_raises              (expectedFailure)
#   test_exclusion_removes_forced_endpoint(expectedFailure)
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
    # test_customize_axes_x_ticks_ignored
    ############################################################
    #
    # Proves (intended contract): passing x_ticks to
    # customize_axes should set the ticks like every other
    # parameter of that method. Currently the parameter is
    # accepted and silently dropped — only set_x_ticks works.
    ############################################################

    @unittest.expectedFailure
    def test_customize_axes_x_ticks_ignored(self):
        self.gen.customize_axes('X', 'Y', x_ticks=[DATES[1]])
        self.assertEqual(self.gen.x_ticks, [DATES[1]])






    ############################################################
    # test_exclude_only_raises
    ############################################################
    #
    # Proves (intended contract): exclusion without a prior
    # selection should act on the full date series (or fail
    # with a clear message). Currently it iterates
    # self.x_ticks = None and dies with a bare TypeError.
    ############################################################

    @unittest.expectedFailure
    def test_exclude_only_raises(self):
        self.gen.set_x_ticks(exclude_ends_with=['-02-01'])
        self.assertIsNotNone(self.gen.x_ticks)






    ############################################################
    # test_exclusion_removes_forced_endpoint
    ############################################################
    #
    # Proves (intended contract): the forced first/last ticks
    # exist so "the axis always shows its true extent" — the
    # exclusion pass runs afterwards and silently removes them
    # again when they match a pattern. This actually happens
    # in production: generateCoefficientsOnSingleChart
    # excludes '-02-01' while its series starts 2018-02-01.
    # Design call for review: either endpoints survive
    # exclusion, or the forced-extent comment is wrong.
    ############################################################

    @unittest.expectedFailure
    def test_exclusion_removes_forced_endpoint(self):
        self.gen.set_x_ticks(ends_with='-03-01', exclude_ends_with=['-02-01'])
        self.assertIn(DATES[0], self.gen.x_ticks)








############################################################
# TestDynamicYLimits
############################################################
#
#   test_known_padding          — 2% below, 25% headroom,
#                                 near-zero floor snaps to 0
#   test_explicit_limit_wins
#   test_empty_data_is_finite         (expectedFailure)
#   test_negative_data_limits_ordered (expectedFailure)
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
    # Proves (intended contract): no data must still yield
    # FINITE limits — currently returns (inf, -inf), which
    # matplotlib turns into a broken axis. The Lorenz subclass
    # dodges this only by always passing explicit limits.
    ############################################################

    @unittest.expectedFailure
    def test_empty_data_is_finite(self):
        low, high = self.gen._find_y_lim_dynamically([])
        self.assertTrue(low < high)
        self.assertNotEqual(low, float('inf'))






    ############################################################
    # test_negative_data_limits_ordered
    ############################################################
    #
    # Proves (intended contract): limits must satisfy
    # low <= high for ANY input. For all-negative series the
    # near-zero floor snaps the minimum to 0 ABOVE the padded
    # maximum (e.g. [-10,-5] -> (0, -3.75)), inverting the
    # axis. Latent — every current chart series is
    # non-negative.
    ############################################################

    @unittest.expectedFailure
    def test_negative_data_limits_ordered(self):
        low, high = self.gen._find_y_lim_dynamically([[-10, -5]])
        self.assertLessEqual(low, high)








############################################################
# TestRenderPath
############################################################
#
# Real renders through LaTeX — kept to three total.
#
#   test_line_chart_renders    — SVG bytes + title + legend
#   test_line_chart_no_header  — title suppressed
#   test_example_lorenz_title  — staged title never drawn
#                                (expectedFailure)
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
    # Proves (intended contract): the example Lorenz curve
    # stages 'Lorenz Curve Example' via customize_axes and the
    # print_header parameter suggests it should be drawn — but
    # no set_title call ever happens, so the published example
    # SVG has no title. (print_header is also accepted and
    # ignored.)
    ############################################################

    @unittest.expectedFailure
    def test_example_lorenz_title(self):
        gen = LorenzCurveChartGenerator()
        buffer = gen.generate_example_lorenz_curve(figsize=(6, 6), print_header=True)
        self.assertGreater(len(buffer.getvalue()), 0)
        self.assertEqual(gen.ax.get_title(), 'Lorenz Curve Example')








if __name__ == '__main__':
    unittest.main()
