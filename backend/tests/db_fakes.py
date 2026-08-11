############################################################
#  [*] DB fakes — scripted stand-ins for get_db_connection
#
#  Minimal fakes for the mysql-connector objects the backend
#  touches: a connection whose cursors replay a SCRIPT (one
#  pre-canned result per execute(), shared across every
#  connection built from it) and log every (sql, params)
#  pair for assertions. Supports both cursor styles used in
#  the codebase: "with conn.cursor() as c" and the plain
#  cursor(dictionary=True) + close() of load_user.
#
#  Used by:
#    - test_sync_reliability.py — DB-free sync-driver tests
#    - test_api_auth.py — DB-free login/session tests
############################################################


############################################################
# FakeCursor
############################################################
#
# Replays one scripted result per execute(); fetchone and
# fetchall both hand back whatever the script held for the
# latest execute (an exhausted script yields []). The
# executed list is the assertion hook.
############################################################

class FakeCursor:
    def __init__(self, script, executed, rowcounts=None):
        self.script = script
        self.executed = executed
        self.rowcounts = rowcounts
        self.result = []
        self.rowcount = 1

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        self.result = self.script.pop(0) if self.script else []
        # rowcounts (shared, popped per execute) lets tests drive
        # INSERT IGNORE-style outcomes; default stays 1
        if self.rowcounts:
            self.rowcount = self.rowcounts.pop(0)

    def executemany(self, sql, rows):
        self.executed.append((sql, list(rows)))
        self.result = self.script.pop(0) if self.script else []

    def fetchone(self):
        return self.result

    def fetchall(self):
        return self.result

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False








############################################################
# FakeConn
############################################################
#
# Context-manager connection: every cursor() shares the SAME
# script list and executed log, so a multi-connection driver
# consumes the script in call order across connections.
############################################################

class FakeConn:
    def __init__(self, script, executed, rowcounts=None):
        self.script = script
        self.executed = executed
        self.rowcounts = rowcounts

    def cursor(self, **kwargs):
        return FakeCursor(self.script, self.executed, self.rowcounts)

    def commit(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False
