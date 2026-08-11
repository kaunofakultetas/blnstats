############################################################
#  [*] Auth — login, session probe and administrator CRUD
#
#  Session-cookie authentication on top of flask-login and
#  bcrypt, plus the System_Users administration endpoints.
#  Login is enumeration-safe: unknown emails burn a dummy
#  bcrypt check so timing matches the wrong-password path.
#  NOTE: the @admin_required decorator on the administrator
#  routes is commented out — any logged-in user can manage
#  accounts.
#
#    POST /api/login                — session login
#    GET  /api/checkauth            — session probe, LastSeen
#    GET  /api/admin/administrators — user list
#    POST /api/admin/administrators — insert/update/delete
############################################################


from flask import Blueprint, request, Response
from flask_login import login_user, login_required, current_user
import bcrypt
import json
from datetime import datetime

from .user import get_user_by_email
from ...database.utils import get_db_connection


auth_bp = Blueprint('auth', __name__)









############################################################
# login_HTTPPOST
############################################################
#
# POST /api/login
#
# Validates credentials against System_Users and opens a
# flask-login session. Every failure returns HTTP 200 with
# a plain-text reason — the frontend treats any body other
# than 'OK' as the error message to display. Unknown emails
# still run bcrypt against a fixed dummy hash so response
# timing does not reveal whether the account exists.
#
# Used by:
#   - Login.jsx (vite/app/src/systemPages/PublicPages/
#     Login) — the login form submit
############################################################

@auth_bp.route('/api/login', methods=['POST'])
def login_HTTPPOST():
    postData = request.get_json()

    # field presence only — password quality is the admin form's problem
    if( not postData or (not postData.get('email') and not postData.get('password')) ):
        return "Please enter email and password."

    if( not postData.get('email') ):
        return "Please enter email."

    if( not postData.get('password') ):
        return "Please enter password."


    # emails are stored lowercase — lowercasing here makes login case-insensitive
    thisUserObject = get_user_by_email(postData['email'].lower())
    if(thisUserObject is not None):
        if( bcrypt.checkpw( str.encode(postData.get('password')), str.encode(thisUserObject.password) )):
            login_user(thisUserObject)
            return 'OK'
        return "Incorrect email or password."

    else:
        # burn a real bcrypt verification for unknown emails too — keeps the
        # response time identical to the wrong-password path (anti-enumeration).
        # [:72] because bcrypt >= 4 raises on longer passwords instead of
        # truncating like the old versions did — without it this line 500s
        # on every unknown-email login (the sentence is 86 bytes)
        bcrypt.checkpw( str.encode("This Only Used to prevent time based user enumeration attack, so doing nothing there.")[:72],
                        str.encode('$2b$12$37rvWwtdP/sb.pZwBklPFeUxoH.KWOXIDjTxiiC9awCYpXIB8EbmS') )
        return "Incorrect email or password."









############################################################
# checkauth_HTTPGET
############################################################
#
# GET /api/checkauth
#
# Confirms the session cookie is still valid, returns the
# user's id/email and stamps System_Users.LastSeen. The
# 'admin' field is hardcoded to 1 — current_user.admin is
# ignored, so every logged-in user looks like an admin to
# the frontend.
#
# Used by:
#   - AuthGuard.jsx (vite/app/src) — the auth probe behind
#     every /admin page
############################################################

@auth_bp.route('/api/checkauth', methods=['GET'])
@login_required
def checkauth_HTTPGET():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            user_info = {
                "id": current_user.id,
                "email": current_user.email,
                "admin": 1
            }

            # every successful probe counts as activity
            timeNow = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute('UPDATE System_Users SET LastSeen = %s WHERE ID = %s', [timeNow, current_user.id])
            conn.commit()
            return Response(json.dumps(user_info, indent=4), mimetype='application/json')









############################################################
# usersList_HTTP
############################################################
#
# GET  /api/admin/administrators
# POST /api/admin/administrators
#
# GET returns all System_Users rows as one JSON array built
# by MySQL (JSON_ARRAYAGG); POST multiplexes insert/update
# and delete through the `action` field, with an empty `id`
# meaning insert. Gotchas: an empty table makes
# JSON_ARRAYAGG return NULL, so json.loads(None) raises on
# GET; the 'at least 8 characters' error message only
# actually checks for an EMPTY password; inserts use INSERT
# IGNORE, so a duplicate email silently answers 'ok'; new
# rows get LastSeen = '' (never NULL); and the bcrypt hash
# is computed even when the password is empty or unused.
#
# Used by:
#   - AdministratorsListTable.jsx (vite/app/src/systemPages
#     /AdminPages/AdministratorsList/…) — the GET list
#   - AddEditAdministrator.jsx (same folder) — POST with
#     action insertupdate / delete
############################################################

@auth_bp.route('/api/admin/administrators', methods=['GET', 'POST'])
@login_required
# @admin_required
def usersList_HTTP():
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            if request.method == "GET":
                cursor.execute('''
                    SELECT
                        JSON_ARRAYAGG(
                            JSON_OBJECT(
                                'id',           System_Users.ID,
                                'email',        System_Users.Email,
                                'admin',        System_Users.Admin,
                                'enabled',      System_Users.Enabled,
                                'lastseen',     DATE_FORMAT(System_Users.LastSeen, '%Y-%m-%d %H:%i:%s')
                            )
                        ) AS UsersJSON
                    FROM
                        System_Users
                ''')
                result = cursor.fetchone()[0]
                users_data = json.loads(result)
                return Response(json.dumps(users_data, indent=4), mimetype='application/json')
            elif request.method == "POST":
                postData = request.get_json()

                if(postData['action'] == 'insertupdate'):
                    passwordHash = bcrypt.hashpw(postData['password'].encode('utf-8'), bcrypt.gensalt(rounds=12)).decode("utf-8")

                    if(postData['id'] == ''):
                        # message promises 8 chars but the check only rejects an empty password
                        if(len(postData['password']) == 0):
                            cursor.close()
                            return Response(json.dumps({'type': 'error', 'reason': 'Password must be at least 8 characters long'}), mimetype='application/json')
                        cursor.execute(' INSERT IGNORE INTO System_Users (Email, Password, Admin, Enabled, LastSeen) VALUES (%s,%s,%s,%s,%s) ',
                                        [ postData['email'], passwordHash, postData['admin'], postData['enabled'], '' ])
                    else:
                        # empty password on update means "keep the current one"
                        if(len(postData['password']) != 0):
                            cursor.execute(' UPDATE System_Users SET Password = %s WHERE ID = %s ', [ passwordHash,         postData['id'] ])
                        cursor.execute(' UPDATE System_Users SET Email = %s WHERE ID = %s ',        [ postData['email'],    postData['id'] ])
                        cursor.execute(' UPDATE System_Users SET Admin = %s WHERE ID = %s ',        [ postData['admin'],    postData['id'] ])
                        cursor.execute(' UPDATE System_Users SET Enabled = %s WHERE ID = %s ',      [ postData['enabled'],  postData['id'] ])

                    conn.commit()
                    cursor.close()
                    return Response(json.dumps({'type': 'ok'}), mimetype='application/json')


                elif(postData['action'] == 'delete'):
                    cursor.execute(' DELETE FROM System_Users WHERE ID = %s ', [ postData['id'] ])
                    conn.commit()
                    cursor.close()
                    return Response(json.dumps({'type': 'ok'}), mimetype='application/json')
                cursor.close()
                return Response(json.dumps({'type': 'error'}), mimetype='application/json')
