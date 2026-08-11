############################################################
#  [*] GeneralStats — network totals & channel lifetimes
#
#  Aggregation layer between the metric selectors and the
#  chart flows: generateGeneralStatisticsCharts
#  (blnstats/__init__.py) feeds NodeMetricsSelector
#  capacity/channel-count snapshots into calculate() and
#  charts the result via charts/chart_generator.py; the
#  channel-lifetime methods skip the selectors, query
#  MySQL directly (database/utils.get_db_connection) and
#  write JSON under
#  /DATA/GENERATED/General_Stats/Channel_Lifetime/ for the
#  frontend to serve.
############################################################


from datetime import datetime
from ..data_types import VerticesAspectDataStructure, GeneralStatsDataStructure
from ..database.utils import get_db_connection
import json
import os








############################################################
# GeneralStats
############################################################
#
# Three independent, stateless jobs: per-month network
# totals (calculate), the channel-lifetime histogram
# (calculate_channel_lifetime_plot) and the average
# channel lifetime (calculate_channel_lifetime_average).
#
# Used by:
#   - generateGeneralStatisticsCharts
#     (blnstats/__init__.py) — calculate + the histogram
#   - main.py — flags --calculate-channel-lifetime-plot /
#     --calculate-channel-lifetime-average (hidden: not
#     listed in the usage text)
############################################################

