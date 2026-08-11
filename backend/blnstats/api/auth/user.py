############################################################
#  [*] Auth — flask-login user model over System_Users
#
#  The LoginManager instance the app registers, the User
#  object flask-login keeps in the session, and the two
#  loaders that rebuild it from MySQL. load_user and
#  get_user_by_email are copy-paste twins that differ only
#  in the WHERE column.
############################################################


from flask_login import UserMixin, LoginManager
from ...database.utils import get_db_connection


# create_app() (blnstats/__init__.py) calls init_app() on this
login_manager = LoginManager()









############################################################
# User
############################################################
#
# Session-facing wrapper around one System_Users row.
# UserMixin supplies is_authenticated/is_active — the
# self.authenticated attribute set in __init__ is never
# read by anything (dead).
#
# Used by:
#   - load_user / get_user_by_email (below)
#   - login_user in routes.py login_HTTPPOST — via the
#     object get_user_by_email returns
############################################################

class User(UserMixin):






    ############################################################
    # __init__
    ############################################################
    #
    # Plain field copy. `admin` is carried around but no
    # route checks it yet (checkauth hardcodes admin: 1).
    #
    # Used by:
    #   - load_user / get_user_by_email (below)
    ############################################################

    def __init__(self, id, email, password, admin):
        self.id = id
        self.email = email
        self.password = password
        self.admin = admin
        self.authenticated = False






    ############################################################
    # get_id
    ############################################################
    #
    # flask-login stores this string in the session and
    # hands it back to load_user on every request.
    #
    # Used by:
    #   - flask-login internals — nothing calls it directly
    ############################################################

    def get_id(self):
        return str(self.id)









############################################################
# load_user
############################################################
#
# Rebuilds the User for the session's stored id on every
# authenticated request. Returns None (→ anonymous) unless
# the id matches exactly one row.
#
# Used by:
#   - flask-login via the @login_manager.user_loader hook —
#     nothing calls it directly
############################################################

@login_manager.user_loader
def load_user(user_id):
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(''' 
            SELECT
                ID,
                Email,
                Password,
                Admin
            FROM
                System_Users
            WHERE 
                ID = %s
        ''', [user_id])
        sqlFetchData = cursor.fetchall()
        cursor.close()

        if len(sqlFetchData) != 1:
            return None

        sqlFetchData = sqlFetchData[0]
        return User(sqlFetchData['ID'], sqlFetchData['Email'], sqlFetchData['Password'], sqlFetchData['Admin'])









############################################################
# get_user_by_email
############################################################
#
# Same query as load_user keyed on Email — the login-time
# lookup. Case handling lives at the caller (routes.py
# lowercases first); the SQL comparison itself relies on
# the column's collation.
#
# Used by:
#   - login_HTTPPOST (routes.py) — the only caller
############################################################

def get_user_by_email(email):
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(''' 
            SELECT
                ID,
                Email,
                Password,
                Admin
            FROM
                System_Users
            WHERE 
                Email = %s
        ''', [email])
        sqlFetchData = cursor.fetchall()
        cursor.close()

        if len(sqlFetchData) != 1:
            return None

        sqlFetchData = sqlFetchData[0]
        return User(sqlFetchData['ID'], sqlFetchData['Email'], sqlFetchData['Password'], sqlFetchData['Admin'])
