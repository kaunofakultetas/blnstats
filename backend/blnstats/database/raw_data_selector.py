############################################################
#  [*] Raw-data selector — first blocks + per-node metrics
#
#  SQL reader for the raw tables the importers fill:
#  Blockchain_Blocks (data_import/blockchain_blocks.py),
#  Lightning_Channels (data_import/lnd_dbreader.py and
#  ln_research.py) and Blockchain_Transactions
#  (data_import/blockchain_transactions.py). Results flow
#  on to data_transform/node_metrics.py — which caches
#  the per-node numbers into _CACHED1_NodeMetrics — and
#  to the chart/CSV pipelines in blnstats/__init__.py.
############################################################


import logging
import json
from datetime import datetime
from ..database.utils import get_db_connection
from ..data_types import MetaDataStructure, BlockchainBlockHeightsStructure, VerticesAspectDataStructure

# NOTE (dead imports, kept as-is): json and
# VerticesAspectDataStructure are never used in this
# module.
logger = logging.getLogger(__name__)








############################################################
# RawDataSelector
############################################################
#
# Stateless reader of the raw blockchain/LN tables:
# date → first-block lookups (the x-axis of every
# chart) and the heavy per-node aggregations the
# _CACHED1_NodeMetrics cache is built from. Methods:
#   - get_first_blocks_of_days_by_date_mask
#   - get_first_blocks_of_months
#   - get_ln_nodes_capacities
#   - get_ln_nodes_channel_counts
############################################################

