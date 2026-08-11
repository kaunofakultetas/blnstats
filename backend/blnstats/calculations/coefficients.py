############################################################
#  [*] Coefficients — BLN (de)centralization metrics
#
#  Pure-math layer of the stats pipeline. The chart/JSON
#  flows in blnstats/__init__.py feed block-height
#  snapshots in (VerticesAspectDataStructure — node/entity
#  capacities or channel counts selected by
#  NodeMetricsSelector / EntityMetricsSelector) and get a
#  CoefficientsDataStructure back (data_types.py), which
#  they save under /DATA/GENERATED/ and hand on to
#  charts/chart_generator.py.
#
#  Every metric takes a list of non-negative values (one
#  weight per node/entity); each method banner states the
#  formula, value range and edge-case conventions.
#  Unit tests: backend/tests/test_coefficients.py.
############################################################


import numpy as np
import math
from datetime import datetime
from ..data_types import VerticesAspectDataStructure, CoefficientsDataStructure








############################################################
# Coefficients
############################################################
#
# Stateless calculator for concentration/inequality
# metrics over one snapshot of node or entity weights:
#
#   Gini                     0 decentralized .. 1 central.
#   HHI                      0 .. 10000
#   Theil / NormalizedTheil  0 .. ln(n)  /  0 .. 1
#   ShannonEntropy (+ norm.) 0 centralized .. log2(n) / 1
#                            — direction OPPOSITE to the
#                            metrics above
#   Nakamoto                 min holders reaching 51%
#   Top10PercentControl...   share / raw sum of the top 10%
#
# calculate_coefficient dispatches by name; details live
# in the method banners below.
#
# Used by:
#   - generateCoefficientCharts,
#     generateOverlappingCoefficientCharts,
#     generateCoefficientsOnSingleChart,
#     generateLorenzCharts (blnstats/__init__.py) — all
#     through calculate_on_vertices_data
#   - tests/test_coefficients.py — direct method calls
############################################################

