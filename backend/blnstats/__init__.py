############################################################
#  [*] blnstats — Flask app factory + analysis pipelines
#
#  Package root of the backend. create_app() builds the
#  API server that the blnstats-backend container runs;
#  every other top-level function is an offline pipeline
#  step (blockchain sync, raw-data imports, node-metric
#  transforms, chart/CSV generation) driven by main.py CLI
#  flags and by the Prefect @task wrappers in workflows.py.
#  All generated output lands under /DATA/GENERATED/...,
#  published to the site as static files.
#
#  The API routes live in the two blueprints create_app()
#  registers (api/auth/routes.py, api/settings/routes.py):
#
#    POST /api/login                — session login
#    GET  /api/checkauth            — session validity probe
#    GET  /api/admin/administrators — admin account list
#    POST /api/admin/administrators — add/edit/delete admin
#    GET  /api/settings             — System_Settings dump
############################################################


from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

import os
import gc
from datetime import datetime
import hashlib
import random

from .database.utils import create_database_if_not_exists, create_tables_if_not_exists
from .database.raw_data_selector import RawDataSelector
from .database.node_metrics_selector import NodeMetricsSelector
from .database.entity_metrics_selector import EntityMetricsSelector
from .data_transform.entity_clusters import EntityClusters
from .calculations.coefficients import Coefficients
from .charts.chart_generator import BaseChartGenerator, LorenzCurveChartGenerator

import logging


# One root logging config for the whole package — the
# containers run python3 -u, stdout is the only log sink.
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


# Read once at import time — flipping APP_DEBUG needs a
# container restart, not just a new request.
APP_DEBUG = os.getenv('APP_DEBUG', 'false').lower() == "true"








############################################################
# create_app
############################################################
#
# Flask application factory: makes sure the lnstats schema
# and tables exist, then wires ProxyFix, the login manager
# and the two API blueprints (api/auth/routes.py,
# api/settings/routes.py — endpoint index in the file
# header above).
#
# Secret key: with APP_DEBUG=true it is the SHA-256 of
# today's date, so dev sessions survive restarts but every
# login dies at midnight — and the key is predictable, so
# debug mode must never face the internet. In production
# it is 32 fresh random bytes, so a restart logs every
# admin out.
#
# SESSION_COOKIE_HTTPONLY=False leaves the session cookie
# readable by page JavaScript — any XSS on the admin pages
# can lift it. Documented here, deliberately not fixed.
#
# Used by:
#   - main.py --serve-api — the blnstats-backend container
#     CMD (python3 -u main.py --serve-api)
############################################################

def create_app():
    # STEP 1: create the lnstats database and tables on
    # first boot — both are no-ops afterwards
    # =================================================
    create_database_if_not_exists('lnstats')
    create_tables_if_not_exists()


    # STEP 2: the Flask app itself, behind one trusted
    # reverse-proxy hop so request.remote_addr is the real
    # client address, not the Caddy container
    # ====================================================
    app = Flask(__name__)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)


    # STEP 3: session secret — deterministic per-day in
    # debug, random per-process in production (see banner)
    # ====================================================
    if(APP_DEBUG):
        app.secret_key = hashlib.sha256(datetime.now().strftime("%Y-%m-%d").encode()).digest()
    else:
        app.secret_key = random.randbytes(32)
    app.config['SESSION_COOKIE_HTTPONLY'] = False


    # STEP 4: flask-login session manager
    # ===================================
    from .api.auth.user import login_manager
    login_manager.init_app(app)


    # STEP 5: the API blueprints — every route lives there
    # ====================================================
    from .api.auth.routes import auth_bp
    app.register_blueprint(auth_bp, url_prefix='')

    from .api.settings.routes import settings_bp
    app.register_blueprint(settings_bp, url_prefix='')

    return app








############################################################
# generateCoefficientCharts
############################################################
#
# The main coefficient-chart pipeline: for every requested
# (subject, metric, coefficient) combination it computes a
# monthly concentration-coefficient series and renders it
# as SVG line charts under /DATA/GENERATED/<subject>/
# <metric>/<coefficient>/20XX-03-01/. The metric and
# coefficient series are also archived as JSON next to the
# charts. "weighted degree" means per-vertex channel
# capacity, "degree" means channel count.
#
# Every chart comes in three canvas sizes, as a Full and a
# NoHeaderFooter variant (the NoFooter variant is disabled
# on purpose). Only March snapshots get x-axis labels;
# Feb/Jul/Aug ticks are dropped entirely.
#
# "firstBlocksOfMoths" (sic, months) — the typo repeats
# through this whole file; the name is load-bearing, keep
# it.
#
# Used by:
#   - workflows.py generate_coefficient_charts (@task) —
#     lightning_network_statistics_flow calls it once with
#     ["Nodes"] and once with ["Entities"]
#   - main.py --calculate-ln-stats — the same two calls
############################################################

