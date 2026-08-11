############################################################
#  [*] Prefect worker — tasks, flows, served deployments
#
#  The blnstats-prefect-worker container runs this file
#  ("python3 -u workflows.py", docker-compose.yml) and sits
#  in serve() forever, waiting on the Prefect server
#  (PREFECT_API_URL) for runs triggered from the admin UI.
#  Every @task is a thin print-bracketed wrapper around one
#  blnstats.* call so each pipeline step gets its own run
#  state in Prefect; the returned strings exist only for the
#  UI. Tasks are called directly (never .submit()), so every
#  flow executes strictly sequentially.
#
#  Served deployments (names must match ACTIONS in the admin
#  UI's QuickActions.jsx — it triggers runs by these exact
#  strings):
#    LND DBReader Full Update Flow — one import + recalc
#    Full Initialization Flow      — both imports + recalc,
#      one-time: sets InitialSyncCompleted, which greys its
#      button out in the admin UI
#  The analysis pipeline itself runs only as a subflow of
#  these two — it is no longer served on its own.
############################################################


from prefect import flow, task, serve
from prefect.schedules import Cron
import blnstats
from blnstats.database.utils import get_setting, set_setting


# The System_Settings key the admin UI's Data Source card
# edits; both DBReader-importing flows resolve their dump URL
# through it. The literal below is only the fallback for an
# unseeded table — database/utils.py and mysql/init.sql seed
# the same value.
DBREADER_SOURCE_KEY = 'LND-DBReader-Source-1'
DBREADER_SOURCE_FALLBACK = 'https://blnstats.knf.vu.lt/rawdata/INPUT/lnd-dbreader-A336EEAB--latest.json.gz'

# Flipped to '1' when full_initialization_flow completes; the
# admin UI greys its button out on it — the static LNResearch
# archive only needs importing once, refreshes come from the
# DBReader update flow. Seeded '0' by database/utils.py and
# mysql/init.sql.
INITIAL_SYNC_KEY = 'InitialSyncCompleted'








############################################################
# transform_node_metrics
############################################################
#
# Wraps blnstats.transformNodeMetrics(): fills the node
# metric tables for the first block of every month — the
# input every chart task below reads.
#
# Used by:
#   - lightning_network_statistics_flow (below)
############################################################

@task
def transform_node_metrics():
    print("Transforming node metrics...")
    blnstats.transformNodeMetrics()
    print("Node metrics transformation completed.")
    return "Node metrics transformed"








############################################################
# generate_general_statistics_charts
############################################################
#
# Wraps blnstats.generateGeneralStatisticsCharts(): the
# network-growth overview charts.
#
# Used by:
#   - lightning_network_statistics_flow (below)
############################################################

@task
def generate_general_statistics_charts():
    print("Generating general statistics charts...")
    blnstats.generateGeneralStatisticsCharts()
    print("General statistics charts generated.")
    return "General statistics charts generated"








############################################################
# compare_data_sources
############################################################
#
# Wraps blnstats.compare_data_sources(): the chart comparing
# the LNResearch dataset against the LND DBReader dump.
#
# Used by:
#   - lightning_network_statistics_flow (below)
############################################################

@task
def compare_data_sources():
    print("Comparing data sources...")
    blnstats.compare_data_sources()
    print("Data sources comparison completed.")
    return "Data sources compared"








############################################################
# generate_coefficient_charts
############################################################
#
# Wraps blnstats.generateCoefficientCharts() for one subject
# list — the analysis flow calls it twice, once with
# ["Nodes"] and once with ["Entities"], so the two subjects
# show up as separate task runs in the Prefect UI.
#
# Used by:
#   - lightning_network_statistics_flow (below) — twice
############################################################

@task
def generate_coefficient_charts(subjects_of_analysis):
    print(f"Generating coefficient charts for: {subjects_of_analysis}")
    blnstats.generateCoefficientCharts(subjectsOfAnalysis=subjects_of_analysis)
    print(f"Coefficient charts for {subjects_of_analysis} generated.")
    return f"Coefficient charts generated for {subjects_of_analysis}"








