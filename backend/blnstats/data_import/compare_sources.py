############################################################
#  [*] Compare gossip sources — LN Research vs LND DBReader
#
#  Cross-checks the two channel-announcement sources staged
#  by ln_research.py and lnd_dbreader.py: overall row counts
#  plus their overlap, monthly counts (BlockIndex joined to
#  Blockchain_Blocks for real calendar dates), and a line
#  chart drawn with BaseChartGenerator.
#
#  Results land in /DATA/GENERATED/Compare_Sources/
#  Channel_Announcements/ and are served over /rawdata — the
#  frontend DataSources.jsx reads compare_sources.json and
#  the 20XX-03-01/10x6_Full.svg chart from there.
############################################################


import logging
import json
from ..database.utils import get_db_connection
from ..charts.chart_generator import BaseChartGenerator
from datetime import datetime
import gc
import os


# Module logging setup. Note: `logger` is created but nothing
# in this file logs through it — all progress goes to print()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)








############################################################
# CompareSources
############################################################
#
# Instantiating the class runs the whole comparison — every
# step happens in __init__.
#
# Used by:
#   - blnstats/__init__.py compare_data_sources() — reached
#     from main.py --calculate-ln-stats (CLI) and from the
#     workflows.py task compare_data_sources inside
#     lightning_network_statistics_flow
############################################################