def generateCoefficientCharts(
        subjectsOfAnalysis=["Nodes", "Entities"],
        metricTypes=["weighted degree", "degree"],
        coefficientTypes=["Gini", "HHI", "Theil", "Normalized Theil", "Shannon Entropy", "Normalized Shannon Entropy", "Nakamoto",
                        "Top 10 Percent Control Percentage", "Top 10 Percent Control Sum"]
    ):
    # STEP 1: fixed chart variations — March-only x-ticks
    # (skip Feb/Jul/Aug) and three canvas sizes
    # ===================================================
    dateMask = '20XX-XX-01'

    # xTicksToGenerate = ["-03-01", "-06-01", "-09-01", "-12-01"]
    xTicksToGenerate = ["-03-01"]
    xTicksToExclude = ["-02-01", "-07-01", "-08-01"]
    figSizes = [(6, 10), (10, 6), (6, 6)]


    # STEP 2: block height of the first block of every
    # month since Feb 2018
    # ================================================
    firstBlocksOfMoths = RawDataSelector().get_first_blocks_of_days_by_date_mask(
        startSince='2018-02-01', endUntil=datetime.now().strftime('%Y-%m-%d'), dateMask=dateMask
    )

    for subjectOfAnalysis in subjectsOfAnalysis:
        for metricType in metricTypes:


            # STEP 3: pull the per-vertex monthly series for
            # this (subject, metric) pair, archive it as JSON
            # ===============================================
            metricsDataSelector = None
            if(subjectOfAnalysis == "Nodes"):
                metricsDataSelector = NodeMetricsSelector()
            elif(subjectOfAnalysis == "Entities"):
                metricsDataSelector = EntityMetricsSelector()

            # An unrecognized metricType leaves this None and
            # crashes on save_to_file — there is no else guard.
            verticesAspectData = None
            if(metricType == "weighted degree"):
                verticesAspectData = metricsDataSelector.get_capacity_metrics(firstBlocksOfMoths)
            elif(metricType == "degree"):
                verticesAspectData = metricsDataSelector.get_channel_count_metrics(firstBlocksOfMoths)

            filePath = f'/DATA/GENERATED/{subjectOfAnalysis}/{metricType.replace(" ", "_")}/{dateMask}.json'
            verticesAspectData.save_to_file(filePath)
            print(f"[*] Saved: {filePath}")


            for coefficientType in coefficientTypes:


                # STEP 4: the coefficient series itself,
                # archived as JSON next to the charts
                # ======================================
                coefficientsData = Coefficients().calculate_on_vertices_data(verticesAspectData, coefficientType.replace(" ", ""))
                filePath = f'/DATA/GENERATED/{subjectOfAnalysis}/{metricType.replace(" ", "_")}/{coefficientType.replace(" ", "_")}/{dateMask}.json'
                coefficientsData.save_to_file(filePath)
                print(f"[*] Saved: {filePath}")


                # STEP 5: render the series in every tick
                # layout and canvas size
                # =======================================
                for xTicksShowEndsWith in xTicksToGenerate:
                    for figsize in figSizes:
                        x_data = [item.date for item in coefficientsData.data.values()]
                        y_data = [item.value for item in coefficientsData.data.values()]

                        x_data = [datetime.strptime(x, '%Y-%m-%d') for x in x_data]

                        folderPath = f'/DATA/GENERATED/{subjectOfAnalysis}/{metricType.replace(" ", "_")}/{coefficientType.replace(" ", "_")}'
                        folderPath += f'/{"20XX"+xTicksShowEndsWith}'

                        chart_generator = BaseChartGenerator(x_data=x_data, y_data_list=[y_data], labels=[coefficientType])
                        chart_generator.customize_axes(
                            x_label='Time',
                            y_label=coefficientType,
                            title=f'{coefficientType} coefficient of {metricType}\ncentrality (BLN {subjectOfAnalysis})'
                        )
                        chart_generator.set_x_ticks(ends_with=xTicksShowEndsWith, exclude_ends_with=xTicksToExclude)

                        # STEP 5.1: Full variant — header and footer on
                        chart_generator.generate_line_chart(figsize=figsize, print_header=True, print_footer=True)
                        filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_Full.svg'
                        chart_generator.save_chart(filePath)
                        print(f"[*] Saved: {filePath}")

                        # # NoFooter variant — disabled, not published:
                        # filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_NoFooter.svg'
                        # chart_generator.generate_line_chart(figsize=figsize, print_header=True, print_footer=False)
                        # chart_generator.save_chart(filePath)
                        # print(f"[*] Saved: {filePath}")

                        # STEP 5.2: bare NoHeaderFooter plot for embedding
                        filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_NoHeaderFooter.svg'
                        chart_generator.generate_line_chart(figsize=figsize, print_header=False, print_footer=False)
                        chart_generator.save_chart(filePath)
                        print(f"[*] Saved: {filePath}")

                        # Matplotlib figures pile up fast — force a GC
                        # every iteration to keep the RSS flat.
                        gc.collect()








############################################################
# generateOverlappingCoefficientCharts
############################################################
#
# Same coefficient pipeline as generateCoefficientCharts,
# but every chart overlays the Entities and the Nodes
# series so the two subjects can be compared directly;
# output goes to /DATA/GENERATED/EntitiesNodes/<metric>/
# <coefficient>/. Nothing is archived as JSON here — this
# one only draws.
#
# The x-axis dates come from the ENTITIES series and the
# Nodes values are plotted against them by position, so
# both selectors must return the same block heights in the
# same order (they do — both walk firstBlocksOfMoths).
#
# Used by:
#   - workflows.py generate_overlapping_coefficient_charts
#     (@task) — lightning_network_statistics_flow
#   - main.py --calculate-ln-stats
############################################################

