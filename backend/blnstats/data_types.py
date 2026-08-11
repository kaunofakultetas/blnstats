############################################################
#  [*] Shared BLN data structures (pydantic models)
#
#  The common currency of the whole pipeline: the selectors
#  in database/ produce these, calculations/coefficients.py
#  and general_stats.py transform them, and the generate*
#  pipelines in blnstats/__init__.py serialize them under
#  /DATA/GENERATED as the JSON/CSV the site serves. Every
#  structure is meta (MetaDataStructure) plus a data dict
#  keyed by str(BlockHeight).
#  NOTE: pydantic is not installed by backend/Dockerfile
#  directly — it arrives transitively with prefect (v2
#  era), and the .json() calls below are the deprecated
#  pydantic-v1 spelling of model_dump_json().
############################################################


from typing import Dict, List
from pydantic import BaseModel
import os
import json
import logging
import csv

# NOTE: this module logger is configured but nothing in
# the file ever logs through it.
logger = logging.getLogger(__name__)








############################################################
# MetaDataStructure
############################################################
#
# The metadata envelope every structure carries: axis
# names, a human description, an 'updated' stamp and the
# provenance chain (yAxisSupplyChain — which aspects fed
# the y values). EVERY field is required: building one
# without 'updated' raises a ValidationError —
# RawDataSelector.get_first_blocks_of_months(withMeta=True)
# trips exactly that (documented there).
#
# Used by:
#   - BaseBLNDataStructure.meta — i.e. every structure
#     below
#   - built by RawDataSelector, both metric selectors,
#     Coefficients.calculate_on_vertices_data and
#     GeneralStats.calculate
############################################################

class MetaDataStructure(BaseModel):
    type: str
    description: str
    updated: str
    xAxis: str
    yAxis: str
    yAxisSupplyChain: List[str]








############################################################
# BaseBLNDataStructure
############################################################
#
# Base of every structure below: pins the meta field and
# carries the serialization helpers. Overall shape:
#   { "meta": {...MetaDataStructure...}, "data": {...} }
# — each subclass declares its own data dict.
############################################################

class BaseBLNDataStructure(BaseModel):
    meta: MetaDataStructure






    ############################################################
    # save_to_file
    ############################################################
    #
    # Pretty-prints the structure as JSON, creating parent
    # directories first. A bare filename would crash —
    # os.makedirs('') raises — but every caller passes
    # absolute /DATA/GENERATED/... paths.
    #
    # Used by (blnstats/__init__.py):
    #   - generateCoefficientCharts, generateLorenzCharts
    #     and generateGeneralStatisticsCharts — metric and
    #     coefficient snapshots under /DATA/GENERATED
    ############################################################

    def save_to_file(self, filePath: str):
        os.makedirs(os.path.dirname(filePath), exist_ok=True)
        with open(filePath, 'w') as file:
            json.dump(json.loads(self.json()), file, indent=4)






    ############################################################
    # to_json_obj
    ############################################################
    #
    # Plain-dict view of the structure via a serialize /
    # parse round-trip of the deprecated .json() API.
    #
    # Used by:
    #   - VerticesAspectDataStructure.save_to_csv (below)
    ############################################################

    def to_json_obj(self):
        return json.loads(self.json())






    ############################################################
    # to_json_str
    ############################################################
    #
    # JSON-string view of the structure. Nothing calls this
    # at the moment.
    ############################################################

    def to_json_str(self):
        return self.json()








############################################################
# BlockchainBlockHeightsStructure
############################################################
#
# The x-axis backbone of every chart: one entry per
# selected block, keyed by str(BlockHeight) and ordered by
# date:
#   data = { "510123": { date: "2018-01-01",
#                        timestamp: 1514764800 }, ... }
# timestamp is typed int but the selector passes str
# values — pydantic coerces them.
#
# Used by:
#   - produced by RawDataSelector.get_first_blocks_of_*
#   - consumed by NodeMetricsSelector and
#     EntityMetricsSelector, which copy date + timestamp
#     into their own results
############################################################

class BlockchainBlockHeightsStructure(BaseBLNDataStructure):

    # One block: mining date + unix timestamp.
    class BlockData(BaseModel):
        date: str
        timestamp: int

    data: Dict[str, BlockData]