class GeneralStats:






    ############################################################
    # calculate
    ############################################################
    #
    # Merges the parallel capacity and channel-count
    # snapshot series (they must cover the SAME block
    # heights) into one GeneralStatsDataStructure: per
    # height the node count, network capacity in BTC and
    # total channel count.
    #
    # Both sums divide by 2 because every channel is
    # reported at both endpoints; capacity additionally
    # divides by 1e8 (satoshis -> BTC).
    #
    # Used by:
    #   - generateGeneralStatisticsCharts
    #     (blnstats/__init__.py)
    ############################################################

    def calculate(self, vertices_capacity_data: VerticesAspectDataStructure, vertices_channel_count_data: VerticesAspectDataStructure):
        # STEP 1: consistency guard — expected yAxis labels,
        # equal length, same first/last block height. NOTE: a
        # mid-series height mismatch slips through, only the
        # endpoints are compared.
        # ===================================================
        if(vertices_capacity_data.meta.yAxis != "List(NodeID,Capacity)"):
            raise ValueError("VerticesCapacityDataStructure must have a yAxis of 'List(NodeID,Capacity)'")
        if(vertices_channel_count_data.meta.yAxis != "List(NodeID,ChannelCount)"):
            raise ValueError("VerticesChannelCountDataStructure must have a yAxis of 'List(NodeID,ChannelCount)'")
        if(len(vertices_capacity_data.data.values()) != len(vertices_channel_count_data.data.values())):
            raise ValueError("VerticesCapacityDataStructure and VerticesChannelCountDataStructure must have the same length")
        if(list(vertices_capacity_data.data.keys())[0] != list(vertices_channel_count_data.data.keys())[0]):
            raise ValueError("VerticesCapacityDataStructure and VerticesChannelCountDataStructure must start with the same block height")
        if(list(vertices_capacity_data.data.keys())[-1] != list(vertices_channel_count_data.data.keys())[-1]):
            raise ValueError("VerticesCapacityDataStructure and VerticesChannelCountDataStructure must end with the same block height")


        # STEP 2: unzip the per-height series the structure
        # needs
        # =================================================
        block_height_data = [block_height for block_height, vertices in vertices_capacity_data.data.items()]

        date_data = [item.date for item in vertices_capacity_data.data.values()]

        timestamp_data = [item.timestamp for item in vertices_capacity_data.data.values()]

        node_count_data = [len(item.vertices) for item in vertices_capacity_data.data.values()]

        # STEP 2.1: capacity sum — /2 because each channel is
        # reported by both endpoints, /1e8 satoshis -> BTC
        node_capacity_sum_data = [sum(vertice.value / (2 * 100000000) for vertice in vertices_entry.vertices)
                for vertices_entry in vertices_capacity_data.data.values()]

        # STEP 2.2: channel count — /2 for the same
        # both-endpoints double-report reason
        channel_count_sum_data = [sum(vertice.value / 2 for vertice in vertices_entry.vertices)
                for vertices_entry in vertices_channel_count_data.data.values()]


        # STEP 3: assemble the structure
        # ==============================
        general_stats_data = GeneralStatsDataStructure(
            meta={
                "type": "GeneralStatsDataStructure",
                "description": "General stats for the BLN network",
                "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "xAxis": "Date",
                "yAxis": "ChannelCount,NodeCount,NetworkCapacity",
                "yAxisSupplyChain": [
                    "BlockHeight",
                    "List(NodeID,Capacity),List(NodeID,ChannelCount)"
                ]
            },
            data={
                block_height_data[i]: GeneralStatsDataStructure.GeneralStatsData(
                    date=date_data[i],
                    timestamp=timestamp_data[i],
                    node_count=node_count_data[i],
                    network_capacity=node_capacity_sum_data[i],
                    channel_count=channel_count_sum_data[i]
                ) for i in range(len(block_height_data))
            }
        )

        return general_stats_data






    ############################################################
    # calculate_channel_lifetime_plot
    ############################################################
    #
    # Histogram of channel lifetimes in whole days
    # (x: lifetime in days, y: channel count), written to
    # /DATA/GENERATED/General_Stats/Channel_Lifetime/
    # channel_lifetime_plot.json. Lifetimes come from the
    # blockchain funding/spending indexes; still-open
    # channels count up to the current chain tip. Days with
    # zero channels are omitted from the plot data.
    #
    # NOTE: leaves a debug print of the total channel count
    # on stdout (documented, not removed).
    #
    # Used by:
    #   - generateGeneralStatisticsCharts
    #     (blnstats/__init__.py)
    #   - main.py --calculate-channel-lifetime-plot
    ############################################################

    def calculate_channel_lifetime_plot(self):
        # STEP 1: lifetime per channel in blocks —
        # SpendingBlockIndex 999999999 is the "still open"
        # sentinel, resolved to the current chain tip. The
        # WHERE drops same-block closes and inverted
        # funding/spending rows, and its NOT NULL filters turn
        # the LEFT JOIN into an effective inner join.
        # ====================================================
        with get_db_connection() as db_conn:
            with db_conn.cursor(dictionary=True) as db_cursor:
                query = '''
                    SELECT 
                        CASE 
                            WHEN BT.SpendingBlockIndex = 999999999 THEN 
                                (SELECT MAX(BlockHeight) FROM Blockchain_Blocks) - BT.FundingBlockIndex
                            ELSE 
                                BT.SpendingBlockIndex - BT.FundingBlockIndex
                        END AS ChannelLifetime
                    FROM 
                        Lightning_Channels LC
                    LEFT JOIN Blockchain_Transactions BT
                        ON LC.ShortChannelID = BT.ShortChannelID
                    WHERE
                        BT.FundingBlockIndex IS NOT NULL AND 
                        BT.SpendingBlockIndex IS NOT NULL AND
                        (BT.SpendingBlockIndex > BT.FundingBlockIndex OR BT.SpendingBlockIndex = 999999999)
                '''
                db_cursor.execute(query)
                results = db_cursor.fetchall()


                # STEP 2: blocks -> days at Bitcoin's ~144
                # blocks/day cadence
                # ========================================
                blocks_per_day = 144  # Bitcoin's ~10-minute block cadence
                lifetimes_days = [row['ChannelLifetime'] / blocks_per_day for row in results if row['ChannelLifetime'] is not None]


                # STEP 3: bucket by whole days — the imports sit
                # mid-function in the original and a restyle
                # moves no code, so they stay here
                # ==============================================
                from collections import Counter
                import math

                lifetime_counts = Counter(math.floor(lifetime) for lifetime in lifetimes_days if lifetime >= 0)


                # STEP 4: keep only days that actually have
                # channels
                # =========================================
                total_channel_count = 0
                plot_data = {}
                if lifetime_counts:
                    max_lifetime = max(lifetime_counts.keys())
                    for day in range(0, max_lifetime + 1):
                        count = lifetime_counts.get(day, 0)
                        if count > 0:  # zero-channel days are omitted
                            plot_data[day] = {
                                'lifetime_days': day,
                                'channel_count': count
                            }
                            total_channel_count += count

                # Debug print left in (documented, not removed)
                print(total_channel_count)


                # STEP 5: write the plot JSON — total_channels in
                # meta counts every fetched channel, which equals
                # the sum of the per-day buckets
                # ===============================================
                data = {
                    'meta': {
                        'type': 'ChannelLifetimePlot',
                        'description': 'Distribution of Lightning channel lifetimes',
                        'updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'xAxis': 'Channel lifetime (days)',
                        'yAxis': 'Number of channels',
                        'total_channels': len(lifetimes_days)
                    },
                    'data': plot_data
                }
                
                os.makedirs('/DATA/GENERATED/General_Stats/Channel_Lifetime', exist_ok=True)
                with open('/DATA/GENERATED/General_Stats/Channel_Lifetime/channel_lifetime_plot.json', 'w') as f:
                    json.dump(data, f, indent=4)






    ############################################################
    # calculate_channel_lifetime_average
    ############################################################
    #
    # Single-value companion of the histogram: AVG(lifetime
    # in blocks) computed by SQL, written to
    # channel_lifetime_average.json in blocks and days
    # (/144). Returns the raw SQL value — a Decimal, or
    # None on an empty table — even though the JSON payload
    # already coerces to float.
    #
    # NOTE (inconsistency, documented not fixed): this
    # WHERE lacks the histogram query's
    # "Spending > Funding OR sentinel" condition, so
    # same-block and inverted funding/spending rows count
    # here but not in the histogram. Debug print of the
    # average left in.
    #
    # Used by:
    #   - main.py --calculate-channel-lifetime-average
    #     (hidden flag) — nothing else calls this at the
    #     moment
    ############################################################

    def calculate_channel_lifetime_average(self):
        with get_db_connection() as db_conn:
            with db_conn.cursor(dictionary=True) as db_cursor:
                query = '''
                    SELECT 
                        AVG(
                            CASE 
                                WHEN BT.SpendingBlockIndex = 999999999 THEN 
                                    (SELECT MAX(BlockHeight) FROM Blockchain_Blocks) - BT.FundingBlockIndex
                                ELSE 
                                    BT.SpendingBlockIndex - BT.FundingBlockIndex
                            END
                        ) AS AverageChannelLifetime
                    FROM 
                        Lightning_Channels LC
                    LEFT JOIN Blockchain_Transactions BT
                        ON LC.ShortChannelID = BT.ShortChannelID
                    WHERE
                        BT.FundingBlockIndex IS NOT NULL AND 
                        BT.SpendingBlockIndex IS NOT NULL
                '''
                db_cursor.execute(query)
                result = db_cursor.fetchone()
                # Debug print left in (documented, not removed)
                print(result['AverageChannelLifetime'])

                # SQL AVG comes back as Decimal — coerce so
                # json.dump does not choke; empty table -> 0
                avg_lifetime = float(result['AverageChannelLifetime']) if result['AverageChannelLifetime'] is not None else 0

                data = {
                    'meta': {
                        'type': 'ChannelLifetimeAverage',
                        'description': 'Average channel lifetime',
                        'updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'average_channel_lifetime': avg_lifetime
                    },
                    'data': {
                        'average_channel_lifetime_blocks': avg_lifetime,
                        'average_channel_lifetime_days': avg_lifetime / 144
                    }
                }

                os.makedirs('/DATA/GENERATED/General_Stats/Channel_Lifetime', exist_ok=True)
                with open('/DATA/GENERATED/General_Stats/Channel_Lifetime/channel_lifetime_average.json', 'w') as f:
                    json.dump(data, f, indent=4)
                return result['AverageChannelLifetime']