def generateOverlappingCoefficientCharts():
    # STEP 1: fixed chart variations and the analysis matrix
    # ======================================================
    dateMask = '20XX-XX-01'

    # xTicksToGenerate = ["-03-01", "-06-01", "-09-01", "-12-01"]
    xTicksToGenerate = ["-03-01"]
    xTicksToExclude = ["-02-01", "-07-01", "-08-01"]
    figSizes = [(6, 10), (10, 6), (6, 6)]

    metricTypes = ["weighted degree", "degree"]
    coefficientTypes = ["Gini", "HHI", "Theil", "Normalized Theil", "Shannon Entropy", "Normalized Shannon Entropy", "Nakamoto",
                        "Top 10 Percent Control Percentage", "Top 10 Percent Control Sum"]


    # STEP 2: block height of the first block of every
    # month since Feb 2018
    # ================================================
    firstBlocksOfMoths = RawDataSelector().get_first_blocks_of_days_by_date_mask(
        startSince='2018-02-01', endUntil=datetime.now().strftime('%Y-%m-%d'), dateMask=dateMask
    )

    for metricType in metricTypes:


        # STEP 3: the per-vertex monthly series for BOTH
        # subjects at once
        # ==============================================
        verticesAspectDataNodes = None
        verticesAspectDataEntities = None
        if(metricType == "weighted degree"):
            verticesAspectDataNodes = NodeMetricsSelector().get_capacity_metrics(firstBlocksOfMoths)
            verticesAspectDataEntities = EntityMetricsSelector().get_capacity_metrics(firstBlocksOfMoths)
        elif(metricType == "degree"):
            verticesAspectDataNodes = NodeMetricsSelector().get_channel_count_metrics(firstBlocksOfMoths)
            verticesAspectDataEntities = EntityMetricsSelector().get_channel_count_metrics(firstBlocksOfMoths)


        for coefficientType in coefficientTypes:


            # STEP 4: the coefficient series for both subjects
            # ================================================
            coefficientsDataEntities = Coefficients().calculate_on_vertices_data(verticesAspectDataEntities, coefficientType.replace(" ", ""))
            coefficientsDataNodes = Coefficients().calculate_on_vertices_data(verticesAspectDataNodes, coefficientType.replace(" ", ""))


            # STEP 5: render both series on one chart per tick
            # layout and canvas size — dates taken from the
            # Entities series (see banner)
            # ================================================
            for xTicksShowEndsWith in xTicksToGenerate:
                for figsize in figSizes:
                    x_data = [item.date for item in coefficientsDataEntities.data.values()]
                    y_data_entities = [item.value for item in coefficientsDataEntities.data.values()]
                    y_data_nodes = [item.value for item in coefficientsDataNodes.data.values()]

                    x_data = [datetime.strptime(x, '%Y-%m-%d') for x in x_data]

                    folderPath = f'/DATA/GENERATED/EntitiesNodes/{metricType.replace(" ", "_")}/{coefficientType.replace(" ", "_")}'
                    folderPath += f'/{"20XX"+xTicksShowEndsWith}'

                    chart_generator = BaseChartGenerator(
                        x_data=x_data,
                        y_data_list=[y_data_entities, y_data_nodes],
                        labels=[coefficientType+" (Entities)", coefficientType+" (Nodes)"]
                    )
                    chart_generator.customize_axes(
                        x_label='Time',
                        y_label=coefficientType,
                        title=f'{coefficientType} coefficient of {metricType}\ncentrality (BLN Entities and Nodes)'
                    )
                    chart_generator.set_x_ticks(ends_with=xTicksShowEndsWith, exclude_ends_with=xTicksToExclude)

                    # STEP 5.1: Full variant — header and footer on
                    chart_generator.generate_line_chart(figsize=figsize, print_header=True, print_footer=True)
                    filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_Full.svg'
                    chart_generator.save_chart(filePath)
                    print(f"[*] Saved: {filePath}")

                    # # NoFooter variant — disabled, not published:
                    # filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_NoFooter.svg'
                    # chart_generator.generate_line_chart(figsize=figsize, print_header=True, print_footer=False)
                    # chart_generator.save_chart(filePath)
                    # print(f"[*] Saved: {filePath}")

                    # STEP 5.2: bare NoHeaderFooter plot for embedding
                    filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_NoHeaderFooter.svg'
                    chart_generator.generate_line_chart(figsize=figsize, print_header=False, print_footer=False)
                    chart_generator.save_chart(filePath)
                    print(f"[*] Saved: {filePath}")

                    # Matplotlib figures pile up fast — force a GC
                    # every iteration to keep the RSS flat.
                    gc.collect()








############################################################
# generateCoefficientsOnSingleChart
############################################################
#
# One chart per (subject, metric) with four normalized
# coefficient series overlaid: Gini, HHI, Normalized Theil
# and Normalized Shannon Entropy. HHI is divided by 10000
# to squeeze its 0–10000 range onto the shared 0–1 axis
# (the y-axis is clamped to 0–1.2). Output goes to
# /DATA/GENERATED/<subject>/<metric>/
# Gini_HHI_NormTheil_NormShannonEntropy/. Draw-only, no
# JSON archive.
#
# Used by:
#   - workflows.py generate_coefficients_on_single_chart
#     (@task) — lightning_network_statistics_flow
#   - main.py --calculate-ln-stats
############################################################