############################################################
# generate_coefficients_on_single_chart
############################################################
#
# Wraps blnstats.generateCoefficientsOnSingleChart(): all
# coefficient types drawn on one combined chart.
#
# Used by:
#   - lightning_network_statistics_flow (below)
############################################################

@task
def generate_coefficients_on_single_chart():
    print("Generating coefficients on single chart...")
    blnstats.generateCoefficientsOnSingleChart()
    print("Single chart coefficients generated.")
    return "Single chart coefficients generated"








############################################################
# generate_overlapping_coefficient_charts
############################################################
#
# Wraps blnstats.generateOverlappingCoefficientCharts():
# the Nodes-vs-Entities overlay variants.
#
# Used by:
#   - lightning_network_statistics_flow (below)
############################################################

@task
def generate_overlapping_coefficient_charts():
    print("Generating overlapping coefficient charts...")
    blnstats.generateOverlappingCoefficientCharts()
    print("Overlapping coefficient charts generated.")
    return "Overlapping coefficient charts generated"








############################################################
# generate_csv_entity_metrics
############################################################
#
# Wraps blnstats.generateCSV_EntityMetrics(date_masks). In a
# mask, 'X' is a date wildcard (it becomes '_' in SQL LIKE):
# '20XX-XX-01' selects the first day of every month since
# 2018, while a full date like '2025-03-01' selects that one
# snapshot.
#
# Used by:
#   - lightning_network_statistics_flow (below)
############################################################

@task
def generate_csv_entity_metrics(date_masks):
    print(f"Generating CSV entity metrics for date masks: {date_masks}")
    blnstats.generateCSV_EntityMetrics(dateMasks=date_masks)
    print("CSV entity metrics generated.")
    return f"CSV entity metrics generated for {date_masks}"








############################################################
# generate_lorenz_charts
############################################################
#
# Wraps blnstats.generateLorenzCharts(): the Lorenz curve
# charts of capacity/channel concentration.
#
# Used by:
#   - lightning_network_statistics_flow (below)
############################################################

@task
def generate_lorenz_charts():
    print("Generating Lorenz charts...")
    blnstats.generateLorenzCharts()
    print("Lorenz charts generated.")
    return "Lorenz charts generated"








############################################################
# generate_example_lorenz_charts
############################################################
#
# Wraps blnstats.generateExampleLorenzCharts(): synthetic
# example curves, independent of the imported data.
#
# Used by:
#   - lightning_network_statistics_flow (below)
############################################################

@task
def generate_example_lorenz_charts():
    print("Generating example Lorenz charts...")
    blnstats.generateExampleLorenzCharts()
    print("Example Lorenz charts generated.")
    return "Example Lorenz charts generated"








############################################################
# synchronize_blockchain
############################################################
#
# Wraps blnstats.synchronizeBlockchain(): pulls missing
# blocks and transactions from the Electrum server named in
# BLNSTATS_ELECTRUM_HOST/_PORT.
#
# Used by:
#   - lightning_network_statistics_flow (below)
############################################################

@task
def synchronize_blockchain():
    print("Synchronizing blockchain...")
    blnstats.synchronizeBlockchain()
    print("Blockchain synchronization completed.")
    return "Blockchain synchronized"








############################################################
# import_lnd_dbreader_data
############################################################
#
# Wraps blnstats.importLNDDBReader(file_path): imports the
# dump (URL or local path) and then runs the alias-to-
# entity-cluster follow-up.
#
# Used by:
#   - lnd_dbreader_import_flow (below) — itself unused
#   - lnd_dbreader_full_update_flow (below)
#   - full_initialization_flow (below)
############################################################

@task
def import_lnd_dbreader_data(file_path):
    print(f"Importing LND DBReader data from: {file_path}")
    blnstats.importLNDDBReader(file_path)
    print("LND DBReader data import completed.")
    return f"LND DBReader data imported from {file_path}"








