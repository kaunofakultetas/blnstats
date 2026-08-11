############################################################
#  [*] Settings — read-only System_Settings dump
#
#  One endpoint that returns the whole System_Settings
#  key/value table as a flat JSON object.
#
#    GET /api/settings — all settings as {Key: Value}
############################################################


from flask import Blueprint, jsonify
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
#   - nothing calls this at the moment — no frontend
#     component requests /api/settings
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