def generateCoefficientsOnSingleChart():
    # STEP 1: fixed chart variations and the analysis matrix
    # ======================================================
    dateMask = '20XX-XX-01'

    # xTicksToGenerate = ["-03-01", "-06-01", "-09-01", "-12-01"]
    xTicksToGenerate = ["-03-01"]
    xTicksToExclude = ["-02-01", "-07-01", "-08-01"]
    figSizes = [(6, 10), (10, 6), (6, 6)]

    subjectsOfAnalysis = ["Nodes", "Entities"]
    metricTypes = ["weighted degree", "degree"]


    # STEP 2: block height of the first block of every
    # month since Feb 2018
    # ================================================
    firstBlocksOfMoths = RawDataSelector().get_first_blocks_of_days_by_date_mask(
        startSince='2018-02-01', endUntil=datetime.now().strftime('%Y-%m-%d'), dateMask=dateMask
    )

    for subjectOfAnalysis in subjectsOfAnalysis:
        for metricType in metricTypes:


            # STEP 3: the per-vertex monthly series for this
            # (subject, metric) pair
            # ==============================================
            metricsDataSelector = None
            if(subjectOfAnalysis == "Nodes"):
                metricsDataSelector = NodeMetricsSelector()
            elif(subjectOfAnalysis == "Entities"):
                metricsDataSelector = EntityMetricsSelector()

            verticesAspectData = None
            if(metricType == "weighted degree"):
                verticesAspectData = metricsDataSelector.get_capacity_metrics(firstBlocksOfMoths)
            elif(metricType == "degree"):
                verticesAspectData = metricsDataSelector.get_channel_count_metrics(firstBlocksOfMoths)


            # STEP 4: the four coefficient series
            # ===================================
            giniCoefData = Coefficients().calculate_on_vertices_data(verticesAspectData, "Gini")
            hhiCoefData = Coefficients().calculate_on_vertices_data(verticesAspectData, "HHI")
            normalizedTheilCoefData = Coefficients().calculate_on_vertices_data(verticesAspectData, "NormalizedTheil")
            normalizedShannonEntropyCoefData = Coefficients().calculate_on_vertices_data(verticesAspectData, "NormalizedShannonEntropy")


            # STEP 5: render all four series on one chart per
            # tick layout and canvas size
            # ===============================================
            for xTicksShowEndsWith in xTicksToGenerate:
                for figsize in figSizes:
                    x_data = [item.date for item in giniCoefData.data.values()]

                    y_data_gini = [item.value for item in giniCoefData.data.values()]
                    # HHI spans 0-10000 — scale it onto the 0-1 axis
                    y_data_hhi = [item.value / 10000 for item in hhiCoefData.data.values()]
                    y_data_normalizedTheil = [item.value for item in normalizedTheilCoefData.data.values()]
                    y_data_normalizedShannonEntropy = [item.value for item in normalizedShannonEntropyCoefData.data.values()]

                    x_data = [datetime.strptime(date, '%Y-%m-%d').date() for date in x_data]

                    y_data_list = [y_data_gini, y_data_hhi, y_data_normalizedTheil, y_data_normalizedShannonEntropy]

                    folderPath = f'/DATA/GENERATED/{subjectOfAnalysis}/{metricType.replace(" ", "_")}/Gini_HHI_NormTheil_NormShannonEntropy'
                    folderPath += f'/{"20XX"+xTicksShowEndsWith}'

                    chart_generator = BaseChartGenerator(
                        x_data=x_data,
                        y_data_list=y_data_list,
                        labels=["Gini", "HHI", "Normalized Theil", "Normalized Shannon Entropy"]
                    )
                    chart_generator.customize_axes(
                        x_label='Time',
                        y_label='Coefficient Value',
                        title=f'Gini, HHI, Normalized Theil, Normalized Shannon Entropy\nof {metricType} centrality (BLN {subjectOfAnalysis})',
                        y_lim=(0, 1.2),
                    )
                    chart_generator.set_x_ticks(ends_with=xTicksShowEndsWith, exclude_ends_with=xTicksToExclude)

                    # STEP 5.1: Full variant — header and footer on
                    chart_generator.generate_line_chart(figsize=figsize, print_header=True, print_footer=True)
                    filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_Full.svg'
                    chart_generator.save_chart(filePath)
                    print(f"[*] Saved: {filePath}")

                    # # NoFooter variant — disabled, not published:
                    # filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_NoFooter.svg'
                    # chart_generator.generate_line_chart(figsize=figsize, print_header=True, print_footer=False)
                    # chart_generator.save_chart(filePath)
                    # print(f"[*] Saved: {filePath}")

                    # STEP 5.2: bare NoHeaderFooter plot for embedding
                    filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_NoHeaderFooter.svg'
                    chart_generator.generate_line_chart(figsize=figsize, print_header=False, print_footer=False)
                    chart_generator.save_chart(filePath)
                    print(f"[*] Saved: {filePath}")

                    # Matplotlib figures pile up fast — force a GC
                    # every iteration to keep the RSS flat.
                    gc.collect()








############################################################
# calculate_gini_from_lorenz
############################################################
#
# Gini coefficient recomputed from Lorenz-curve points:
# takes cumulative population percentiles and cumulative
# value percentages (both 0–100), integrates the curve
# with the trapezoidal rule and returns twice the area
# between it and the equality line.
#
# Gotcha: the endpoint fix-up is asymmetric — a missing
# (0, 0) start is fixed by REBINDING new local lists, but
# a missing (100, 100) end is APPENDED IN PLACE, mutating
# the caller's lists. The only caller always passes lists
# that already end at 100, so the mutation never fires
# today.
#
# Used by:
#   - generateLorenzCharts (below) — only as a printed
#     cross-check against Coefficients()' own Gini values
############################################################

def calculate_gini_from_lorenz(percentiles, cumulative_percentages):
    # Normalize the endpoints: the curve must span (0, 0)
    # to (100, 100) before integrating.
    if percentiles[0] != 0 or cumulative_percentages[0] != 0:
        percentiles = [0] + percentiles
        cumulative_percentages = [0] + cumulative_percentages
    if percentiles[-1] != 100 or cumulative_percentages[-1] != 100:
        percentiles.append(100)
        cumulative_percentages.append(100)

    # Percentages → proportions, then the trapezoidal area
    # under the curve.
    X = [p / 100.0 for p in percentiles]
    Y = [cp / 100.0 for cp in cumulative_percentages]

    area_under_lorenz = 0.0
    for i in range(1, len(X)):
        width = X[i] - X[i - 1]
        height = (Y[i] + Y[i - 1]) / 2.0
        area_under_lorenz += width * height

    # The equality line covers area 0.5; Gini is twice the
    # gap between it and the curve.
    area_between = 0.5 - area_under_lorenz

    gini_coefficient = 2 * area_between

    return gini_coefficient