############################################################
# import_ln_research_data
############################################################
#
# Wraps blnstats.importLNResearchData(): the full LNResearch
# import (LNResearchData() runs download/parse/insert in its
# __init__) plus the alias-to-entity-cluster follow-up that
# main.py's --import-ln-research-data branch skips.
#
# Used by:
#   - ln_research_import_flow (below) — itself unused
#   - full_initialization_flow (below) — its first step
############################################################

@task
def import_ln_research_data():
    print("Importing LNResearch data...")
    blnstats.importLNResearchData()
    print("LNResearch data import completed.")
    return "LNResearch data imported"








############################################################
# lnd_dbreader_import_flow
############################################################
#
# Import-only flow around import_lnd_dbreader_data — no
# recalculation afterwards.
#
# Used by:
#   - nothing at the moment: it is not among the served
#     deployments below, and lnd_dbreader_full_update_flow
#     calls the task directly instead of this flow
############################################################

@flow
def lnd_dbreader_import_flow(file_path: str):
    return import_lnd_dbreader_data(file_path)








############################################################
# ln_research_import_flow
############################################################
#
# Import-only flow around import_ln_research_data — which
# currently always fails (see that task's banner).
#
# Used by:
#   - nothing at the moment: it is not among the served
#     deployments below, and full_initialization_flow calls
#     the task directly instead of this flow
############################################################

@flow
def ln_research_import_flow():
    return import_ln_research_data()








############################################################
# lightning_network_statistics_flow
############################################################
#
# The whole recalculation pipeline: blockchain sync, node
# metric transform, then every chart and CSV the site
# serves. Order matters — later steps read tables the
# earlier ones fill. Same sequence as main.py
# --calculate-ln-stats, plus the blockchain sync that flag
# leaves out. The returned dict of task-result strings is
# only surfaced in the Prefect UI.
#
# Used by:
#   - lnd_dbreader_full_update_flow (below) — as a subflow
#   - full_initialization_flow (below) — as a subflow
#   - no longer served on its own: the admin UI's separate
#     "Recalculate Statistics" button was removed 2026-08
############################################################

@flow
def lightning_network_statistics_flow():
    # STEP 1: blockchain first — the capacity metrics need
    # blocks and transactions to be current
    # ====================================================
    sync_result = synchronize_blockchain()


    # STEP 2: node metrics — fills the tables every chart
    # below reads
    # ===================================================
    node_metrics_result = transform_node_metrics()


    # STEP 3: general statistics and the source comparison
    # ====================================================
    general_stats_result = generate_general_statistics_charts()
    data_sources_result = compare_data_sources()


    # STEP 4: concentration coefficients — per subject,
    # all-on-one-chart, and overlapping variants
    # =================================================
    nodes_coefficients = generate_coefficient_charts(["Nodes"])
    entities_coefficients = generate_coefficient_charts(["Entities"])
    single_chart_coefficients = generate_coefficients_on_single_chart()
    overlapping_coefficients = generate_overlapping_coefficient_charts()


    # STEP 5: CSV export — 'X' is a date wildcard (SQL LIKE
    # '_'): '20XX-XX-01' means the first day of every month
    # since 2018, '2025-03-01' one fixed snapshot
    # =====================================================
    csv_result = generate_csv_entity_metrics(['2025-03-01', '20XX-XX-01'])


    # STEP 6: Lorenz curves, plus the synthetic example set
    # =====================================================
    lorenz_result = generate_lorenz_charts()
    example_lorenz_result = generate_example_lorenz_charts()


    return {
        "sync_blockchain": sync_result,
        "node_metrics": node_metrics_result,
        "general_stats": general_stats_result,
        "data_sources": data_sources_result,
        "nodes_coefficients": nodes_coefficients,
        "entities_coefficients": entities_coefficients,
        "single_chart_coefficients": single_chart_coefficients,
        "overlapping_coefficients": overlapping_coefficients,
        "csv_export": csv_result,
        "lorenz_charts": lorenz_result,
        "example_lorenz": example_lorenz_result
    }








