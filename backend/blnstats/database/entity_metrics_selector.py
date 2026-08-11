############################################################
#  [*] Entity metrics selector — per-entity cached metrics
#
#  Rolls the per-node cache _CACHED1_NodeMetrics (built
#  by data_transform/node_metrics.py) up to entity level
#  via the NodeID → EntityName map in Lightning_Entities
#  (maintained by data_transform/entity_clusters.py).
#  Results are VerticesAspectDataStructure objects that
#  flow on to the coefficient / Lorenz / CSV pipelines
#  in blnstats/__init__.py.
############################################################


import logging
from datetime import datetime
from ..database.utils import get_db_connection
from ..data_types import VerticesAspectDataStructure, BlockchainBlockHeightsStructure

# NOTE: this module logger is configured but nothing in
# the file ever logs through it.
logger = logging.getLogger(__name__)








############################################################
# EntityMetricsSelector
############################################################
#
# Stateless reader of preprocessed entity metrics:
# channel counts and capacities at given block heights,
# aggregated from the per-node cache. Both methods
# share one shape and the same caveats — spelled out in
# the first method's banner, referenced from the
# second.
############################################################

class EntityMetricsSelector:






    ############################################################
    # get_channel_count_metrics
    ############################################################
    #
    # For each block height in blockHeightsStructure, sums
    # the cached per-node ChannelCount per entity. Returns
    # a VerticesAspectDataStructure: data[str(blockHeight)]
    # = {date, timestamp, vertices: [{name: EntityName,
    # value: summed count}]}. One query per block height
    # (N+1 by design — each is a cheap indexed cache read).
    # Caveats:
    #   - LEFT JOIN + COALESCE: a cached node missing from
    #     Lightning_Entities (entity import lagging the
    #     cache) stands as its own entity under its NodeID
    #     — mirroring the hex-prefix placeholder
    #     entity_clusters would assign it, instead of all
    #     such nodes collapsing into one NULL group.
    #   - counts are endpoint-based: a channel between two
    #     nodes of the SAME entity counts twice for it.
    #   - a block height absent from the cache silently
    #     yields an empty vertices list.
    #
    # Used by (all in blnstats/__init__.py):
    #   - the "Entities" branches of
    #     generateCoefficientCharts,
    #     generateOverlappingCoefficientCharts,
    #     generateCoefficientsOnSingleChart and
    #     generateLorenzCharts
    #   - generateCSV_EntityMetrics
    ############################################################

    def get_channel_count_metrics(self, blockHeightsStructure: BlockchainBlockHeightsStructure):

        blockHeights = list(blockHeightsStructure.data.keys())

        results = VerticesAspectDataStructure(
            meta={
                "type": "VerticesAspectDataStructure",
                "description": "Entities channel counts on given block heights",
                "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "xAxis": "BlockHeight",
                "yAxis": "List(EntityName,ChannelCount)",
                "yAxisSupplyChain": ["BlockHeight"]
            },
            data={}
        )

        with get_db_connection() as db_conn:
            with db_conn.cursor(dictionary=True) as db_cursor:
                for blockHeight in blockHeights:
                    
                    db_cursor.execute('''
                        SELECT
                            COALESCE(Lightning_Entities.EntityName, _CACHED1_NodeMetrics.NodeID) AS EntityName,
                            SUM(_CACHED1_NodeMetrics.ChannelCount) AS ChannelCount
                        FROM
                            _CACHED1_NodeMetrics
                        LEFT JOIN Lightning_Entities
                            ON _CACHED1_NodeMetrics.NodeID = Lightning_Entities.NodeID
                        WHERE
                            BlockHeight = %s
                        GROUP BY COALESCE(Lightning_Entities.EntityName, _CACHED1_NodeMetrics.NodeID)
                    ''',
                        (blockHeight,)
                    )
                    
                    rows = db_cursor.fetchall()
                    vertices = []
                    for row in rows:
                        vertex = VerticesAspectDataStructure.VerticeData(name=row['EntityName'], value=int(row['ChannelCount']))
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
    # Same aggregation as get_channel_count_metrics above,
    # over the cached Capacity column: value is the
    # entity's endpoint-credited capacity in sats (channels
    # between two nodes of the same entity count twice;
    # generateCSV_EntityMetrics divides by 1e8 for BTC).
    # Same N+1 pattern, COALESCE fallback and empty-list
    # behavior as above.
    #
    # Used by (all in blnstats/__init__.py):
    #   - the "Entities" branches of
    #     generateCoefficientCharts,
    #     generateOverlappingCoefficientCharts,
    #     generateCoefficientsOnSingleChart and
    #     generateLorenzCharts
    #   - generateCSV_EntityMetrics
    ############################################################

    def get_capacity_metrics(self, blockHeightsStructure: BlockchainBlockHeightsStructure):

        blockHeights = list(blockHeightsStructure.data.keys())

        results = VerticesAspectDataStructure(
            meta={
                "type": "VerticesAspectDataStructure",
                "description": "Entities capacities on given block heights",
                "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "xAxis": "BlockHeight",
                "yAxis": "List(EntityName,Capacity)",
                "yAxisSupplyChain": ["BlockHeight"]
            },
            data={}
        )
        
        with get_db_connection() as db_conn:
            with db_conn.cursor(dictionary=True) as db_cursor:
                for blockHeight in blockHeights:
                    
                    db_cursor.execute('''
                        SELECT
                            COALESCE(Lightning_Entities.EntityName, _CACHED1_NodeMetrics.NodeID) AS EntityName,
                            SUM(_CACHED1_NodeMetrics.Capacity) AS Capacity
                        FROM
                            _CACHED1_NodeMetrics
                        LEFT JOIN Lightning_Entities
                            ON _CACHED1_NodeMetrics.NodeID = Lightning_Entities.NodeID
                        WHERE
                            BlockHeight = %s
                        GROUP BY COALESCE(Lightning_Entities.EntityName, _CACHED1_NodeMetrics.NodeID)
                    ''',
                        (blockHeight,)
                    )
                    
                    rows = db_cursor.fetchall()
                    vertices = []
                    for row in rows:
                        vertex = VerticesAspectDataStructure.VerticeData(name=row['EntityName'], value=int(row['Capacity']))
                        vertices.append(vertex)
                    
                    results.data[str(blockHeight)] = VerticesAspectDataStructure.VerticeEntry(
                        date=blockHeightsStructure.data[blockHeight].date,
                        timestamp=blockHeightsStructure.data[blockHeight].timestamp,
                        vertices=vertices
                    )
        
        return results