############################################################
# VerticesAspectDataStructure
############################################################
#
# One metric for every vertex at each block height — the
# vertex is a node OR an entity, the metric a capacity
# (sats) OR a channel count, depending on which selector
# method produced it (meta.yAxis says which;
# GeneralStats.calculate validates against it):
#   data = { "505000": { date, timestamp, vertices:
#            [ { name, value }, ... ] }, ... }
#
# Used by:
#   - produced by NodeMetricsSelector /
#     EntityMetricsSelector
#   - consumed by Coefficients.calculate_on_vertices_data,
#     GeneralStats.calculate and the Lorenz-curve builder
#     in generateLorenzCharts (blnstats/__init__.py)
############################################################

class VerticesAspectDataStructure(BaseBLNDataStructure):

    # One vertex: NodeID or EntityName + its metric value.
    class VerticeData(BaseModel):
        name: str
        value: int

    # One block height: date/timestamp + all its vertices.
    # The forward-ref string is deliberate — VerticeData is
    # a sibling nested class, not bound yet at parse time.
    class VerticeEntry(BaseModel):
        date: str
        timestamp: int
        vertices: List['VerticesAspectDataStructure.VerticeData']

    data: Dict[str, VerticeEntry]






    ############################################################
    # save_to_csv
    ############################################################
    #
    # Flattens the structure into name,value,date rows —
    # one row per vertex per block height. divideValueBy !=
    # 1.0 turns value into a fixed 8-decimal STRING
    # (callers pass 1e8 to convert sats → BTC); otherwise
    # the raw int is written. Operates on the to_json_obj()
    # copy, so the model itself is never mutated.
    #
    # Used by:
    #   - generateCSV_EntityMetrics (blnstats/__init__.py)
    #     — entity capacity (/1e8) and channel-count CSVs
    ############################################################

    def save_to_csv(self, filePath: str, divideValueBy: float = 1.0):

        jsonObject = self.to_json_obj()

        headers = ['name', 'value', 'date']

        os.makedirs(os.path.dirname(filePath), exist_ok=True)
        with open(filePath, mode='w', newline='', encoding='utf-8') as file:

            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()

            for blockHeight in list(jsonObject['data'].keys()):

                singlePointVerticesObject = jsonObject['data'][blockHeight]

                date = singlePointVerticesObject['date']
                verticesData = singlePointVerticesObject['vertices']

                for vertex in verticesData:
                    # Dead code (kept as-is): the else arm just
                    # reassigns vertex['value'] to itself.
                    if(divideValueBy != 1.0):
                        vertex['value'] = f"{vertex['value'] / divideValueBy:.8f}"
                    else:
                        vertex['value'] = vertex['value']

                    writer.writerow(
                        {
                            'name': vertex['name'],
                            'value': vertex['value'],
                            'date': date
                        }
                    )








############################################################
# CoefficientsDataStructure
############################################################
#
# One concentration-coefficient value (Gini, HHI, Theil,
# Nakamoto, ...) per block height:
#   data = { "505000": { date, timestamp, value,
#            input_array_length, input_array_sum }, ... }
# input_array_length/_sum record the size and total of the
# vertex-value array the coefficient was computed from —
# provenance for sanity-checking published numbers.
#
# Used by:
#   - produced by Coefficients.calculate_on_vertices_data
#     (calculations/coefficients.py)
#   - plotted and saved by the generate* pipelines in
#     blnstats/__init__.py
############################################################

class CoefficientsDataStructure(BaseBLNDataStructure):

    # One point: the coefficient value + its input
    # provenance.
    class CoefficientData(BaseModel):
        date: str
        timestamp: int
        value: float
        input_array_length: int
        input_array_sum: int

    data: Dict[str, CoefficientData]








############################################################
# GeneralStatsDataStructure
############################################################
#
# Network-wide totals per block height:
#   data = { "505000": { date, timestamp, node_count,
#            network_capacity, channel_count }, ... }
# network_capacity is BTC (float): GeneralStats.calculate
# already divided the endpoint-summed sats by 2 * 1e8.
# channel_count arrives as an integral float (sum / 2 —
# each channel was counted at both endpoints) and pydantic
# coerces it to int.
#
# Used by:
#   - produced by GeneralStats.calculate
#     (calculations/general_stats.py)
#   - consumed by generateGeneralStatisticsCharts
#     (blnstats/__init__.py)
############################################################

class GeneralStatsDataStructure(BaseBLNDataStructure):

    # One point: the three network totals for that block.
    # channel_count stays int ON PURPOSE: half a channel is
    # physically impossible (every channel has exactly two
    # endpoints), so GeneralStats.calculate validates the
    # endpoint-sum parity and raises a diagnostic error
    # before a fractional count could ever reach this
    # structure.
    class GeneralStatsData(BaseModel):
        date: str
        timestamp: int
        node_count: int
        network_capacity: float
        channel_count: int

    data: Dict[str, GeneralStatsData]
