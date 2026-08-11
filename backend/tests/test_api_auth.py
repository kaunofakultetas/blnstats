############################################################
#  [*] API auth tests — login, session probe, route guards
#
#  Drives the real blueprints (api/auth/routes.py,
#  api/settings/routes.py) through a throwaway Flask app
#  with the DB stubbed: the /api/login contract (HTTP 200 +
#  plain-text reason on every failure, 'OK' on success), the
#  session round-trip into /api/checkauth, and the 401 walls
#  on /api/checkauth and /api/settings for anonymous
#  clients — the /api/settings case is the regression test
#  for the decorator-order fix (route decorator must stay
#  outermost). bcrypt hashes are generated with rounds=4 to
#  keep the suite fast.
#
#  Used by:
#    - runTests.sh (repo root) — "python3 -m unittest discover"
#      over tests/test_*.py
############################################################


import unittest
from unittest.mock import patch

import bcrypt
from flask import Flask

from blnstats.api.auth import routes as auth_routes
from blnstats.api.auth import user as auth_user
from blnstats.api.settings.routes import settings_bp
from db_fakes import FakeConn


PASSWORD = 'correct-horse-battery'
PASSWORD_HASH = bcrypt.hashpw(PASSWORD.encode(), bcrypt.gensalt(rounds=4)).decode()








############################################################
# TestApiAuth
############################################################
#
#   test_login_missing_fields      — the three reason texts
#   test_login_wrong_password      — generic rejection
#   test_login_unknown_email       — same generic rejection
#   test_login_ok_and_checkauth    — full session round-trip
#   test_checkauth_anonymous_401   — guard on the auth probe
#   test_settings_anonymous_401    — decorator-order
#                                    regression guard
############################################################

class TestApiAuth(unittest.TestCase):






    ############################################################
    # setUp
    ############################################################
    #
    # Fresh app per test: real blueprints, real login_manager,
    # throwaway secret key. DB access is patched per test.
    #
    # Used by:
    #   - the unittest runner, before every test method
    ############################################################

    def setUp(self):
        app = Flask(__name__)
        app.secret_key = 'unit-test-only'
        auth_user.login_manager.init_app(app)
        app.register_blueprint(auth_routes.auth_bp)
        app.register_blueprint(settings_bp)
        self.client = app.test_client()






    ############################################################
    # __login
    ############################################################
    #
    # POSTs /api/login with get_user_by_email stubbed to one
    # known account (Admin=0 on purpose — see the checkauth
    # test) and returns the response.
    #
    # Used by:
    #   - the login tests (below)
    ############################################################

    def __login(self, email, password):
        def fake_lookup(looked_up_email):
            if looked_up_email == 'admin@test.lt':
                return auth_user.User(1, 'admin@test.lt', PASSWORD_HASH, 0)
            return None

        with patch.object(auth_routes, 'get_user_by_email', fake_lookup):
            return self.client.post('/api/login', json={'email': email, 'password': password})






    ############################################################
    # test_login_missing_fields
    ############################################################
    #
    # Proves: the three field-presence reasons come back as
    # plain text with HTTP 200 — the frontend treats any body
    # other than 'OK' as the message to display.
    ############################################################

    def test_login_missing_fields(self):
        rv = self.client.post('/api/login', json={})
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.data, b'Please enter email and password.')

        rv = self.client.post('/api/login', json={'password': 'x'})
        self.assertEqual(rv.data, b'Please enter email.')

        rv = self.client.post('/api/login', json={'email': 'a@b.c'})
        self.assertEqual(rv.data, b'Please enter password.')






    ############################################################
    # test_login_wrong_password
    ############################################################
    #
    # Proves: a bad password answers the generic rejection —
    # never a hint that the account exists.
    ############################################################

    def test_login_wrong_password(self):
        rv = self.__login('admin@test.lt', 'not-the-password')
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.data, b'Incorrect email or password.')






    ############################################################
    # test_login_unknown_email
    ############################################################
    #
    # Proves: an unknown account draws the SAME rejection text
    # as a wrong password (anti-enumeration contract).
    ############################################################

    def test_login_unknown_email(self):
        rv = self.__login('nobody@test.lt', PASSWORD)
        self.assertEqual(rv.data, b'Incorrect email or password.')






    ############################################################
    # test_login_ok_and_checkauth
    ############################################################
    #
    # Proves: correct credentials answer 'OK' and the session
    # cookie then satisfies /api/checkauth, which reports the
    # user's id/email — and admin ALWAYS as 1, even though the
    # account was created with Admin=0 (the documented
    # hardcoding in checkauth_HTTPGET; this test pins it so a
    # future fix updates the assertion consciously). Email
    # lookup is stubbed uppercase to prove the lowercasing.
    ############################################################

    def test_login_ok_and_checkauth(self):
        rv = self.__login('ADMIN@test.lt', PASSWORD)
        self.assertEqual(rv.data, b'OK')

        # checkauth: load_user restores the session from the DB
        # (dictionary cursor), the route then stamps LastSeen
        user_row = [{'ID': 1, 'Email': 'admin@test.lt', 'Password': PASSWORD_HASH, 'Admin': 0}]
        with patch.object(auth_user, 'get_db_connection', lambda: FakeConn([user_row], [])), \
             patch.object(auth_routes, 'get_db_connection', lambda: FakeConn([None], [])):
            rv = self.client.get('/api/checkauth')

        self.assertEqual(rv.status_code, 200)
        self.assertEqual(rv.json['email'], 'admin@test.lt')
        self.assertEqual(rv.json['admin'], 1)  # hardcoded — NOT the account's Admin=0






    ############################################################
    # test_checkauth_anonymous_401
    ############################################################
    #
    # Proves: no session cookie -> 401 from the auth probe.
    ############################################################

    def test_checkauth_anonymous_401(self):
        rv = self.client.get('/api/checkauth')
        self.assertEqual(rv.status_code, 401)






    ############################################################
    # test_settings_anonymous_401
    ############################################################
    #
    # Proves: /api/settings rejects anonymous clients. This is
    # the regression guard for the decorator-order bug where
    # @login_required sat ABOVE @settings_bp.route and the
    # endpoint was registered unwrapped (public).
    ############################################################

    def test_settings_anonymous_401(self):
        rv = self.client.get('/api/settings')
        self.assertEqual(rv.status_code, 401)








if __name__ == '__main__':
    unittest.main()