############################################################
# generateLorenzCharts
############################################################
#
# Lorenz-curve chart per (subject, metric): one curve per
# yearly March snapshot (dateMask 20XX-03-01), each
# labelled "T<n>: <date> (Gini: x.xxx)" with the Gini
# value from Coefficients(). The metric and Gini series
# are archived as JSON like in generateCoefficientCharts
# (different dateMask, so different file names). Charts go
# to /DATA/GENERATED/<subject>/<metric>/Lorenz_Curves/.
#
# Starts at 2018-01-01 — one month earlier than the
# coefficient pipelines.
#
# Every snapshot's Gini is also recomputed from the curve
# via calculate_gini_from_lorenz and printed as a sanity
# cross-check — print only, nothing is stored.
#
# Used by:
#   - workflows.py generate_lorenz_charts (@task) —
#     lightning_network_statistics_flow
#   - main.py --calculate-ln-stats
############################################################

def generateLorenzCharts():
    # STEP 1: fixed chart variations and the analysis
    # matrix — yearly March snapshots only
    # ===============================================
    # dateMasks = ['20XX-03-01', '20XX-06-01', '20XX-09-01', '20XX-12-01']
    dateMasks = ['20XX-03-01']

    figSizes = [(6, 10), (10, 6), (6, 6)]

    subjectsOfAnalysis = ["Nodes", "Entities"]
    # subjectsOfAnalysis = ["Entities"]
    metricTypes = ["weighted degree", "degree"]

    for dateMask in dateMasks:


        # STEP 2: first block of every day matching the mask
        # — note the 2018-01-01 start (see banner)
        # ==================================================
        blockHeightsData = RawDataSelector().get_first_blocks_of_days_by_date_mask(
            startSince='2018-01-01', endUntil=datetime.now().strftime('%Y-%m-%d'), dateMask=dateMask
        )

        for subjectOfAnalysis in subjectsOfAnalysis:
            for metricType in metricTypes:


                # STEP 3: the per-vertex series for this
                # (subject, metric) pair, archived as JSON
                # ========================================
                metricsDataSelector = None
                if(subjectOfAnalysis == "Nodes"):
                    metricsDataSelector = NodeMetricsSelector()
                elif(subjectOfAnalysis == "Entities"):
                    metricsDataSelector = EntityMetricsSelector()

                verticesAspectData = None
                if(metricType == "weighted degree"):
                    verticesAspectData = metricsDataSelector.get_capacity_metrics(blockHeightsData)
                elif(metricType == "degree"):
                    verticesAspectData = metricsDataSelector.get_channel_count_metrics(blockHeightsData)

                filePath = f'/DATA/GENERATED/{subjectOfAnalysis}/{metricType.replace(" ", "_")}/{dateMask}.json'
                verticesAspectData.save_to_file(filePath)
                print(f"[*] Saved: {filePath}")


                # STEP 4: the reference Gini per snapshot — goes
                # into the curve labels and the JSON archive
                # ==============================================
                coefficientType = "Gini"
                coefficientsData = Coefficients().calculate_on_vertices_data(verticesAspectData, coefficientType.replace(" ", ""))
                filePath = f'/DATA/GENERATED/{subjectOfAnalysis}/{metricType.replace(" ", "_")}/{coefficientType.replace(" ", "_")}/{dateMask}.json'
                coefficientsData.save_to_file(filePath)
                print(f"[*] Saved: {filePath}")


                # STEP 5: one Lorenz dataset per snapshot — sort
                # the vertices ascending, build the cumulative
                # percentage curve, label it with the Gini value
                # ==============================================
                datasets = []
                timestampID = 0
                for blockHeight in verticesAspectData.data:
                    timestampID += 1
                    date = verticesAspectData.data[blockHeight].date

                    # Leftover debug output — every block height is
                    # printed on every run.
                    print(blockHeight)
                    nodesmetricsData = verticesAspectData.data[blockHeight].vertices

                    sorted_data = sorted(nodesmetricsData, key=lambda x: x.value)

                    cumulative_sum = [sum(item.value for item in sorted_data[:i+1]) for i in range(len(sorted_data))]

                    # A snapshot with zero vertices would IndexError
                    # here — cumulative_sum[-1] on an empty list.
                    total = cumulative_sum[-1]
                    cumulative_percentages = [x / total * 100 for x in cumulative_sum]

                    percentiles = [(i + 1) / len(sorted_data) * 100 for i in range(len(sorted_data))]

                    giniCoefficient = round(coefficientsData.data[blockHeight].value, 3)
                    datasets.append({
                        'percentiles': percentiles,
                        'cumulative_percentages': cumulative_percentages,
                        'label': f"T{timestampID}: {date} (Gini: {giniCoefficient:.3f})"
                    })

                    # STEP 5.1: print-only Gini cross-check from the curve
                    giniCoefficientFromLorenzCurve = calculate_gini_from_lorenz(percentiles, cumulative_percentages)
                    print(f"T{timestampID}: {date} (GiniFromLorenzCurve: {giniCoefficientFromLorenzCurve})")


                # STEP 6: draw the curves in every canvas size
                # ============================================
                for figsize in figSizes:
                    title, y_label = '', ''
                    if(metricType == 'degree'):
                        title = 'Lorenz curves of degree centrality'
                        y_label = 'Cumulative percentage of channels count'
                    elif(metricType == 'weighted degree'):
                        title = 'Lorenz curves of weighted degree\ncentrality'
                        y_label = 'Cumulative percentage of channels capacity'

                    folderPath = f'/DATA/GENERATED/{subjectOfAnalysis}/{metricType.replace(" ", "_")}/Lorenz_Curves'
                    folderPath += f'/{dateMask}'

                    chart_generator = LorenzCurveChartGenerator(
                        datasets=datasets,
                    )
                    chart_generator.customize_axes(
                        x_label=f'Cumulative percentage of {subjectOfAnalysis.lower()}',
                        y_label=y_label,
                        title=title + f" (BLN {subjectOfAnalysis})",
                        # y_lim=(0, 1.2),
                    )

                    # STEP 6.1: Full variant — header and footer on
                    chart_generator.generate_lorenz_curves(figsize=figsize, print_header=True, print_footer=True)
                    filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_Full.svg'
                    chart_generator.save_chart(filePath)
                    print(f"[*] Saved: {filePath}")

                    # # NoFooter variant — disabled, not published:
                    # filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_NoFooter.svg'
                    # chart_generator.generate_lorenz_curves(figsize=figsize, print_header=True, print_footer=False)
                    # chart_generator.save_chart(filePath)
                    # print(f"[*] Saved: {filePath}")

                    # STEP 6.2: bare NoHeaderFooter plot for embedding
                    filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_NoHeaderFooter.svg'
                    chart_generator.generate_lorenz_curves(figsize=figsize, print_header=False, print_footer=False)
                    chart_generator.save_chart(filePath)
                    print(f"[*] Saved: {filePath}")

                    # Matplotlib figures pile up fast — force a GC
                    # every iteration to keep the RSS flat.
                    gc.collect()