class RawDataSelector:






    ############################################################
    # get_first_blocks_of_days_by_date_mask
    ############################################################
    #
    # For every Date matching dateMask, returns the LOWEST
    # block height mined on that date. 'X' matches exactly
    # one character ('20XX-XX-01' → every first of a
    # month, '20XX-03-01' → every March 1st). Returns a
    # BlockchainBlockHeightsStructure whose data is keyed
    # by str(BlockHeight) → {date, timestamp}, ordered by
    # date.
    # BUG (documented, not fixed): the dateMask=None
    # default crashes .replace() with AttributeError —
    # every live caller passes a mask.
    #
    # Used by (all in blnstats/__init__.py):
    #   - generateCoefficientCharts
    #   - generateOverlappingCoefficientCharts
    #   - generateCoefficientsOnSingleChart
    #   - generateLorenzCharts
    #   - generateGeneralStatisticsCharts
    #   - generateCSV_EntityMetrics
    ############################################################

    def get_first_blocks_of_days_by_date_mask(self, dateMask=None, startSince='2018-01-01', endUntil='2050-01-01'):

        # 'X' → '_', the single-character wildcard of SQL LIKE
        sql_date_mask = dateMask.replace('X', '_')

        with get_db_connection() as db_conn:
            with db_conn.cursor(dictionary=True) as db_cursor:
                db_cursor.execute('''
                    SELECT 
                        BlockHeight, 
                        Date,
                        Timestamp
                    FROM 
                        Blockchain_Blocks
                    WHERE 
                        (Date, BlockHeight) IN (
                            SELECT 
                                Date, 
                                MIN(BlockHeight) AS BlockHeight
                            FROM 
                                Blockchain_Blocks
                            WHERE 
                                Date >= %s
                                AND Date <= %s
                                AND Date LIKE %s
                            GROUP BY Date
                        )
                    ORDER BY Date;
                ''', [startSince, endUntil, sql_date_mask])
                rows = db_cursor.fetchall()
                
                data = {
                    str(row['BlockHeight']): BlockchainBlockHeightsStructure.BlockData(
                        date=str(row['Date']),
                        timestamp=str(row['Timestamp'])
                    ) for row in rows
                }
                
                meta = MetaDataStructure(
                    type="BlockchainBlockHeights",
                    description=f"First blockchain block heights which have been mined at every date matching {dateMask}",
                    updated=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    xAxis="Date",
                    yAxis="BlockHeight",
                    yAxisSupplyChain=[]
                )
                
                return BlockchainBlockHeightsStructure(meta=meta, data=data)






    ############################################################
    # get_first_blocks_of_months
    ############################################################
    #
    # The MIN(BlockHeight) lookup restricted to
    # DAY(Date)=1 — the first block of every month.
    # withMeta=False returns the bare {str(BlockHeight):
    # BlockData} dict; True wraps it in a
    # BlockchainBlockHeightsStructure.
    # BUG (documented, not fixed): the withMeta=True
    # branch builds MetaDataStructure WITHOUT the required
    # 'updated' field, so it raises a pydantic
    # ValidationError. Harmless today: the only caller
    # passes withMeta=False.
    #
    # Used by:
    #   - NodeMetrics.transformForFirstBlocksOfMonths
    #     (data_transform/node_metrics.py), withMeta=False
    #     — the _CACHED1_NodeMetrics refresh loop
    ############################################################

    def get_first_blocks_of_months(self, withMeta=False, startSince='2018-01-01', endUntil='9999-12-31'):

        with get_db_connection() as db_conn:
            with db_conn.cursor(dictionary=True) as db_cursor:
                db_cursor.execute('''
                    SELECT 
                        BlockHeight, 
                        Date,
                        Timestamp
                    FROM 
                        Blockchain_Blocks
                    WHERE 
                        (Date, BlockHeight) IN (
                            SELECT 
                                Date, 
                                MIN(BlockHeight) AS BlockHeight
                            FROM 
                                Blockchain_Blocks
                            WHERE 
                                DAY(Date) = 1
                                AND Date >= %s
                                AND Date <= %s
                            GROUP BY Date
                        )
                    ORDER BY Date;
                ''', [startSince, endUntil])
                rows = db_cursor.fetchall()
                
                data = {
                    str(row['BlockHeight']): BlockchainBlockHeightsStructure.BlockData(
                        date=str(row['Date']),
                        timestamp=str(row['Timestamp'])
                    ) for row in rows
                }
                
                if withMeta:
                    meta = MetaDataStructure(
                        type="BlockchainBlockHeights",
                        description="First blockchain block heights which have been mined at every month of BLN lifetime",
                        xAxis="Date",
                        yAxis="BlockHeight",
                        yAxisSupplyChain=[]
                    )
                    return BlockchainBlockHeightsStructure(meta=meta, data=data)
                else:
                    return data






    ############################################################
    # get_ln_nodes_capacities
    ############################################################
    #
    # Sums, per node, the funding value (sats) of every
    # channel ACTIVE at blockHeight: FundingBlockIndex <=
    # blockHeight AND SpendingBlockIndex > blockHeight.
    # Channels still unspent carry the 999999999 sentinel
    # written by data_import/blockchain_transactions.py,
    # so open channels always pass the second test. The
    # UNION ALL credits each channel's FULL value to BOTH
    # endpoints — summing the result over all nodes
    # double-counts network capacity
    # (GeneralStats.calculate divides by 2 downstream).
    # Returns a list of {'NodeID', 'NodeValue'} dicts.
    #
    # Used by:
    #   - NodeMetrics.transformForBlockHeight
    #     (data_transform/node_metrics.py) — the
    #     _CACHED1_NodeMetrics cache builder
    ############################################################

    def get_ln_nodes_capacities(self, blockHeight):
        with get_db_connection() as db_conn:
            with db_conn.cursor(dictionary=True) as db_cursor:
                query = '''
                    SELECT NodeID, SUM(Value) AS NodeValue FROM (
                        SELECT LC.NodeID1 AS NodeID, BT.Value AS Value
                        FROM Lightning_Channels LC
                        JOIN Blockchain_Transactions BT
                          ON LC.ShortChannelID = BT.ShortChannelID
                        WHERE BT.FundingBlockIndex <= %s
                          AND BT.SpendingBlockIndex > %s
                        
                        UNION ALL
                        
                        SELECT LC.NodeID2 AS NodeID, BT.Value AS Value
                        FROM Lightning_Channels LC
                        JOIN Blockchain_Transactions BT 
                          ON LC.ShortChannelID = BT.ShortChannelID
                        WHERE BT.FundingBlockIndex <= %s
                          AND BT.SpendingBlockIndex > %s
                    ) AS combined
                    GROUP BY NodeID;
                '''
                logger.debug("Executing LN nodes capacities query for blockHeight: %s", blockHeight)
                # Each UNION arm repeats both WHERE conditions —
                # hence four identical parameters
                db_cursor.execute(query, (blockHeight, blockHeight, blockHeight, blockHeight))
                result = db_cursor.fetchall()
                logger.debug("LN nodes capacities result: %s", result)
                return [{'NodeID': row['NodeID'], 'NodeValue': row['NodeValue']} for row in result]






    ############################################################
    # get_ln_nodes_channel_counts
    ############################################################
    #
    # Counts, per node, the channels ACTIVE at blockHeight
    # — same activity rule and 999999999 sentinel as
    # get_ln_nodes_capacities above. Endpoint counting
    # again: a channel adds one to BOTH endpoints, so the
    # network-wide total is the sum divided by 2. Returns
    # a list of {'NodeID', 'ChannelCount'} dicts.
    #
    # Used by:
    #   - NodeMetrics.transformForBlockHeight
    #     (data_transform/node_metrics.py) — the
    #     _CACHED1_NodeMetrics cache builder
    ############################################################

    def get_ln_nodes_channel_counts(self, blockHeight):
        with get_db_connection() as db_conn:
            with db_conn.cursor(dictionary=True) as db_cursor:
                query = '''
                    SELECT NodeID, COUNT(*) AS ChannelCount FROM (
                        SELECT LC.NodeID1 AS NodeID
                        FROM Lightning_Channels LC
                        JOIN Blockchain_Transactions BT 
                          ON LC.ShortChannelID = BT.ShortChannelID
                        WHERE BT.FundingBlockIndex <= %s
                          AND BT.SpendingBlockIndex > %s
                        
                        UNION ALL
                        
                        SELECT LC.NodeID2 AS NodeID
                        FROM Lightning_Channels LC
                        JOIN Blockchain_Transactions BT 
                          ON LC.ShortChannelID = BT.ShortChannelID
                        WHERE BT.FundingBlockIndex <= %s
                          AND BT.SpendingBlockIndex > %s
                    ) AS combined
                    GROUP BY NodeID;
                '''
                logger.debug("Executing LN nodes channel counts query for blockHeight: %s", blockHeight)
                db_cursor.execute(query, (blockHeight, blockHeight, blockHeight, blockHeight))
                result = db_cursor.fetchall()
                logger.debug("LN nodes channel counts result: %s", result)
                return [{'NodeID': row['NodeID'], 'ChannelCount': row['ChannelCount']} for row in result]