class CompareSources:






    ############################################################
    # __init__
    ############################################################
    #
    # Produces the three outputs in order: overall-count JSON,
    # across-time JSON, comparison chart. xTicksToGenerate is
    # a month-day suffix like '-03-01' choosing which x labels
    # the chart draws; xTicksToExclude lists suffixes to drop
    # (both go straight to BaseChartGenerator.set_x_ticks).
    #
    # Used by:
    #   - blnstats/__init__.py compare_data_sources() — the
    #     only caller; see the class banner for the full chain
    ############################################################

    def __init__(self, xTicksToGenerate, xTicksToExclude):
        # STEP 1: overall totals + overlap → compare_sources.json
        # =======================================================
        general_stats = self.compare_sources(
            source_db_table1="_LNResearch_ChannelAnnouncements",
            column_name1="ShortChannelID",
            source_db_table2="_LND_DBReader_ChannelAnnouncements",
            column_name2="ShortChannelID"
        )
        os.makedirs("/DATA/GENERATED/Compare_Sources/Channel_Announcements", exist_ok=True)
        with open("/DATA/GENERATED/Compare_Sources/Channel_Announcements/compare_sources.json", "w") as f:
            json.dump(general_stats, f, indent=4)


        # STEP 2: monthly counts → compare_sources_across_time.json
        # (written for reference — nothing reads this file at the
        # moment; the frontend uses the SVG from STEP 3 instead)
        # =========================================================
        stats_across_time = self.compare_sources_across_time()
        with open("/DATA/GENERATED/Compare_Sources/Channel_Announcements/compare_sources_across_time.json", "w") as f:
            json.dump(stats_across_time, f, indent=4)


        # STEP 3: render the comparison chart
        # ===================================
        self.plot_data(stats_across_time, xTicksToGenerate, xTicksToExclude)






    ############################################################
    # compare_sources
    ############################################################
    #
    # One-shot totals: COUNT(*) of each table plus the INNER
    # JOIN overlap on the given columns, stamped with
    # updated_at. Table/column names are interpolated into the
    # SQL with f-strings — tolerable only because the sole
    # caller passes hardcoded names; never feed this user
    # input.
    #
    # Used by:
    #   - __init__ (above) — on the two ChannelAnnouncements
    #     staging tables, joined on ShortChannelID
    ############################################################

    def compare_sources(self, source_db_table1, column_name1, source_db_table2, column_name2):
        with get_db_connection() as db_conn:
            with db_conn.cursor() as db_cursor:

                # Per-table totals
                db_cursor.execute(f"SELECT COUNT(*) FROM {source_db_table1}")
                count1 = db_cursor.fetchone()[0]

                db_cursor.execute(f"SELECT COUNT(*) FROM {source_db_table2}")
                count2 = db_cursor.fetchone()[0]

                # Rows both sources agree on (inner join)
                db_cursor.execute(f"SELECT COUNT(*) FROM {source_db_table1} INNER JOIN {source_db_table2} ON {source_db_table1}.{column_name1} = {source_db_table2}.{column_name2}")
                overlap_count = db_cursor.fetchone()[0]

                return {
                    source_db_table1: count1,
                    source_db_table2: count2,
                    "overlap": overlap_count,
                    "updated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }






    ############################################################
    # compare_sources_across_time
    ############################################################
    #
    # Monthly channel-announcement counts per source since
    # 2018-01-01. Announcements only carry a block height, so
    # BlockIndex joins Blockchain_Blocks.BlockHeight to get a
    # real calendar date. Returns {'YYYY-MM': {'lnresearch':
    # n, 'lnd_dbreader': n}} — a month missing from one source
    # simply lacks that key; plot_data fills 0 via .get().
    #
    # Used by:
    #   - __init__ (above)
    ############################################################

    def compare_sources_across_time(self):
        # Local shorthand — one query in, all rows out
        def get_monthly_counts(cursor, query):
            cursor.execute(query)
            return cursor.fetchall()

        data = {}
        with get_db_connection() as cnx:
            with cnx.cursor(dictionary=True) as cursor:

                # Same query for both staging tables — only the
                # table name differs
                query_research = """
                    SELECT DATE_FORMAT(b.Date, '%Y-%m') AS month, COUNT(*) AS count
                    FROM _LNResearch_ChannelAnnouncements a
                    JOIN Blockchain_Blocks b ON a.BlockIndex = b.BlockHeight
                    WHERE b.Date >= '2018-01-01'
                    GROUP BY month
                    ORDER BY month;
                """

                query_dbreader = """
                    SELECT DATE_FORMAT(b.Date, '%Y-%m') AS month, COUNT(*) AS count
                    FROM _LND_DBReader_ChannelAnnouncements a
                    JOIN Blockchain_Blocks b ON a.BlockIndex = b.BlockHeight
                    WHERE b.Date >= '2018-01-01'
                    GROUP BY month
                    ORDER BY month;
                """

                results_research = get_monthly_counts(cursor, query_research)
                results_dbreader = get_monthly_counts(cursor, query_dbreader)


                # First pass seeds the month entries
                print("Monthly counts for _LNResearch_ChannelAnnouncements:")
                for row in results_research:
                    print(f"{row['month']}: {row['count']}")
                    data[row['month']] = {}
                    data[row['month']]["lnresearch"] = row['count']



                print("\nMonthly counts for _LND_DBReader_ChannelAnnouncements:")
                for row in results_dbreader:
                    print(f"{row['month']}: {row['count']}")
                    # A month may exist in this source only
                    if row['month'] not in data:
                        data[row['month']] = {}
                    data[row['month']]["lnd_dbreader"] = row['count']
        return data






    ############################################################
    # plot_data
    ############################################################
    #
    # Draws the monthly comparison as a single 10x6 line chart
    # (10x6_Full.svg, with header and footer) under
    # .../Channel_Announcements/20XX<suffix>/ — the folder
    # name advertises which x ticks are drawn, and the
    # frontend DataSources.jsx links the 20XX-03-01 variant
    # explicitly.
    #
    # Used by:
    #   - __init__ (above)
    ############################################################

    def plot_data(self, data, xTicksShowEndsWith, xTicksToExclude):
        # STEP 1: flatten {month: {source: count}} into two
        # aligned series — a month missing from one source
        # counts as 0 there
        # =================================================
        months = sorted(data.keys())  # 'YYYY-MM' sorts lexicographically = chronologically
        lnresearch_data = [data[month].get("lnresearch", 0) for month in months]
        lnd_dbreader_data = [data[month].get("lnd_dbreader", 0) for month in months]

        # Real datetimes (first of month) so the x axis is a
        # true time axis, not evenly spaced labels
        x_data = [datetime.strptime(f"{month}-01", '%Y-%m-%d') for month in months]


        # STEP 2: output folder — '20XX' + the tick suffix
        # (save_chart below creates it on demand)
        # ================================================
        folderPath = f'/DATA/GENERATED/Compare_Sources/Channel_Announcements'
        folderPath += f'/{"20XX"+xTicksShowEndsWith}'


        # STEP 3: build and label the chart
        # =================================
        chart_generator = BaseChartGenerator(
            x_data=x_data,
            y_data_list=[lnresearch_data, lnd_dbreader_data],
            labels=["LNResearch", "LND DBReader"]
        )

        # The class default (24 pt) would crowd the long
        # y-axis title
        chart_generator.y_label_fontsize = 18

        chart_generator.customize_axes(
            x_label='Time',
            y_label='Channel Announcements Count',
            title='Comparison of Channel Announcements Sources Over Time'
        )
        chart_generator.set_x_ticks(ends_with=xTicksShowEndsWith, exclude_ends_with=xTicksToExclude)


        # STEP 4: render and save
        # =======================
        chart_generator.generate_line_chart(figsize=(10, 6), print_header=True, print_footer=True)
        filePath = folderPath + f'/10x6_Full.svg'
        chart_generator.save_chart(filePath)
        print(f"[*] Saved: {filePath}")

        # Matplotlib figures accumulate across a full
        # statistics run — collect explicitly to keep memory
        # flat
        gc.collect()
