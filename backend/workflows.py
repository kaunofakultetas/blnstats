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
#    BLN Analysis Flow             — recalculate everything
#    LND DBReader Full Update Flow — one import + recalc
#    Full Initialization Flow      — both imports + recalc
############################################################


from prefect import flow, task, serve
import blnstats








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
# Wraps blnstats.importLNResearchData(). BUG, documented not
# fixed: that wrapper does "from .data_import.ln_research
# import LNResearch", but the module only defines
# LNResearchData (whose __init__ performs the whole import;
# there is no public import_data method either) — so this
# task raises ImportError every time it runs, killing the
# Full Initialization Flow at its first step. main.py's
# --import-ln-research-data branch instantiates
# LNResearchData directly and works.
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
#   - served below as deployment "BLN Analysis Flow"
#   - lnd_dbreader_full_update_flow (below) — as a subflow
#   - full_initialization_flow (below) — as a subflow
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

    # With no explicit path, pull the always-current dump from
    # the host at Vilnius University Kaunas faculty that
    # publishes it — 172.16.2.6 is a private address, so the
    # default only works from inside that network (the public
    # mirror of the same dump is https://blnstats.knf.vu.lt/
    # rawdata/INPUT/lnd-dbreader-A336EEAB--latest.json.gz,
    # which full_initialization_flow uses instead).
    if(file_path == None):
        file_path = "https://blnstats.knf.vu.lt/rawdata/INPUT/lnd-dbreader-A336EEAB--latest.json.gz"
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
# the blockchain sync). BROKEN at its first step for as long
# as import_ln_research_data raises ImportError (see that
# task's banner). Note the source asymmetry: this flow
# hardcodes the public mirror URL for the DBReader dump,
# while lnd_dbreader_full_update_flow defaults to the
# internal 172.16.2.6 host.
#
# Used by:
#   - served below as deployment "Full Initialization Flow"
#     — the admin UI's "Run Full Pipeline" button
############################################################

@flow
def full_initialization_flow():
    # STEP 1: LNResearch gossip archive — currently dies
    # with ImportError inside blnstats.importLNResearchData
    # =====================================================
    ln_research_import_result = import_ln_research_data()


    # STEP 2: LND DBReader dump — from the public mirror,
    # not the internal host the update flow defaults to
    # ===================================================
    lnd_dbreader_import_result = import_lnd_dbreader_data("https://blnstats.knf.vu.lt/rawdata/INPUT/lnd-dbreader-A336EEAB--latest.json.gz")


    # STEP 3: recalculate everything as a subflow
    # ===========================================
    analysis_results = lightning_network_statistics_flow()


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
# entire life. Only these three flows are reachable from the
# admin UI — the two import-only flows above are not served.
# The deployment names are the API: QuickActions.jsx in the
# admin UI triggers runs by these exact strings, so renaming
# one here silently disables its dashboard button.
#
# Used by:
#   - blnstats-prefect-worker (docker-compose.yml) —
#     command: python3 -u workflows.py
############################################################

if __name__ == "__main__":
    ln_stats_deployment = lightning_network_statistics_flow.to_deployment(name="BLN Analysis Flow")
    full_lnd_dbreader_update_deployment = lnd_dbreader_full_update_flow.to_deployment(name="LND DBReader Full Update Flow")
    full_pipeline_deployment = full_initialization_flow.to_deployment(name="Full Initialization Flow")

    serve(
        ln_stats_deployment,
        full_lnd_dbreader_update_deployment,
        full_pipeline_deployment
    )
