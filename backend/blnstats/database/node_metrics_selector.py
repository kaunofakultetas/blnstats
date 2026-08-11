############################################################
#  [*] Node metrics selector — per-node cached metrics
#
#  Straight reads of the _CACHED1_NodeMetrics cache
#  table built by data_transform/node_metrics.py from
#  the raw aggregations in raw_data_selector.py — no
#  joins, the cache already holds one row per
#  (BlockHeight, NodeID). Results are
#  VerticesAspectDataStructure objects that flow on to
#  the coefficient / Lorenz / general-stats pipelines in
#  blnstats/__init__.py.
############################################################


import logging
from datetime import datetime
from ..database.utils import get_db_connection
from ..data_types import VerticesAspectDataStructure, BlockchainBlockHeightsStructure

# NOTE: this module logger is configured but nothing in
# the file ever logs through it.
logger = logging.getLogger(__name__)








############################################################
# NodeMetricsSelector
############################################################
#
# Stateless reader of preprocessed per-node metrics:
# channel counts and capacities at given block heights.
# Both methods share one shape and the same caveats —
# spelled out in the first method's banner; only the
# selected column differs.
############################################################

class NodeMetricsSelector:






    ############################################################
    # get_channel_count_metrics
    ############################################################
    #
    # For each block height in blockHeightsStructure, reads
    # the cached per-node channel counts. Returns a
    # VerticesAspectDataStructure: data[str(blockHeight)] =
    # {date, timestamp, vertices: [{name: NodeID, value:
    # ChannelCount}]}. One query per block height (N+1 by
    # design — each is a cheap indexed cache read).
    # Caveats:
    #   - counts are endpoint-based: every channel adds one
    #     to BOTH endpoints, so network totals need
    #     dividing by 2 (GeneralStats.calculate does that)
    #   - a block height absent from the cache silently
    #     yields an empty vertices list, not an error
    #
    # Used by (all in blnstats/__init__.py):
    #   - the "Nodes" branches of generateCoefficientCharts,
    #     generateOverlappingCoefficientCharts,
    #     generateCoefficientsOnSingleChart and
    #     generateLorenzCharts
    #   - generateGeneralStatisticsCharts
    ############################################################

    def get_channel_count_metrics(self, blockHeightsStructure: BlockchainBlockHeightsStructure):

        blockHeights = list(blockHeightsStructure.data.keys())

        results = VerticesAspectDataStructure(
            meta={
                "type": "VerticesAspectDataStructure",
                "description": "Nodes channel counts on given block heights",
                "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "xAxis": "BlockHeight",
                "yAxis": "List(NodeID,ChannelCount)",
                "yAxisSupplyChain": ["BlockHeight"]
            },
            data={}
        )

        with get_db_connection() as db_conn:
            with db_conn.cursor(dictionary=True) as db_cursor:
                for blockHeight in blockHeights:
                    
                    db_cursor.execute(
                        'SELECT NodeID, ChannelCount FROM _CACHED1_NodeMetrics WHERE BlockHeight = %s',
                        (blockHeight,)
                    )
                    
                    rows = db_cursor.fetchall()
                    vertices = []
                    for row in rows:
                        vertex = VerticesAspectDataStructure.VerticeData(name=row['NodeID'], value=int(row['ChannelCount']))
                        vertices.append(vertex)
                    
                    # str() is a no-op — the structure's keys
                    # are already strings
                    results.data[str(blockHeight)] = VerticesAspectDataStructure.VerticeEntry(
                        date=blockHeightsStructure.data[blockHeight].date,
                        timestamp=blockHeightsStructure.data[blockHeight].timestamp,
                        vertices=vertices
                    )
        
        return results






    ############################################################
    # get_capacity_metrics
    ############################################################
    #
    # Same read as get_channel_count_metrics above, for the
    # Capacity column: value is the node's
    # endpoint-credited capacity in sats (each channel
    # counted at both ends — GeneralStats.calculate divides
    # by 2 * 1e8 for network BTC totals). Same N+1 pattern
    # and empty-list caveat as above.
    #
    # Used by (all in blnstats/__init__.py):
    #   - the "Nodes" branches of generateCoefficientCharts,
    #     generateOverlappingCoefficientCharts,
    #     generateCoefficientsOnSingleChart and
    #     generateLorenzCharts
    #   - generateGeneralStatisticsCharts
    ############################################################

    def get_capacity_metrics(self, blockHeightsStructure: BlockchainBlockHeightsStructure):

        blockHeights = list(blockHeightsStructure.data.keys())

        results = VerticesAspectDataStructure(
            meta={
                "type": "VerticesAspectDataStructure",
                "description": "Nodes capacities on given block heights",
                "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "xAxis": "BlockHeight",
                "yAxis": "List(NodeID,Capacity)",
                "yAxisSupplyChain": ["BlockHeight"]
            },
            data={}
        )
        
        with get_db_connection() as db_conn:
            with db_conn.cursor(dictionary=True) as db_cursor:
                for blockHeight in blockHeights:
                    
                    db_cursor.execute(
                        'SELECT NodeID, Capacity FROM _CACHED1_NodeMetrics WHERE BlockHeight = %s',
                        (blockHeight,)
                    )
                    
                    rows = db_cursor.fetchall()
                    vertices = []
                    for row in rows:
                        vertex = VerticesAspectDataStructure.VerticeData(name=row['NodeID'], value=int(row['Capacity']))
                        vertices.append(vertex)
                    
                    results.data[str(blockHeight)] = VerticesAspectDataStructure.VerticeEntry(
                        date=blockHeightsStructure.data[blockHeight].date,
                        timestamp=blockHeightsStructure.data[blockHeight].timestamp,
                        vertices=vertices
                    )
        
        return results
