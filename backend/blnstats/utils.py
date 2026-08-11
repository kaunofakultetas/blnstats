############################################################
#  [*] Utils — generic pure helpers (UNUSED)
#
#  Small standalone helpers for dates, satoshi formatting
#  and address validation. Dead code: nothing anywhere in
#  the backend imports blnstats.utils — ln_research.py even
#  carries its own private copy of hex_to_onion. The json
#  and Decimal imports below are unused as well.
############################################################


import datetime
import json
from decimal import Decimal
import re
import base64









############################################################
# timestamp_to_datetime_string
############################################################
#
# Unix timestamp → 'YYYY-MM-DD HH:MM:SS' in the SERVER's
# local timezone (fromtimestamp is tz-naive).
#
# Used by:
#   - nothing calls this at the moment
############################################################

def timestamp_to_datetime_string(timestamp):
    dt_object = datetime.datetime.fromtimestamp(timestamp)
    return dt_object.strftime('%Y-%m-%d %H:%M:%S')









############################################################
# hex_to_onion
############################################################
#
# Hex-encoded address bytes → base32 .onion hostname
# (lowercased, base32 '=' padding stripped). ln_research.py
# duplicates this as a private __hex_to_onion instead of
# importing it.
#
# Used by:
#   - nothing calls this at the moment
############################################################

def hex_to_onion(hex_str):
    decoded_bytes = bytes.fromhex(hex_str)
    encoded_base32 = base64.b32encode(decoded_bytes).decode('utf-8').lower().rstrip('=')
    return f"{encoded_base32}.onion"









############################################################
# parse_date
############################################################
#
# 'YYYY-MM-DD' string → datetime.date; raises ValueError on
# any other shape.
#
# Used by:
#   - nothing calls this at the moment
############################################################

def parse_date(date_string):
    return datetime.datetime.strptime(date_string, '%Y-%m-%d').date()









############################################################
# format_satoshis_as_btc
############################################################
#
# Satoshis → '0.00000000 BTC' display string. Plain float
# division — fine for display, not for accounting (the
# Decimal import above was presumably meant for this but is
# never used).
#
# Used by:
#   - nothing calls this at the moment
############################################################

def format_satoshis_as_btc(satoshis):
    btc = satoshis / 100000000
    return f"{btc:.8f} BTC"









############################################################
# safe_divide
############################################################
#
# Division that answers 0 instead of raising on a zero
# denominator.
#
# Used by:
#   - nothing calls this at the moment
############################################################

def safe_divide(numerator, denominator):
    return numerator / denominator if denominator != 0 else 0









############################################################
# is_valid_bitcoin_address
############################################################
#
# Shape-only check for legacy (1…/3…) and bech32 (bc1…)
# address formats — no checksum validation, so a
# well-shaped typo still passes.
#
# Used by:
#   - nothing calls this at the moment
############################################################

def is_valid_bitcoin_address(address):
    pattern = r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[ac-hj-np-z02-9]{39,59}$'
    return bool(re.match(pattern, address))