class Coefficients:






    ############################################################
    # calculate_gini
    ############################################################
    #
    # Gini via the sorted-index identity:
    #   G = sum_i((2i - n - 1) * x_(i)) / (n * sum(x)),
    # x sorted ascending, i = 1..n. 0 means a perfectly
    # even split; the maximum (n-1)/n approaches 1 when one
    # holder has everything. Empty and all-zero input
    # return 0.0 by convention (Gini is undefined there);
    # negatives raise ValueError.
    #
    # Used by:
    #   - calculate_coefficient (below, "Gini")
    #   - tests/test_coefficients.py
    ############################################################

    def calculate_gini(self, data: list) -> float:
        n = len(data)
        if n == 0:
            return 0.0

        data = np.array(data, dtype=np.float64)
        if np.any(data < 0):
            raise ValueError("All data values must be non-negative.")

        sorted_data = np.sort(data)
        sum_data = np.sum(sorted_data)
        if sum_data == 0:
            return 0.0

        index = np.arange(1, n + 1)
        gini_numerator = np.sum((2 * index - n - 1) * sorted_data)
        gini_denominator = n * sum_data
        gini = gini_numerator / gini_denominator
        return gini






    ############################################################
    # calculate_hhi
    ############################################################
    #
    # Herfindahl-Hirschman Index on the market-share scale:
    #   HHI = 10000 * sum_i((x_i / total)^2).
    # 10000/n for a uniform split, 10000 for a monopoly.
    # Zero total returns 0.0; negatives raise ValueError.
    #
    # Used by:
    #   - calculate_coefficient (below, "HHI")
    #   - tests/test_coefficients.py
    ############################################################

    def calculate_hhi(self, data: list) -> float:
        total = sum(data)
        if total == 0:
            return 0.0

        data = np.array(data, dtype=np.float64)
        if np.any(data < 0):
            raise ValueError("All data values must be non-negative.")

        shares = data / total
        hhi = np.sum(shares ** 2) * 10000
        return hhi






    ############################################################
    # calculate_theil_index
    ############################################################
    #
    # Theil T index in share form:
    #   T = sum_i(s_i * ln(s_i * n)),  s_i = x_i / total,
    # with n the FULL entry count (zeros included). 0 for a
    # uniform split, ln(n) when one holder has everything.
    # Zero shares are dropped before the log — their
    # contribution tends to 0 anyway and it keeps log() off
    # zero. Empty or zero-total input returns 0.0;
    # negatives raise ValueError.
    #
    # Used by:
    #   - calculate_normalized_theil_index (below)
    #   - calculate_coefficient (below, "Theil")
    #   - tests/test_coefficients.py
    ############################################################

    def calculate_theil_index(self, data: list) -> float:
        n = len(data)
        total = sum(data)
        if n == 0 or total == 0:
            return 0.0

        data = np.array(data, dtype=np.float64)
        if np.any(data < 0):
            raise ValueError("All data values must be non-negative.")

        shares = data / total
        shares = shares[shares > 0]

        theil = np.sum(shares * np.log(shares * n))
        return theil






    ############################################################
    # calculate_max_theil_index
    ############################################################
    #
    # Upper bound of Theil T for n holders: ln(n), reached
    # when one holder has everything. n <= 1 returns 0.0 —
    # a single holder has no inequality to measure.
    #
    # Used by:
    #   - calculate_normalized_theil_index (below)
    #   - tests/test_coefficients.py
    ############################################################

    def calculate_max_theil_index(self, n: int) -> float:
        if n <= 1:
            return 0.0
        return math.log(n)






    ############################################################
    # calculate_normalized_theil_index
    ############################################################
    #
    # T / ln(n): rescales Theil to 0 (decentralized) .. 1
    # (centralized) so snapshots of different sizes
    # compare. n counts ALL entries including zero-valued
    # ones — consistent with calculate_theil_index, which
    # uses the unfiltered length inside its log. n <= 1
    # returns 0.0 (max_theil guard).
    #
    # Used by:
    #   - calculate_coefficient (below, "NormalizedTheil")
    #   - tests/test_coefficients.py
    ############################################################

    def calculate_normalized_theil_index(self, data) -> float:
        theil_index = self.calculate_theil_index(data)
        max_theil = self.calculate_max_theil_index(len(data))
        if max_theil == 0:
            return 0.0

        coefficient_value = theil_index / max_theil
        return coefficient_value






    ############################################################
    # calculate_shannon_entropy
    ############################################################
    #
    # Shannon entropy in bits over the share distribution:
    #   H = -sum_i(s_i * log2(s_i)),  s_i = x_i / total.
    # 0 when one holder has everything (centralized),
    # log2(n) for a uniform split — the direction is
    # OPPOSITE to Gini/HHI/Theil. Zero shares are dropped
    # (log2(0) guard); zero total returns 0.0; negatives
    # raise ValueError.
    #
    # Used by:
    #   - calculate_normalized_shannon_entropy (below)
    #   - calculate_coefficient (below, "ShannonEntropy")
    #   - tests/test_coefficients.py
    ############################################################

    def calculate_shannon_entropy(self, data) -> float:
        total = sum(data)
        if total == 0:
            return 0.0

        data = np.array(data, dtype=np.float64)
        if np.any(data < 0):
            raise ValueError("All data values must be non-negative.")

        shares = data / total
        shares = shares[shares > 0]

        entropy = -np.sum(shares * np.log2(shares))
        return entropy






    ############################################################
    # calculate_max_shannon_entropy
    ############################################################
    #
    # Upper bound of H for n holders: log2(n), reached on a
    # perfectly uniform split. n <= 1 returns 0.0.
    #
    # Used by:
    #   - calculate_normalized_shannon_entropy (below)
    #   - tests/test_coefficients.py
    ############################################################

    def calculate_max_shannon_entropy(self, n) -> float:
        if n <= 1:
            return 0.0
        return math.log2(n)






    ############################################################
    # calculate_normalized_shannon_entropy
    ############################################################
    #
    # H / log2(n), rescaled to 0 (centralized) .. 1
    # (perfectly even). n counts ALL entries including
    # zero-valued ones; n <= 1 returns 0.0 (max_entropy
    # guard).
    #
    # Used by:
    #   - calculate_coefficient (below,
    #     "NormalizedShannonEntropy")
    #   - tests/test_coefficients.py
    ############################################################

    def calculate_normalized_shannon_entropy(self, data) -> float:
        shannon_entropy = self.calculate_shannon_entropy(data)
        max_entropy = self.calculate_max_shannon_entropy(len(data))
        if max_entropy == 0:
            return 0.0

        coefficient_value = shannon_entropy / max_entropy
        return coefficient_value






    ############################################################
    # calculate_nakamoto
    ############################################################
    #
    # Nakamoto coefficient: the smallest k such that the k
    # largest holders together reach the 51% threshold —
    # searchsorted(cumsum(descending shares), 0.51) + 1.
    #
    # NOTE (definition quirk, documented not fixed): the
    # textbook definition is "strictly more than 50%"; the
    # fixed 0.51 cutoff overcounts by one when the top k
    # hold between 50% and 51%. Zero total returns 0 even
    # though 1 is the documented minimum (undefined case).
    # Negatives raise ValueError.
    #
    # Used by:
    #   - calculate_coefficient (below, "Nakamoto")
    #   - tests/test_coefficients.py
    ############################################################

    def calculate_nakamoto(self, data) -> int:
        data = np.array(data, dtype=np.float64)
        if np.any(data < 0):
            raise ValueError("All data values must be non-negative.")

        total = np.sum(data)
        if total == 0:
            return 0

        sorted_data = np.sort(data)[::-1]
        cumulative_share = np.cumsum(sorted_data) / total

        # searchsorted finds the first index whose cumulative
        # share reaches 0.51; +1 turns the index into a count
        nodes_needed = np.searchsorted(cumulative_share, 0.51) + 1
        return nodes_needed






    ############################################################
    # calculate_top_10_percent_control_percentage
    ############################################################
    #
    # Share of the total held by the top 10% of holders:
    # sort descending, take the first floor(n * 0.1)
    # entries (never fewer than one — for n < 10 the top
    # decile IS the single largest holder), divide their
    # sum by the grand total. Despite the name it returns a
    # FRACTION in [0, 1], not 0-100. Empty or all-zero
    # input returns 0.0, the same degenerate convention as
    # every other metric. For n >= 10 the floor cut is
    # unchanged, so historical series keep their values.
    #
    # Used by:
    #   - calculate_coefficient (below,
    #     "Top10PercentControlPercentage")
    #   - tests/test_scientific_coefficients.py
    ############################################################

    def calculate_top_10_percent_control_percentage(self, data) -> float:
        data = np.array(data, dtype=np.float64)
        if np.any(data < 0):
            raise ValueError("All data values must be non-negative.")

        # degenerate convention shared with the other metrics —
        # and the guard that used to be missing (0/0 -> nan)
        if len(data) == 0 or np.sum(data) == 0:
            return 0.0

        sorted_data = np.sort(data)[::-1]
        ten_percent_index = max(1, int(0.1 * len(sorted_data)))
        return np.sum(sorted_data[:ten_percent_index]) / np.sum(sorted_data)






    ############################################################
    # calculate_top_10_percent_control_sum
    ############################################################
    #
    # Raw sum of the values held by the top 10% of holders
    # — same never-fewer-than-one decile cut as the
    # percentage variant. The unit is whatever the input
    # carries: satoshis for capacity, channels for degree.
    #
    # Used by:
    #   - calculate_coefficient (below,
    #     "Top10PercentControlSum")
    #   - tests/test_scientific_coefficients.py
    ############################################################

    def calculate_top_10_percent_control_sum(self, data) -> float:
        data = np.array(data, dtype=np.float64)
        if np.any(data < 0):
            raise ValueError("All data values must be non-negative.")

        sorted_data = np.sort(data)[::-1]
        # empty input: the [:1] slice of an empty array sums to 0.0
        ten_percent_index = max(1, int(0.1 * len(sorted_data)))
        return np.sum(sorted_data[:ten_percent_index])






    ############################################################
    # calculate_coefficient
    ############################################################
    #
    # Name -> method dispatcher. The names are the
    # UI-facing coefficient types with spaces stripped
    # (callers do coefficientType.replace(" ", "")):
    # "Gini", "HHI", "Theil", "NormalizedTheil",
    # "ShannonEntropy", "NormalizedShannonEntropy",
    # "Nakamoto", "Top10PercentControlPercentage",
    # "Top10PercentControlSum" — anything else raises
    # ValueError.
    #
    # Used by:
    #   - calculate_on_vertices_data (below) — once per
    #     block height
    ############################################################

    def calculate_coefficient(self, values: list, coefficient_type: str) -> float:
        if coefficient_type == "Gini":
            return self.calculate_gini(values)
        elif coefficient_type == "HHI":
            return self.calculate_hhi(values)
        elif coefficient_type == "Theil":
            return self.calculate_theil_index(values)
        elif coefficient_type == "NormalizedTheil":
            return self.calculate_normalized_theil_index(values)
        elif coefficient_type == "ShannonEntropy":
            return self.calculate_shannon_entropy(values)
        elif coefficient_type == "NormalizedShannonEntropy":
            return self.calculate_normalized_shannon_entropy(values)
        elif coefficient_type == "Nakamoto":
            return self.calculate_nakamoto(values)
        elif coefficient_type == "Top10PercentControlPercentage":
            return self.calculate_top_10_percent_control_percentage(values)
        elif coefficient_type == "Top10PercentControlSum":
            return self.calculate_top_10_percent_control_sum(values)
        else:
            raise ValueError(f"Invalid coefficient type: {coefficient_type}")






    ############################################################
    # calculate_on_vertices_data
    ############################################################
    #
    # Runs one coefficient over every block-height snapshot
    # of a VerticesAspectDataStructure and wraps the series
    # in a CoefficientsDataStructure — per height: value,
    # date, timestamp, plus the input length/sum so
    # consumers can judge sample size. The meta description
    # is derived by parsing the input's yAxis label, e.g.
    # "List(NodeID,Capacity)".
    #
    # Used by:
    #   - generateCoefficientCharts,
    #     generateOverlappingCoefficientCharts,
    #     generateCoefficientsOnSingleChart,
    #     generateLorenzCharts (blnstats/__init__.py)
    ############################################################

    def calculate_on_vertices_data(self, vertices_data: VerticesAspectDataStructure, coefficient_type: str) -> CoefficientsDataStructure:
        # STEP 1: run the metric on every block-height snapshot
        # =====================================================
        coefficient_data = {}
        for block_height, vertice_entry in vertices_data.data.items():
            date = vertice_entry.date
            timestamp = vertice_entry.timestamp
            values = [vertice.value for vertice in vertice_entry.vertices]
            coefficient_value = self.calculate_coefficient(values, coefficient_type)
            coefficient_data[block_height] = {
                "value": coefficient_value,
                "date": date,
                "timestamp": timestamp
            }


        # STEP 2: derive the human description from the input's
        # yAxis label — brittle parse assuming the exact shape
        # "List(<subject>,<metric>)"; unmapped names surface as
        # "UNKNOWN ..." in the description instead of failing
        # =====================================================
        input_y_axis = vertices_data.meta.yAxis.split("(")[1].split(")")[0]
        input_subject, input_metric = input_y_axis.split(",")

        SUBJECT_MAPPING = {
            "NodeID": "nodes",
            "EntityName": "entities"
        }
        METRIC_MAPPING = {
            "Capacity": "capacities",
            "ChannelCount": "channel counts"
        }

        subjectOfAnalysis = SUBJECT_MAPPING.get(input_subject, "UNKNOWN SUBJECT")
        analysisMetric = METRIC_MAPPING.get(input_metric, "UNKNOWN METRIC")


        # STEP 3: extend the provenance trail — the input yAxis
        # is appended so consumers see every transformation the
        # series went through
        # =====================================================
        yAxisSupplyChain = vertices_data.meta.yAxisSupplyChain.copy()
        yAxisSupplyChain.append(vertices_data.meta.yAxis)


        # STEP 4: assemble the coefficients structure
        # ===========================================
        return CoefficientsDataStructure(
            meta={
                "type": f"CoefficientsAcrossTheTime({coefficient_type})",
                "description": f"{coefficient_type} Coefficients for {subjectOfAnalysis} {analysisMetric} at given block heights",
                "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "xAxis": "BlockHeight",
                "yAxis": coefficient_type,
                "yAxisSupplyChain": yAxisSupplyChain
            },
            data={block_height: CoefficientsDataStructure.CoefficientData(
                value=coefficient_data[block_height]["value"],
                date=coefficient_data[block_height]["date"],
                timestamp=coefficient_data[block_height]["timestamp"],
                input_array_length=len(vertices_data.data[block_height].vertices),
                input_array_sum=sum([vertice.value for vertice in vertices_data.data[block_height].vertices])
            ) for block_height in coefficient_data.keys()}
        )