############################################################
# generateExampleLorenzCharts
############################################################
#
# Renders the generator's built-in textbook Lorenz-curve
# illustration (no DB access) in three canvas sizes under
# /DATA/GENERATED/Examples/Lorenz_Curves/ — Full and
# NoHeaderFooter variants. The disabled middle variant is
# mislabelled: it would render header OFF / footer ON yet
# save as _NoFooter.svg. Kept verbatim, it is dead code.
#
# Used by:
#   - workflows.py generate_example_lorenz_charts (@task)
#     — lightning_network_statistics_flow
#   - main.py --calculate-ln-stats
############################################################

def generateExampleLorenzCharts():
    for figsize in [(6, 6), (10, 6), (6, 10)]:

        chart_generator = LorenzCurveChartGenerator()

        # Full variant — header and footer on
        chart_generator.generate_example_lorenz_curve(figsize=figsize, print_header=True, print_footer=True)
        filePath = f'/DATA/GENERATED/Examples/Lorenz_Curves/{figsize[0]}x{figsize[1]}_Full.svg'
        chart_generator.save_chart(filePath)
        print(f"[*] Saved: {filePath}")

        # # NoFooter variant — disabled AND mislabelled (see banner):
        # chart_generator.generate_example_lorenz_curve(figsize=figsize, print_header=False, print_footer=True)
        # filePath = f'/DATA/GENERATED/Examples/Lorenz_Curves/{figsize[0]}x{figsize[1]}_NoFooter.svg'
        # chart_generator.save_chart(filePath)
        # print(f"[*] Saved: {filePath}")

        # Bare NoHeaderFooter plot for embedding
        chart_generator.generate_example_lorenz_curve(figsize=figsize, print_header=False, print_footer=False)
        filePath = f'/DATA/GENERATED/Examples/Lorenz_Curves/{figsize[0]}x{figsize[1]}_NoHeaderFooter.svg'
        chart_generator.save_chart(filePath)
        print(f"[*] Saved: {filePath}")








############################################################
# generateGeneralStatisticsCharts
############################################################
#
# Network-wide totals as monthly line charts: node count,
# total capacity (BTC) and channel count, each in three
# canvas sizes under /DATA/GENERATED/General_Stats/<name>/.
# The series comes from GeneralStats().calculate over the
# monthly capacity and channel-count metrics and is
# archived as General_Stats/20XX-XX-01.json. Also kicks
# off GeneralStats().calculate_channel_lifetime_plot() for
# its side effect.
#
# Unlike the coefficient pipelines there is no
# xTicksToExclude here — only the ends_with March filter
# thins the tick labels.
#
# Used by:
#   - workflows.py generate_general_statistics_charts
#     (@task) — lightning_network_statistics_flow
#   - main.py --calculate-ln-stats
############################################################

