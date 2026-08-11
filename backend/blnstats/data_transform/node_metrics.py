############################################################
#  [*] Node metrics cache — _CACHED1_NodeMetrics builder
#
#  Precomputes per-node capacity and channel count for the
#  first block of every month and stores them in
#  _CACHED1_NodeMetrics, so the chart and coefficient code
#  never re-aggregates raw channel data. Read downstream by
#  NodeMetricsSelector and EntityMetricsSelector.
############################################################


import logging
from ..database.utils import get_db_connection
from ..database.raw_data_selector import RawDataSelector

logger = logging.getLogger(__name__)









############################################################
# NodeMetrics
############################################################
#
# Creates the cache table on construction, then rebuilds it
# height by height — delete-then-insert per BlockHeight, so
# a re-run refreshes a month instead of duplicating it.
#
# Used by:
#   - transformNodeMetrics (blnstats/__init__.py) — the
#     entrypoint behind main.py --calculate-ln-stats and
#     the Prefect task transform_node_metrics in
#     workflows.py
############################################################

class NodeMetrics:






    ############################################################
    # __init__
    ############################################################
    #
    # Ensures _CACHED1_NodeMetrics exists and wires up the
    # RawDataSelector both transforms read from.
    #
    # Used by:
    #   - transformNodeMetrics (blnstats/__init__.py)
    ############################################################

    def __init__(self):
        with get_db_connection() as db_conn:
            with db_conn.cursor() as db_cursor:
                db_cursor.execute('''
                    CREATE TABLE IF NOT EXISTS `_CACHED1_NodeMetrics` (
                        `BlockHeight` INTEGER NOT NULL,
                        `NodeID` VARCHAR(66) NOT NULL,
                        `ChannelCount` INTEGER NOT NULL,
                        `Capacity` BIGINT NOT NULL,
                        PRIMARY KEY (`BlockHeight`, `NodeID`),
                        INDEX idx_blockheight (`BlockHeight`),
                        INDEX idx_nodeid (`NodeID`)
                    );
                ''')
        self.raw_data_selector = RawDataSelector()
        logger.info("NodeMetrics table initialized.")






    ############################################################
    # transformForBlockHeight
    ############################################################
    #
    # Rebuilds the cache rows for one block height: pulls
    # per-node capacities and channel counts from the raw
    # data, full-outer-joins them in Python (a node missing
    # from either side gets 0 there), then replaces that
    # height's rows. Inserts run in 10000-row batches with a
    # commit after each, so a crash mid-insert leaves the
    # height partially written — harmless, because the next
    # run's DELETE clears it first.
    #
    # Used by:
    #   - transformForFirstBlocksOfMonths (below) — once per
    #     month's first block
    ############################################################

    def transformForBlockHeight(self, blockHeight):
        blockHeight = int(blockHeight)
        logger.info(f"Processing BlockHeight: {blockHeight}")


        # STEP 1: pull raw capacities and channel counts
        # ==============================================
        capacities = self.raw_data_selector.get_ln_nodes_capacities(blockHeight)

        channel_counts = self.raw_data_selector.get_ln_nodes_channel_counts(blockHeight)


        # STEP 2: merge into one record per node — missing
        # side defaults to 0
        # ================================================
        node_metrics = {}

        for cap in capacities:
            NodeID = cap['NodeID']
            NodeValue = int(cap['NodeValue'])
            node_metrics[NodeID] = {'Capacity': NodeValue}

        for cnt in channel_counts:
            NodeID = cnt['NodeID']
            ChannelCount = int(cnt['ChannelCount'])
            if NodeID in node_metrics:
                node_metrics[NodeID]['ChannelCount'] = ChannelCount
            else:
                node_metrics[NodeID] = {'ChannelCount': ChannelCount, 'Capacity': 0}

        # only ChannelCount can still be missing (capacity-only nodes) — the
        # Capacity setdefault is dead code, every entry gets Capacity at creation
        for NodeID, metrics in node_metrics.items():
            metrics.setdefault('ChannelCount', 0)
            metrics.setdefault('Capacity', 0)


        # STEP 3: replace this height's rows in the cache
        # ===============================================
        with get_db_connection() as db_conn:
            with db_conn.cursor() as db_cursor:

                db_cursor.execute('''
                    DELETE FROM `_CACHED1_NodeMetrics` WHERE `BlockHeight` = %s
                ''', (blockHeight,))
                db_conn.commit()

                data_to_insert = []
                for NodeID, metrics in node_metrics.items():
                    ChannelCount = metrics['ChannelCount']
                    Capacity = metrics['Capacity']
                    data_to_insert.append((blockHeight, NodeID, ChannelCount, Capacity))

                # batched so a month with hundreds of thousands of nodes
                # never builds one giant statement
                batch_size = 10000
                for i in range(0, len(data_to_insert), batch_size):
                    batch = data_to_insert[i:i + batch_size]
                    db_cursor.executemany('''
                        INSERT INTO `_CACHED1_NodeMetrics` (`BlockHeight`, `NodeID`, `ChannelCount`, `Capacity`)
                        VALUES (%s, %s, %s, %s)
                    ''', batch)
                    db_conn.commit()

        logger.info(f"Successfully processed BlockHeight: {blockHeight}")






    ############################################################
    # transformForFirstBlocksOfMonths
    ############################################################
    #
    # Refreshes the cache for the first block of every month
    # on record — the whole-history rebuild the monthly
    # stats run performs.
    #
    # Used by:
    #   - transformNodeMetrics (blnstats/__init__.py) — via
    #     main.py --calculate-ln-stats and the Prefect task
    #     transform_node_metrics in workflows.py
    ############################################################

    def transformForFirstBlocksOfMonths(self):
        first_blocks = self.raw_data_selector.get_first_blocks_of_months(withMeta=False)
        if not first_blocks:
            logger.warning("No first blocks found. Ensure the Blockchain_Blocks table is populated.")
            return

        for blockHeight in first_blocks:
            self.transformForBlockHeight(blockHeight)
