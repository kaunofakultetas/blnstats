############################################################
#  [*] Settings — the System_Settings key/value store
#
#  Read and write access to System_Settings: the GET dumps
#  the whole table as a flat JSON object, the POST upserts
#  the pairs it is given. The admin UI's Data Source card
#  edits 'LND-DBReader-Source-1' through here — the key the
#  Prefect flows resolve their dump URL from.
#
#    GET  /api/settings — all settings as {Key: Value}
#    POST /api/settings — upsert a {Key: Value} object
############################################################


from flask import Blueprint, jsonify, request
import json

from ...database.utils import get_db_connection
from flask_login import login_required

settings_bp = Blueprint('settings', __name__)









############################################################
# get_settings_HTTPGET
############################################################
#
# GET /api/settings
#
# Returns System_Settings as one {Key: Value} object built
# by MySQL (JSON_OBJECTAGG); an empty table comes back as
# {}. Login required — @settings_bp.route must stay the
# OUTER decorator so the blueprint registers the
# auth-wrapped function, not the bare one.
#
# Used by:
#   - DataSourceSettings.jsx (vite/app/src/systemPages/
#     AdminPages/Flows/Dashboard/components/) — loads the
#     current DBReader dump URL into the field
############################################################

@settings_bp.route('/api/settings', methods=['GET'])
@login_required
def get_settings_HTTPGET():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SELECT JSON_OBJECTAGG(`Key`, `Value`) FROM System_Settings')
            result = cursor.fetchone()[0]

    settings_dict = json.loads(result) if result else {}
    return jsonify(settings_dict)








############################################################
# set_settings_HTTPPOST
############################################################
#
# POST /api/settings
#
# Upserts every pair of the posted {Key: Value} object into
# System_Settings (values coerced to strings). Unknown keys
# are allowed on purpose — the table is a generic store.
# Anything that is not a non-empty JSON object answers
# {type:'error'} with a reason, as does any key or value
# over the columns' 255 characters (strict-mode MySQL would
# otherwise 500 instead of truncating). Login required —
# the route decorator stays OUTER so the blueprint
# registers the auth-wrapped function.
#
# Used by:
#   - DataSourceSettings.jsx (vite/app/src/systemPages/
#     AdminPages/Flows/Dashboard/components/) — saving the
#     DBReader dump URL
############################################################

@settings_bp.route('/api/settings', methods=['POST'])
@login_required
def set_settings_HTTPPOST():
    postData = request.get_json(silent=True)

    if(not isinstance(postData, dict) or len(postData) == 0):
        return jsonify({'type': 'error', 'reason': 'Expected a non-empty JSON object of settings'})

    # both columns are VARCHAR(255) — refuse oversize input
    # with a reason instead of letting strict-mode MySQL 500
    for key, value in postData.items():
        if(len(str(key)) > 255 or len(str(value)) > 255):
            return jsonify({'type': 'error', 'reason': f"Key or value for '{str(key)[:64]}' exceeds 255 characters"})

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            for key, value in postData.items():
                cursor.execute('''
                    INSERT INTO System_Settings (`Key`, `Value`) VALUES (%s, %s)
                    ON DUPLICATE KEY UPDATE `Value` = VALUES(`Value`)
                ''', [key, str(value)])
        conn.commit()

    return jsonify({'type': 'ok'})
