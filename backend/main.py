############################################################
#  [*] BLN Stats — CLI entrypoint of the backend container
#
#  One flag, one job: everything the backend can do is
#  reachable from this dispatcher. The blnstats-backend
#  container runs "--serve-api" (backend/Dockerfile CMD);
#  the other flags are for manual runs inside the container.
#  The Prefect worker does NOT shell out to this file — it
#  wraps the same blnstats.* calls in workflows.py.
#
#    --import-ln-research-data             — LNResearch gossip dataset
#    --import-lnd-dbreader-data <path>     — LND DBReader dump (URL or file)
#    --sync-blockchain                     — blocks/transactions via Electrum
#    --calculate-ln-stats                  — recalculate all charts and CSVs
#    --serve-api                           — Flask API on :8000 (the CMD)
#    --calculate-channel-lifetime-plot     — hidden: absent from usage text
#    --calculate-channel-lifetime-average  — hidden: absent from usage text
#
#  A mistyped flag matches no branch and exits silently with
#  status 0 — there is no final else re-printing the usage.
############################################################


import blnstats
import sys








############################################################
# __main__ — flag dispatch
############################################################
#
# A plain if/elif chain on sys.argv[1] — no argparse, no
# validation beyond the argument count where one is needed.
#
# Used by:
#   - backend/Dockerfile CMD — "python3 -u main.py
#     --serve-api" (the blnstats-backend service)
#   - manual "docker exec" runs for imports and recalcs
############################################################

if __name__ == "__main__":

    # The usage text advertises only five of the seven flags —
    # the two channel-lifetime flags at the bottom are absent.
    if(len(sys.argv) == 1):
        print("Usage: python main.py <command>")
        print("")
        print("Commands:")
        print("  --import-ln-research-data      Import LN Research data")
        print("  --import-lnd-dbreader-data     Import LND DBReader data")
        print("  --sync-blockchain              Synchronize the blockchain")
        print("  --calculate-ln-stats           Calculate Lightning Network statistics")
        print("")
        print("  --serve-api                    Serve the backend API")
        print("")
        print("Example: python main.py --sync-blockchain")
        print("")
        print("")


    # Instantiating the class IS the import: LNResearchData
    # downloads, parses and inserts inside its __init__. Unlike
    # the DBReader branch below, this path skips the alias-to-
    # entity-cluster follow-up — and the package-level wrapper
    # that would run it, blnstats.importLNResearchData, is
    # broken (it imports a nonexistent LNResearch class; see
    # workflows.py where that wrapper is actually called).
    elif(sys.argv[1] == "--import-ln-research-data"):
        from blnstats.data_import.ln_research import LNResearchData
        LNResearchData()


    # Accepts a URL or a container-local path — the examples
    # in the error text show one of each.
    elif(sys.argv[1] == "--import-lnd-dbreader-data"):
        if(len(sys.argv) == 3):
            blnstats.importLNDDBReader(sys.argv[2])
        else:
            print("Error: Invalid number of arguments")
            print()
            print("Usage: python3 main.py --import-lnd-dbreader-data <file_path>")
            print()
            print("Examples:")
            print("    python3 main.py --import-lnd-dbreader-data http://192.168.1.2/rawdata/lnd-dbreader.json.gz")
            print("    python3 main.py --import-lnd-dbreader-data /DATA/INPUT/lnd-dbreader-20250101-123456.json.gz")
            print("")


    elif(sys.argv[1] == "--sync-blockchain"):
        blnstats.synchronizeBlockchain()


    # Same sequence the Prefect "BLN Analysis Flow" runs, minus
    # the blockchain sync — run --sync-blockchain first if the
    # chain data may be stale.
    elif(sys.argv[1] == "--calculate-ln-stats"):
        # STEP 1: node metrics first — every chart and CSV
        # below reads the tables this transform fills
        # ================================================
        blnstats.transformNodeMetrics()


        # STEP 2: general statistics and the LNResearch vs
        # LND DBReader source comparison
        # ================================================
        blnstats.generateGeneralStatisticsCharts()
        blnstats.compare_data_sources()


        # STEP 3: concentration coefficients — per subject,
        # all-on-one-chart, and overlapping variants
        # =================================================
        blnstats.generateCoefficientCharts(subjectsOfAnalysis=["Nodes"])
        blnstats.generateCoefficientCharts(subjectsOfAnalysis=["Entities"])
        blnstats.generateCoefficientsOnSingleChart()
        blnstats.generateOverlappingCoefficientCharts()


        # STEP 4: CSV export — 'X' is a date wildcard (SQL
        # LIKE '_'): '20XX-XX-01' means the first day of every
        # month since 2018, '2025-03-01' one fixed snapshot
        # ====================================================
        blnstats.generateCSV_EntityMetrics(dateMasks=['2025-03-01', '20XX-XX-01'])


        # STEP 5: Lorenz curves, plus the synthetic example set
        # =====================================================
        blnstats.generateLorenzCharts()
        blnstats.generateExampleLorenzCharts()


    # Flask's builtin dev server with debug=True hardcoded —
    # the interactive Werkzeug debugger is live wherever this
    # port is reachable, even though this flag is what the
    # production container's CMD runs.
    elif(sys.argv[1] == "--serve-api"):
        app = blnstats.create_app()
        app.run(host='0.0.0.0', port=8000, debug=True)


    # The two flags below work but are absent from the usage
    # text above — you have to know they exist.
    elif(sys.argv[1] == "--calculate-channel-lifetime-plot"):
        from blnstats.calculations.general_stats import GeneralStats
        GeneralStats().calculate_channel_lifetime_plot()


    elif(sys.argv[1] == "--calculate-channel-lifetime-average"):
        from blnstats.calculations.general_stats import GeneralStats
        GeneralStats().calculate_channel_lifetime_average()