def generateGeneralStatisticsCharts():
    # STEP 1: fixed chart variations — March-only x-ticks
    # and three canvas sizes
    # ===================================================
    dateMask = '20XX-XX-01'

    # xTicksToGenerate = ["-03-01", "-06-01", "-09-01", "-12-01"]
    xTicksToGenerate = ["-03-01"]
    figSizes = [(6, 10), (10, 6), (6, 6)]


    # STEP 2: block height of the first block of every
    # month since Feb 2018
    # ================================================
    firstBlocksOfMoths = RawDataSelector().get_first_blocks_of_days_by_date_mask(
        startSince='2018-02-01', endUntil=datetime.now().strftime('%Y-%m-%d'), dateMask=dateMask
    )


    # STEP 3: monthly node metrics folded into the general
    # stats series, archived as JSON; the channel-lifetime
    # plot is generated as a side effect
    # ====================================================
    vertices_capacity_data =        NodeMetricsSelector().get_capacity_metrics(firstBlocksOfMoths)
    vertices_channel_count_data =   NodeMetricsSelector().get_channel_count_metrics(firstBlocksOfMoths)

    from .calculations.general_stats import GeneralStats
    general_stats_data = GeneralStats().calculate(vertices_capacity_data, vertices_channel_count_data)
    general_stats_data.save_to_file(f'/DATA/GENERATED/General_Stats/{dateMask}.json')

    GeneralStats().calculate_channel_lifetime_plot()


    # STEP 4: flatten the series into per-chart arrays
    # ================================================
    date_data = [item.date for item in general_stats_data.data.values()]
    node_count_data = [item.node_count for item in general_stats_data.data.values()]
    node_capacity_data = [item.network_capacity for item in general_stats_data.data.values()]
    channel_count_data = [item.channel_count for item in general_stats_data.data.values()]

    date_data = [datetime.strptime(date, '%Y-%m-%d').date() for date in date_data]


    # STEP 5: render the three charts per tick layout and
    # canvas size — Full and NoHeaderFooter variants, the
    # NoFooter variant disabled like everywhere else
    # ===================================================
    for xTicksShowEndsWith in xTicksToGenerate:
        for figsize in figSizes:

            # STEP 5.1: node count chart
            folderPath = f'/DATA/GENERATED/General_Stats/Node_Count'
            folderPath += f'/{"20XX"+xTicksShowEndsWith}'

            chart_generator = BaseChartGenerator(x_data=date_data, y_data_list=[node_count_data], labels=["Total Number of Nodes"])
            chart_generator.customize_axes(
                x_label='Time',
                y_label="Total Number of Nodes",
                title=f'Total number of BLN nodes in the network'
            )
            chart_generator.set_x_ticks(ends_with=xTicksShowEndsWith)

            chart_generator.generate_line_chart(figsize=figsize, print_header=True, print_footer=True)
            filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_Full.svg'
            chart_generator.save_chart(filePath)
            print(f"[*] Saved: {filePath}")

            # # NoFooter variant — disabled, not published:
            # filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_NoFooter.svg'
            # chart_generator.generate_line_chart(figsize=figsize, print_header=True, print_footer=False)
            # chart_generator.save_chart(filePath)
            # print(f"[*] Saved: {filePath}")

            filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_NoHeaderFooter.svg'
            chart_generator.generate_line_chart(figsize=figsize, print_header=False, print_footer=False)
            chart_generator.save_chart(filePath)
            print(f"[*] Saved: {filePath}")


            # STEP 5.2: network capacity chart (BTC)
            folderPath = f'/DATA/GENERATED/General_Stats/Network_Capacity'
            folderPath += f'/{"20XX"+xTicksShowEndsWith}'

            chart_generator = BaseChartGenerator(x_data=date_data, y_data_list=[node_capacity_data], labels=["Total Network Capacity (BTC)"])
            chart_generator.customize_axes(
                x_label='Time',
                y_label="Total Network Capacity (BTC)",
                title=f'Total network capacity in the BLN network'
            )
            chart_generator.set_x_ticks(ends_with=xTicksShowEndsWith)

            chart_generator.generate_line_chart(figsize=figsize, print_header=True, print_footer=True)
            filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_Full.svg'
            chart_generator.save_chart(filePath)
            print(f"[*] Saved: {filePath}")

            # # NoFooter variant — disabled, not published:
            # filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_NoFooter.svg'
            # chart_generator.generate_line_chart(figsize=figsize, print_header=True, print_footer=False)
            # chart_generator.save_chart(filePath)
            # print(f"[*] Saved: {filePath}")

            filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_NoHeaderFooter.svg'
            chart_generator.generate_line_chart(figsize=figsize, print_header=False, print_footer=False)
            chart_generator.save_chart(filePath)
            print(f"[*] Saved: {filePath}")


            # STEP 5.3: channel count chart
            folderPath = f'/DATA/GENERATED/General_Stats/Channel_Count'
            folderPath += f'/{"20XX"+xTicksShowEndsWith}'

            chart_generator = BaseChartGenerator(x_data=date_data, y_data_list=[channel_count_data], labels=["Total Channel Count"])
            chart_generator.customize_axes(
                x_label='Time',
                y_label="Total Channel Count",
                title=f'Total channel count in the BLN network'
            )
            chart_generator.set_x_ticks(ends_with=xTicksShowEndsWith)

            chart_generator.generate_line_chart(figsize=figsize, print_header=True, print_footer=True)
            filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_Full.svg'
            chart_generator.save_chart(filePath)
            print(f"[*] Saved: {filePath}")

            # # NoFooter variant — disabled, not published:
            # filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_NoFooter.svg'
            # chart_generator.generate_line_chart(figsize=figsize, print_header=True, print_footer=False)
            # chart_generator.save_chart(filePath)
            # print(f"[*] Saved: {filePath}")

            filePath = folderPath + f'/{figsize[0]}x{figsize[1]}_NoHeaderFooter.svg'
            chart_generator.generate_line_chart(figsize=figsize, print_header=False, print_footer=False)
            chart_generator.save_chart(filePath)
            print(f"[*] Saved: {filePath}")








############################################################
# compare_data_sources
############################################################
#
# Thin wrapper: CompareSources does all its work in the
# constructor — instantiating it renders the data-source
# comparison charts as a side effect. March-only tick
# labels, Jan/Feb excluded (a different exclude list than
# the coefficient pipelines use).
#
# Used by:
#   - workflows.py compare_data_sources (@task) —
#     lightning_network_statistics_flow
#   - main.py --calculate-ln-stats
############################################################

def compare_data_sources():
    from blnstats.data_import.compare_sources import CompareSources
    xTicksShowEndsWith = "-03-01"
    xTicksToExclude = ["-01-01", "-02-01"]
    CompareSources(xTicksShowEndsWith, xTicksToExclude)








############################################################
# generateCSV_EntityMetrics
############################################################
#
# CSV export of the entity metrics for external analysis:
# per date mask, one capacity CSV (values divided by 1e8 —
# satoshis to BTC) and one channel-count CSV (raw counts),
# written to /DATA/GENERATED/Entities/<metric>/DATA_CSV/.
#
# Used by:
#   - workflows.py generate_csv_entity_metrics (@task) —
#     lightning_network_statistics_flow, with the masks
#     ['2025-03-01', '20XX-XX-01']
#   - main.py --calculate-ln-stats — the same two masks
############################################################