############################################################
# lnd_dbreader_full_update_flow
############################################################
#
# One-source refresh: import an LND DBReader dump, then run
# the full analysis pipeline as a subflow.
#
# Used by:
#   - served below as deployment "LND DBReader Full Update
#     Flow" — the admin UI's "Update From DBReader" button
############################################################

@flow
def lnd_dbreader_full_update_flow(file_path=None):

    # With no explicit path, the dump URL comes from
    # System_Settings — editable in the admin UI's Data Source
    # card — with the public mirror as the code fallback for
    # an unseeded table.
    if(file_path == None):
        file_path = get_setting(DBREADER_SOURCE_KEY, DBREADER_SOURCE_FALLBACK)
    lnd_dbreader_import_result = import_lnd_dbreader_data(file_path)


    # Everything downstream of the import is recalculated as
    # a subflow.
    analysis_results = lightning_network_statistics_flow()


    return {
        "lnd_dbreader_import": lnd_dbreader_import_result,
        "bln_analysis": analysis_results
    }








############################################################
# full_initialization_flow
############################################################
#
# Cold-start pipeline for an empty database: both source
# imports, then the full analysis (which itself begins with
# the blockchain sync). The DBReader dump URL comes from the
# same System_Settings key the update flow uses, so the
# admin-set source applies to both. Completing marks
# InitialSyncCompleted = '1', which greys the button out in
# the admin UI — the LNResearch archive is static, so this
# flow is meant to run ONCE per database.
#
# Used by:
#   - served below as deployment "Full Initialization Flow"
#     — the admin UI's "Run Full Pipeline" button
############################################################

@flow
def full_initialization_flow():
    # STEP 1: LNResearch gossip archive
    # =================================
    ln_research_import_result = import_ln_research_data()


    # STEP 2: LND DBReader dump — settings-driven, same
    # source the update flow resolves
    # =================================================
    lnd_dbreader_import_result = import_lnd_dbreader_data(
        get_setting(DBREADER_SOURCE_KEY, DBREADER_SOURCE_FALLBACK))


    # STEP 3: recalculate everything as a subflow
    # ===========================================
    analysis_results = lightning_network_statistics_flow()


    # STEP 4: mark the one-time initialization done — only on
    # full success (any failed task above raises past this)
    # ======================================================
    set_setting(INITIAL_SYNC_KEY, '1')


    return {
        "ln_research_import": ln_research_import_result,
        "lnd_dbreader_import": lnd_dbreader_import_result,
        "bln_analysis": analysis_results
    }








############################################################
# __main__ — build and serve the deployments
############################################################
#
# serve() blocks forever: this is the worker container's
# entire life. Only these two flows are reachable from the
# admin UI — the import-only flows and the analysis flow are
# not served (the analysis runs as a subflow of both). The
# deployment names are the API: QuickActions.jsx in the
# admin UI triggers runs by these exact strings, so renaming
# one here silently disables its dashboard button.
#
# The DBReader update flow also carries the ONLY schedule:
# monthly, the 1st at 04:00 Europe/Vilnius (the dataset's
# pinned zone) — right after the monthly snapshot boundary
# every chart is keyed to, so the data can no longer
# silently go stale (the 2026-08 audit found a six-week gap
# nobody noticed). The other two deployments stay
# manual-trigger. The Data Source card in the admin UI
# states this schedule — keep the two in sync.
#
# Used by:
#   - blnstats-prefect-worker (docker-compose.yml) —
#     command: python3 -u workflows.py
############################################################

if __name__ == "__main__":
    full_lnd_dbreader_update_deployment = lnd_dbreader_full_update_flow.to_deployment(
        name="LND DBReader Full Update Flow",
        schedules=[Cron("0 4 1 * *", timezone="Europe/Vilnius")],
    )
    full_pipeline_deployment = full_initialization_flow.to_deployment(name="Full Initialization Flow")

    serve(
        full_lnd_dbreader_update_deployment,
        full_pipeline_deployment
    )
