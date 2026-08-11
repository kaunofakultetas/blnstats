############################################################
#  [*] Offline IP → country geolocation
#
#  Country lookup backed by the iwik.org per-country network
#  dumps (https://www.iwik.org/ipcountry/ — e.g. LT.cidr):
#  ./IPGeo/<CC>.cidr holds a country's IPv4 networks and
#  ./IPGeo/<CC>.ipv6 its IPv6 networks, one per line, with
#  '#' comment lines skipped. Everything loads into
#  class-level dicts at IMPORT TIME via the
#  loadGeoNetworks() call at the bottom of this file. The
#  ./IPGeo/ path is relative to the process CWD, not to this
#  file.
#
#  DEAD MODULE at the moment: nothing in the backend imports
#  it, and no IPGeo/ folder ships with the repo — with the
#  folder missing, the os.walk fallback yields an empty file
#  list, so even the import-time load silently does nothing.
############################################################


import os
import ipaddress








############################################################
# IPGeolocation
############################################################
#
# Static-only holder: allNetworks maps address family →
# {countryCode: [network strings]}. getIPCountry is a linear
# scan over every network of every country and re-parses the
# candidate address once per subnet — fine for a handful of
# lookups, slow in bulk.
#
# Used by:
#   - nothing calls this at the moment (no imports anywhere
#     in the backend)
############################################################

class IPGeolocation:
    # Family → {countryCode: [cidr strings]}; filled once at
    # import time by the loadGeoNetworks() call below
    allNetworks = {'IPv4': {}, 'IPv6': {}}






    ############################################################
    # loadGeoNetworks
    ############################################################
    #
    # Fills allNetworks from ./IPGeo/: the extension picks the
    # family (*.cidr → IPv4, *.ipv6 → IPv6) and the name
    # before the first dot is the country code.
    #
    # BUG (documented, not fixed): a file with any OTHER
    # extension leaves addressType == '' yet its lines are
    # still appended — allNetworks[''] raises KeyError, so a
    # single stray file (only .DS_Store is filtered out)
    # crashes the load, and the load runs at module import
    # time.
    #
    # Used by:
    #   - the module-level call at the bottom of this file —
    #     import-time initialization; nothing else
    ############################################################

    @staticmethod
    def loadGeoNetworks():
        cidrFolder = "./IPGeo/"

        # (None, None, []) fallback: a missing folder yields no
        # filenames instead of a StopIteration crash
        filenames = next(os.walk(cidrFolder), (None, None, []))[2]
        for filename in filenames:

            if(filename in [".DS_Store"]):
                continue

            countryCode = filename.split('.')[0]

            addressType = ''
            if(filename.endswith(".cidr")):
                addressType = 'IPv4'
                IPGeolocation.allNetworks['IPv4'][countryCode] = []
            elif(filename.endswith(".ipv6")):
                addressType = 'IPv6'
                IPGeolocation.allNetworks['IPv6'][countryCode] = []

            with open(f"{cidrFolder}/{filename}", "r") as f:
                for line in f.readlines():
                    line = line.strip()
                    if(not line.startswith("#")):
                        if(line != ""):
                            IPGeolocation.allNetworks[addressType][countryCode].append(line)






    ############################################################
    # getIPCountry
    ############################################################
    #
    # Returns the country code of the first loaded network
    # containing ipAddress, or '' when nothing matches (or
    # nothing was loaded at all — see the file header).
    #
    # BUG (documented, not fixed): family detection is naive —
    # any '.' means IPv4, any ':' means IPv6. A .onion address
    # therefore classifies as IPv4 and ipaddress.ip_address()
    # raises ValueError; an address with neither separator
    # leaves addressType == '' and allNetworks[''] raises
    # KeyError. ip_network(..., False) passes strict=False, so
    # dump entries with host bits set are tolerated.
    #
    # Used by:
    #   - nothing calls this at the moment
    ############################################################

    @staticmethod
    def getIPCountry(ipAddress):
        addressType = ''
        if('.' in ipAddress):
            addressType = 'IPv4'
        elif(':' in ipAddress):
            addressType = 'IPv6'

        for countryCode in IPGeolocation.allNetworks[addressType]:
            countrySubnets = IPGeolocation.allNetworks[addressType][countryCode]

            for ipSubnet in countrySubnets:
                if(ipaddress.ip_address(ipAddress) in ipaddress.ip_network(ipSubnet, False)):
                    return countryCode

        return ''








# Import-time side effect: load the network lists the moment
# the module is imported, so importers can call getIPCountry
# straight away
IPGeolocation.loadGeoNetworks()

# Example usage (would also need `import json`, which this
# module does not do):
# print(json.dumps(IPGeolocation.allNetworks, indent=4))