def generateCSV_EntityMetrics(dateMasks):
    for dateMask in dateMasks:

        blockHeightsStructure = RawDataSelector().get_first_blocks_of_days_by_date_mask(
            dateMask=dateMask,
            startSince='2018-01-01',
            endUntil=datetime.now().strftime('%Y-%m-%d')
        )

        # divideValueBy: satoshis → BTC
        EntityMetricsSelector().get_capacity_metrics(blockHeightsStructure).save_to_csv(
            filePath=f'/DATA/GENERATED/Entities/weighted_degree/DATA_CSV/EntityCapacityDate_{dateMask}.csv',
            divideValueBy=100000000.0
        )

        EntityMetricsSelector().get_channel_count_metrics(blockHeightsStructure).save_to_csv(
            filePath=f'/DATA/GENERATED/Entities/degree/DATA_CSV/EntityChannelCountDate_{dateMask}.csv',
        )








############################################################
# synchronizeBlockchain
############################################################
#
# Brings the local block and transaction tables up to the
# blockchain tip via the Electrum server named in
# BLNSTATS_ELECTRUM_HOST / BLNSTATS_ELECTRUM_PORT (port
# defaults to 50001). Blocks are synced BEFORE and AFTER
# the transaction import: the second pass picks up blocks
# mined while the (long) transaction run was going, so the
# next pipeline step sees a consistent tip.
#
# Used by:
#   - workflows.py synchronize_blockchain (@task) —
#     lightning_network_statistics_flow runs it first
#   - main.py --sync-blockchain
############################################################

def synchronizeBlockchain():
    # STEP 1: catch the block table up to the current tip
    # ===================================================
    from .data_import.blockchain_blocks import BlockchainBlocks
    BlockchainBlocks(
        electrum_host=os.getenv('BLNSTATS_ELECTRUM_HOST'),
        electrum_port=int(os.getenv('BLNSTATS_ELECTRUM_PORT', 50001))
    ).sync_blocks()


    # STEP 2: import the missing transactions — 500 is the
    # importer's blockRange window parameter
    # ====================================================
    from .data_import.blockchain_transactions import BlockchainTransactions
    BlockchainTransactions(
        electrum_host=os.getenv('BLNSTATS_ELECTRUM_HOST'),
        electrum_port=int(os.getenv('BLNSTATS_ELECTRUM_PORT', 50001))
    ).run(500)


    # STEP 3: second block pass — the tip moved while
    # STEP 2 was running
    # ===============================================
    from .data_import.blockchain_blocks import BlockchainBlocks
    BlockchainBlocks(
        electrum_host=os.getenv('BLNSTATS_ELECTRUM_HOST'),
        electrum_port=int(os.getenv('BLNSTATS_ELECTRUM_PORT', 50001))
    ).sync_blocks()








############################################################
# importLNDDBReader
############################################################
#
# Imports an LND DBReader dump (local path or http(s) URL,
# .json.gz) into the _LND_DBReader_* staging tables, then
# folds the announced node aliases into the main tables
# and refreshes the entity clusters derived from them.
#
# Used by:
#   - workflows.py import_lnd_dbreader_data (@task) —
#     lnd_dbreader_import_flow,
#     lnd_dbreader_full_update_flow and
#     full_initialization_flow
#   - main.py --import-lnd-dbreader-data <file_path>
############################################################

def importLNDDBReader(file_path):
    # STEP 1: raw import — LNDDBReader does all its work in
    # the constructor
    # =====================================================
    from .data_import.lnd_dbreader import LNDDBReader
    LNDDBReader(file_path)


    # STEP 2: fold the announced aliases into the main
    # table and rebuild the entity view of them
    # ================================================
    entityObj = EntityClusters()
    entityObj.import_node_aliases_to_main_table(
        from_table_name='_LND_DBReader_NodeAnnouncements',
        from_alias_column='Alias',
        from_node_id_column='NodeID',
        from_timestamp_column='LastSeen'
    )
    entityObj.import_new_entities_to_main_table()
    entityObj.fix_entity_hex_names_if_possible()








############################################################
# importLNResearchData
############################################################
#
# Full LNResearch import: instantiating LNResearchData IS
# the import (download, parse and insert happen in its
# __init__), then the announced aliases are folded into the
# entity tables — the follow-up main.py's
# --import-ln-research-data flag skips.
#
# Used by:
#   - workflows.py import_ln_research_data (@task) —
#     ln_research_import_flow and full_initialization_flow
############################################################

def importLNResearchData():
    # STEP 1: raw import into the staging tables — the
    # constructor runs the whole pipeline
    # ====================================================
    from .data_import.ln_research import LNResearchData
    LNResearchData()


    # STEP 2: fold the announced aliases into the main
    # table and rebuild the entity view of them
    # ================================================
    entityObj = EntityClusters()
    entityObj.import_node_aliases_to_main_table(
        from_table_name='_LNResearch_NodeAnnouncements',
        from_alias_column='Alias',
        from_node_id_column='NodeID',
        from_timestamp_column='LastSeen'
    )
    entityObj.import_new_entities_to_main_table()
    entityObj.fix_entity_hex_names_if_possible()








############################################################
# transformNodeMetrics
############################################################
#
# Rebuilds the per-node metric tables from the raw gossip
# and blockchain data for the first block of every month —
# NodeMetrics().transformForFirstBlocksOfMonths() does the
# actual work (it warns and returns quietly when the
# Blockchain_Blocks table is still empty).
#
# Used by:
#   - workflows.py transform_node_metrics (@task) —
#     lightning_network_statistics_flow, right after the
#     blockchain sync
#   - main.py --calculate-ln-stats — its first step
############################################################

def transformNodeMetrics():
    from .data_transform.node_metrics import NodeMetrics
    nodeMetrics = NodeMetrics()

    nodeMetrics.transformForFirstBlocksOfMonths()
