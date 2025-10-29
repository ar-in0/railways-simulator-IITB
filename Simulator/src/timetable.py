## How to represent a Rake-Cycle after parsing the timetable?
# Option1: Maintain a unique list of station objects per rake cycle. 
# Store arrival times in each station object. Too much repetition.
#
# Option2: A single set of station objects. 
# Currently using option2
# We want to plot the entire journey in a single day, and in particular, 
# during the peak hour
import pandas as pd
import re
from collections import defaultdict

# to check column colour, need to create an authentication
# with google sheets. Downloading the file strips colour information.

# @oct24
# services have start end stations
# rake cycles have start end depot

SERVICE_ID_LEN = 5

class TimeTable:
    def __init__(self):
        # ground truth
        self.xlsxSheets = []
        # self.stationCol = None

        self.rakes = [Rake(i) for i in range(1,100)] # each rake has an id 1-100
        self.stations = {} # stationName: <Station>

        self.upServices = []
        self.downServices = []
        self.suburbanServices = None
        
        self.stationEvents = {} # station: StationEvent
        self.serviceChains = [] # created by following the serviceids across sheets

        # use the service chains to generate station events?
        # wont that reuire another parse of the serviceCols?
        # isnt it better for the service itself to contain station events?
        self.rakecycles = [] # needs timing info
        self.allCyclesWtt = [] # from wtt linked follow

    
    def generateRakeCyclePath(self, rakecycle):
        # Rakecycle contains the serviceIDs of a rake-link.
        # We simply find those services, get the stationpath with 
        print(rakecycle)

    # We have a digraph, with nodes v repreented by 
    # Services, and edge (u,v) rep by `u.linkedTo = v`.
    # Rake-Links are CCs of the graph.
    # Our task is to identify the CCs given a set of Nodes
    # and Edges ie. G = (V, E)
    # Invariants for valid WTT:
    # - No cycles in CCs
    def makeRakeCyclePathsSV(self, services):
        '''
        Build rake-cycle paths by recursively following directed `linkedTo` chains.
        Each service node stores both `prev` and `next` links.
        '''
        idMap = {sid: s for s in services for sid in s.serviceId}
        adj = defaultdict(lambda: {'prev': None, 'next': None})

        # build directed links
        for sv in idMap.values():
            sid = sv.serviceId[0]
            if not sv.linkedTo:
                continue
            try:
                nextId = int(str(sv.linkedTo).strip())
            except ValueError:
                nextId = str(sv.linkedTo).strip()

            if nextId not in idMap:
                continue

            adj[sid]['next'] = nextId
            adj[nextId]['prev'] = sid

        visited = set()

        def followChain(sid, chain):
            if sid in visited or sid not in idMap:
                return
            visited.add(sid)
            chain.append(idMap[sid])
            nxt = adj[sid]['next']
            if nxt:
                followChain(nxt, chain)

        for sid in idMap:
            if sid in visited:
                continue
            if adj[sid]['prev'] is not None:
                continue  # not a starting node
            if adj[sid]['next'] is None:
                continue  # isolated or terminal only

            chain = []
            followChain(sid, chain)
            if chain:
                self.allCyclesWtt.append(chain)

        print(f"Constructed {len(self.allCyclesWtt)} rake-cycle paths.")

    # creates stationEvents
    def generateRakeCycles(self):
        self.suburbanServices.sort(
            key=lambda sv: (
                isinstance(sv.serviceId[0], int),  # False (0) for strings, True (1) for ints
                sv.serviceId[0]                    # then sort by the ID itself
            )
        )
        for sv in self.suburbanServices:
            print(sv)

        self.makeRakeCyclePathsSV(self.suburbanServices)
        print(f"# rake links = {len(self.allCyclesWtt)}")

        for path in self.allCyclesWtt:
            print(f"rakecycle starting with service {path[0].serviceId} has length = {len(path)}")

        # need to link the paths to the rake linkNames
        # wtt.rakeclcyes rc contain the linkname
        # and servicepath. Assign a path in allcycles to
        # rc.servicePath
        # rc.serviceIds contains the service path. [sids]
        for rc in self.rakecycles:
            for path in self.allCyclesWtt:
                if rc.serviceIds[0] == path[0].serviceId:
                    rc.servicePath = path
            if not rc.servicePath:
                print(f"Issue with serviceIdpath: {rc.linkName}") # every rakecycle must be assigned its path by the end.

        # Then for every service in every rakecycle, parse the stationcol 
        # to extract timings and create StationEvents.
        for rc in self.rakecycles:
            for svc in rc.servicePath:
                svc.generateStationEvents()
                assert(svc.events)

        # for rc in self.rakecycles:
        #     self.generateRakeCyclePath(rc) 

    # Summarizes the wtt
    # 1. Total # services
    # 2. Services in up direction
    # 3. Services in down direction
    # 4. num AC services
    # 5. In a certain time-period, how many services runnning?
    def printStatistics(self):
        pass


class Rake:
    '''Physical rake specifications.'''
    def __init__(self, rakeId):
        self.rakeId = rakeId
        self.isAC = False
        self.rakeSize = 12 # How many cars in this rake?
        self.velocity = 1 # can make it a linear model
        self.assignedToLink = None  # which rake-cycle is it used for?

    def __repr__(self):
        return f"<Rake {self.rakeId} ({'AC' if self.isAC else 'NON-AC'}, {self.rakeSize}-car)>"

class RakeCycle:
    # A rake cycle is the set of stations that a particular rake covers in a 
    # day, aka Rake-Link
    def __init__(self, linkName): # linkName comes from summary sheet.
        self.rake = None

        # From parsing summary sheet.
        self.linkName = linkName  # A, B, C etc.
        # self.services = {}       # serviceID: Service
        self.serviceIds = [] # list of serviceIDs that implement this link
        # we want the summary sheet and the wtt to agree always
        self.startDepot = None
        self.endDepot = None

        # for a detailed visualization later.
        # generateRakeCyclePath()

        # from the service list, we can generate all
        # the stationevents associated with a rakecycle.
        # so a rakecycle will have:
        # {st1: [], st2: [], ...}
        # self.path = {} # {stationID: [StationEvent]}
        
        # [list of services in path]. Service contains stationevents.
        self.servicePath = None

    
    def __repr__(self):
        rake_str = self.rake.rakeId if self.rake else 'Unassigned'
        n_services = len(self.services)
        start = self.startDepot if self.startDepot else '?'
        end = self.endDepot if self.endDepot else '?'

        return f"<RakeCycle {self.linkName} ({n_services} services) {start}->{end} rake:{rake_str}>"
    
# const
# The service details must be stored first. After that, 
# a row-wise traversal is done to assign events (which are tarrival,depart pairs)
# Service does not store any timing info!??
# Pick a service column
# Then, for every station row check:
# - is this station accesed? 
# --> If yes, append a refernce to the station to service.stationpath
# --> if no, 

from enum import Enum

# initially we only handle regular suburban trains
# excluding dahanu road services
class ServiceType(Enum):
    REGULAR = 'regular'
    STABLING = 'stabling'
    MULTI_SERVICE = 'multi-service'

class ServiceZone(Enum):
    SUBURBAN = 'suburban'
    CENTRAL = 'central'

class Direction(Enum):
    UP = 'up'
    DOWN = 'down'

class Day(Enum):
    MONDAY = 'monday'
    TUESDAY = 'tuesday'
    WEDNESDAY = 'wednesday'
    THURSDAY = 'thursday'
    FRIDAY = 'friday'
    SATURDAY = 'saturday'
    SUNDAY = 'sunday'

class Service:
    '''Purely what can be extracted from a single column'''
    def __init__(self, type: ServiceType):
        self.rawServiceCol = None
        self.type = type # regular, stabling, multi-service
        self.zone = None # western, central
        self.serviceId = None # a list
        self.direction = None # UP (VR->CCG) or DOWN (CCG to VR)

        self.rakeLinkName = None
        self.rakeSizeReq = None # 15 is default?, 12 is specified via "12 CAR", but what are blanks?
        self.needsACRake = False

        self.initStation = None
        # service id after reversal at last station. 
        # Will be used to generate the rake cycle.
        # i.e. the next service integer ID. Will be in
        # the up timetable
        self.linkedTo = None 
        self.finalStation = None

        self.events = [] # [StationEvents in chronological order]

        # by default each service is active each day
        # AC services have a date restriction
        # "multi-service" services have date restrictions.
        self.activeDates = set(Day) 
        
        # self.name = None


    def generateStationEvents(self):
        sheet = None
        if self.direction == Direction.UP:
            sheet = TimeTableParser.wttSheets[0]
        else:
            sheet = TimeTableParser.wttSheets[1]

        stName = None
        serviceCol = self.rawServiceCol
        for rowIdx, cell in serviceCol.items():
            if TimeTableParser.rTimePattern.match(cell):
                stName= sheet.iat[rowIdx, 0]
                # print(stName)
                # this can be made better
                if pd.isna(stName) or not str(stName).strip():
                    # check row above
                    stName = sheet.iat[rowIdx - 1, 0]
                    if pd.isna(stName) or not str(stName).strip():
                        stName = sheet.iat[rowIdx - 2, 0]
                # stName = str(self.stationCol.iloc[rowIdx]).strip().upper()
                if str(stName).strip() == "M'BAI CENTRAL (L)":
                    # hack special case. 
                    # make names identical in wtt is the right solution
                    stName = "M'BAI CENTRAL(L)" 
                if str(stName).strip() in self.wtt.stations.keys():
                    station = self.wtt.stations[str(stName).strip()]
                    print(f"Last station from time: {str(stName).strip()}")
                    return station
                elif "REVERSED" in str(stName).upper():
                    # print("reversal")
                    # check row above
                    stName= sheet.iat[rowIdx - 1, 0]
                    if pd.isna(stName) or not str(stName).strip():
                        stName = sheet.iat[rowIdx - 2, 0]
                
                # check arrival and departure
                isDwell = True if sheet.iat[rowIdx, 1] == "D" else False
                tDep = cell
                if isDwell: 
                    tArr = str(serviceCol.iloc[rowIdx - 1]).strip()
                    event = StationEvent(stName, self, tArr)
                    event.tDeparture = tDep
                else:
                    event = StationEvent(stName, self, tDep)

                self.events.append(event)

        print(f"For service {self.serviceId}, events are:")
        for ev in self.events:
            print(f"{ev.atStation}: {event.tDeparture}")
                        
    
    def __repr__(self):
        sid = ','.join(str(s) for s in self.serviceId) if self.serviceId else 'None'
        dirn = self.direction.name if self.direction else 'NA'
        zone = self.zone.name if self.zone else 'NA'
        ac = 'AC' if self.needsACRake else 'NON-AC'
        rake = f"{self.rakeSizeReq}-CAR" if self.rakeSizeReq else '?'
        init = self.initStation.name if self.initStation else '?'
        final = self.finalStation.name if self.finalStation else '?'
        linked = self.linkedTo if self.linkedTo else 'None'

        return f"<Service {sid} ({dirn}, {zone}, {ac}, {rake}) {init}->{final} linked:{linked}>"

    def getLastStation(self):
        return self.stationPath[-1]

    def getFirstStation(self):
        return self.stationPath[0]
    
class StationEvent:
    def __init__(self, st, sv, tArr, tDep=None):
        self.atStation = st
        self.ofService = sv

        self.platform = None
        self.tArrival = tArr
        self.tDeparture = tArr

# Activity at a station is dynamic with time
# The activity is studied to generate rake-cycles
# which is a sequence of station ids for every rake id.
class Station:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.large = False # all caps/lowercase
        self.rakeHoldingCapacity = None # max rakes at this station at any given time.
        self.events = {} # {rakelinkName: [stationEvent]}

# Create a TimeTable object. This is then plotted
# via plotly-dash.
# Algo:
# 1. Create a list of every available service. (each service contains list of stations)
# 2. Pick a rake id. For that rake, begin 
class TimeTableParser:
    rCentralRailwaysPattern = re.compile(r'^[Cc]\.\s*[Rr][Ll][Yy]\.?$')
    rTimePattern = re.compile(r'^(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?$')
    rServiceIDPattern = re.compile(r'^\s*\d{5}(?:\b.*)?$', re.IGNORECASE)
    rLinkNamePattern = re.compile(r'^\s*([A-Z]{1,2})\s*(?:\u2020)?\s*$', re.UNICODE) # only match A AK with dagger, i.e. start links
    rEtyPattern = re.compile(r'\bETY\s*\d+\b', re.IGNORECASE)

    # extracted from the WTT parse
    # Finally need store a single source of truth
    # from both the summary and the WTT, so hopefully both match.
    # @290ct: not used
    rakeLinkNames = [] 

    wttSheets = [] # upsheet, downsheet, summary sheets

    def __init__(self, fpWttXlsx, fpWttSummaryXlsx):
        self.wtt = TimeTable()
        self.stationCol = None # df column with stations

        self.xlsxToDf(fpWttXlsx)
        self.registerStations()
        self.registerServices()

        # get timing information too 
        # WTT services must be fully populated 
        # before starting the summary-sheet parse.


        # parse summary sheet
        # generate rakelink summary
        self.parseWttSummary(fpWttSummaryXlsx)


        self.wtt.suburbanServices = self.isolateSuburbanServices()
        # print(self.suburbanServices)
        # for s in self.suburbanServices:
        #     print(s.serviceId)
    
    def isolateSuburbanServices(self):
        suburbanIds = set()
        print("Updating suburban")
        seen, repeated = set(), set()
        for rc in self.wtt.rakecycles:
            print(rc.serviceIds)
            suburbanIds.update(rc.serviceIds)
            s = set(rc.serviceIds)
            repeated |= seen & s
            seen |= s
        print(repeated)
        
        suburbanServices = []
        for s in (self.wtt.upServices + self.wtt.downServices):
            if any(sid in suburbanIds for sid in s.serviceId):
                suburbanServices.append(s)

        print(f"\nSuburban services identified: {len(suburbanServices)} / {len(self.wtt.upServices) + len(self.wtt.downServices)}")
        return suburbanServices

    def parseRakeLinks(self, sheet):
        unmatchedIds = []
        allServices = self.wtt.upServices + self.wtt.downServices
        print(len(allServices))
        sheet = sheet.reset_index(drop=True)

        print(f"Summary sheet rows: {len(sheet)}")

        for i in range(len(sheet)):
            sIDRow = sheet.iloc[i]

            # check for linkname
            if pd.isna(sIDRow.iloc[1]):
                continue

            linkName = str(sIDRow.iloc[1]).strip().upper()
            if not TimeTableParser.rLinkNamePattern.match(linkName):
                continue

            # collect all valid service IDs in this row
            # in order
            sIds = []
            for cell in sIDRow.iloc[2:]:
                if pd.isna(cell):
                    continue
                cell = str(cell)
                
                # use the serviceID idiom
                if TimeTableParser.isServiceID(cell):
                    print("found sids")
                    # numeric or ETY-style
                    matchEty = TimeTableParser.rEtyPattern.search(cell)
                    if matchEty:
                        sIds.append(matchEty.group(0))  # store the ETY token as string
                    else:
                        print("no ety")
                        print(cell)
                        sIds.append(int(re.search(r'\d+', cell).group())) # extract the integer ex 93232 L/SPL

            if not sIds:
                continue

            rc = RakeCycle(linkName)

            for sid in sIds:
                service = next((s for s in allServices if sid in s.serviceId), None)
                if service:
                    # rc.services[sid] = service # unordered, does not maintain the path
                    rc.serviceIds.append(sid)
                else:
                    unmatchedIds.append((linkName, sid))

            self.wtt.rakecycles.append(rc)

        # summary
        if unmatchedIds:
            print(f"\n{len(unmatchedIds)} service IDs from summary sheet not found in detailed WTT:")
            for linkName, sid in unmatchedIds:
                print(f" ** Link {linkName}: Service {sid}")
        else:
            print("\nAll rake link service IDs successfully matched with WTT services.")
    
    def parseWttSummary(self, filePathXlsx):
        xlsx = pd.ExcelFile(filePathXlsx)
        summarySheet = xlsx.sheet_names[0]
        self.wttSummarySheet = xlsx.parse(summarySheet, skiprows=2).dropna(axis=0, how="all") # drop fully blank rows
        
        self.parseRakeLinks(self.wttSummarySheet)

    def xlsxToDf(self, filePathXlsx):
        xlsx = pd.ExcelFile(filePathXlsx)
        for sheet in xlsx.sheet_names:
            # First row is blank, followed by the station row # onwards
            # with skipped=4. skipped=5 removes the extra white row above the main content.
            df = xlsx.parse(sheet, skiprows=4).dropna(axis=1, how='all')
            TimeTableParser.wttSheets.append(df)
            # remove fully blank columns
            
        self.upSheet = TimeTableParser.wttSheets[0]
        self.downSheet = TimeTableParser.wttSheets[1]
    
    # always use cleancol before working with a column
    def cleanCol(self, sheet, colIdx):
        '''Return the column as-is unless it is entirely NaN or whitespace.'''
        clean = sheet.iloc[:, colIdx].astype(str)

        # Check if all entries are NaN or whitespace (after conversion to str)
        if clean.isna().all() or clean.str.fullmatch(r'(nan|\s*)', na=False).all():
            return pd.Series(dtype=str)

        # if (colIdx == 0):
        #     mask =  clean.str.fullmatch(r'\s*')
        #     # invert mask to keep non-blank rows
        #     clean = clean[~mask]

        return clean

    def registerStations(self):
        '''Create an object corresponding to every station on the network'''
        sheet = self.upSheet # a dataframe
        self.stationCol = sheet.iloc[:, 0]
        # self.stationCol = self.cleanCol(sheet, 0) # 0 column index of station
        # print(stationCol)
        # print((self.stationCol[1:-8])) 

        for idx, rawVal in enumerate(self.stationCol[1:-8]): # to skip the linkage line + nans
            if pd.isna(rawVal):
                continue
            stName = str(rawVal).strip()
            if not stName:
                continue
            
            st = Station(idx, stName.upper())
            print(f"Registering station {st.name}, idx {st.id}")
            self.wtt.stations[st.name] = st 
        
        # create station map
        TimeTableParser.stationMap = {
            "BDTS": self.wtt.stations["BANDRA"],
            "BA": self.wtt.stations["BANDRA"],
            "MM": self.wtt.stations["MAHIM JN."],
            "ADH": self.wtt.stations["ANDHERI"],
            "KILE": self.wtt.stations["KANDIVALI"],
            "BSR": self.wtt.stations["BHAYANDAR"],
            "DDR": self.wtt.stations["DADAR"],
            "VR": self.wtt.stations["VIRAR"],
            "BVI": self.wtt.stations["BORIVALI"],
            "CSTM": Station(43, "CHATTRAPATI SHIVAJI MAHARAJ TERMINUS"),
            "CSMT": Station(44, "CHATTRAPATI SHIVAJI MAHARAJ TERMINUS"),
            "PNVL": Station(45, "PANVEL")
        }

    # First station with a valid time
    # "EX ..."
    # else First station in Stations i.e. VIRAR
    def extractInitStation(self, serviceCol, sheet):
        '''Determines the first arrival station in the service path.
        serviceCol: pandas.Series
        sheet: pandas.Dataframe'''
        # print(serviceCol)

        # for every column:
        # stop at the first time string
        # in that row, look leftwards for a station name.
        # also check for A, D
        # if station name found, that station is the init station.
        ## if name in self.wtt.stations.keys(): its a starting time
        stationName = None
        for rowIdx, cell in serviceCol.items():
            if TimeTableParser.rTimePattern.match(cell):
                stationName = sheet.iat[rowIdx, 0]
                # row = sheet.iloc[rowIdx, :].astype(str)
                # stationName = row.iloc[0]
                # print(f"{stationName}: {cell}")

                if pd.isna(stationName) or not str(stationName).strip():
                    # check row above if possible
                    if rowIdx > 0:
                        stationName = sheet.iat[rowIdx - 1, 0]
                break

        if pd.isna(stationName) or not str(stationName).strip():
            raise ValueError(f"Invalid station name near row {rowIdx}")
        
        # print(self.wtt.stations.keys())
        if stationName == "M'BAI CENTRAL (L)":
            # hack special case. 
            # make names identical in wtt is the right solution
            stationName = "M'BAI CENTRAL(L)" 

        station = self.wtt.stations[stationName.strip().upper()]
        assert(station)
        return station
        
    def extractFinalStation(self, serviceCol, sheet):
        # ARRL., Arr, ARR
        # last station with a timing
        # last station in stations, i.e. CCG

        # If some cell contains "Arrl./arrl/ARRL/ARR":
        # check for a name in stationmap and a time in nearby cells
        # "nearby cells": current cell, cell above, cell below.
        # (if the stationmap doesnt contain the string, print it)

        # else:
        # return the station associated with the last time
        abbrStations = TimeTableParser.stationMap.keys()
        station = None
        arrlRowIdx = None

        # Find the "ARR" / "ARRL." marker first
        for rowIdx, cell in serviceCol.items():
            cellStr = str(cell).strip().upper()
            if re.search(r'\bARRL?\.?\b', cellStr, flags=re.IGNORECASE):
                # print("found arr")
                arrlRowIdx = rowIdx
                break

        # If arrl not found:
        if not arrlRowIdx:
            # arrl station not explicitly written, 
            # use the station with last mentioned timing
            for rowIdx in reversed(serviceCol.index):
                cell = str(serviceCol.iloc[rowIdx]).strip()
                if TimeTableParser.rTimePattern.match(cell):
                    stName= sheet.iat[rowIdx, 0]
                    # print(stName)
                    # this can be made better
                    if pd.isna(stName) or not str(stName).strip():
                        # check row above
                        stName = sheet.iat[rowIdx - 1, 0]
                        if pd.isna(stName) or not str(stName).strip():
                            stName = sheet.iat[rowIdx - 2, 0]
                    # stName = str(self.stationCol.iloc[rowIdx]).strip().upper()
                    if str(stName).strip() == "M'BAI CENTRAL (L)":
                        # hack special case. 
                        # make names identical in wtt is the right solution
                        stName = "M'BAI CENTRAL(L)" 
                    if str(stName).strip() in self.wtt.stations.keys():
                        station = self.wtt.stations[str(stName).strip()]
                        print(f"Last station from time: {str(stName).strip()}")
                        return station
                    elif "REVERSED" in str(stName).upper():
                        # print("reversal")
                        # check row above
                        stName= sheet.iat[rowIdx - 1, 0]
                        if pd.isna(stName) or not str(stName).strip():
                            stName = sheet.iat[rowIdx - 2, 0]
                        station = self.wtt.stations[str(stName).strip()]
                        print(f"Last station from time,: {str(stName).strip()}")
                        return station


            print("Could not determine final station (no ARRL or valid time)")
            return station
        
        # arrl found, now look in nearby cells for a station
        nearbyRows = [arrlRowIdx]
        if arrlRowIdx > 0:
            nearbyRows.append(arrlRowIdx - 1)
        if arrlRowIdx < len(serviceCol) - 1:
            nearbyRows.append(arrlRowIdx + 1)

        stationName = None
        for r in nearbyRows:
            cellVal = str(serviceCol.iloc[r]).strip().upper()
            print(f"'{cellVal}'")
            if not cellVal or cellVal == 'NAN':
                continue

            # does it contain a station abbreviation?
            for stKey in abbrStations:
                # allow substring match (e.g. "CCG ARR." -> finds "CCG")
                if stKey in cellVal:
                    stationName = stKey
                    break

            if stationName:
                # found a valid station in/near the ARRL region
                print(f"found stationname {stationName} from row {r}: {cellVal}")
                station = TimeTableParser.stationMap[stationName]
                # print(station)
                return station

            # if not found, print the cell for debugging
            print(f"No station match near ARRL at row {r}: {cellVal}")
        

    def extractInitialDepot(self, serviceID):
        '''Every service must start at some yard/carshed. These
        are specified in the WTT-Summary Sheet.'''
        pass

    def extractLinkedToNext(self, serviceCol, direction):
        '''Find the linked service (if any) following a 'Reversed as' entry.'''
        # dropNa
        serviceCol = serviceCol.dropna()
        mask = self.stationCol.str.contains("Reversed as", case=False, na=False)
        match = self.stationCol[mask]

        if match.empty:
            return None

        rowIdx = match.index[0]
        print(rowIdx)
        # print(serviceCol)

        # Guard
        if rowIdx not in serviceCol.index:
            return None

        # for lower sheet, the idx are idx -1, idx
        if (direction == Direction.UP):
            depTime = serviceCol.loc[rowIdx]
            linkedService = serviceCol.loc[rowIdx + 1]
        else:
            depTime = serviceCol.loc[rowIdx -1]
            linkedService = serviceCol.loc[rowIdx]


        # Convert safely, handle NaN/None/float cases
        if pd.isna(linkedService) or pd.isna(depTime):
            return None

        depTime = str(depTime).strip()
        linkedService = str(linkedService).strip()

        # Skip empty, non-sid
        match = linkedService.isdigit() and len(linkedService) == SERVICE_ID_LEN
        if not depTime or depTime.lower() == "nan" or not linkedService or linkedService.lower() == "nan" or not match:
            linkedService = None

        print(f"Linked to: {linkedService} at {depTime}")
        return linkedService
    
    @staticmethod
    def isServiceID(cell): # cell must be str
        # if empty, return False
        if not cell or cell.strip().lower() == "nan":
            return False
        # service IDs may be ETY <integer>
        # or 5-long positive integer + <some optional text>
        return bool(
            TimeTableParser.rServiceIDPattern.match(cell) or
            TimeTableParser.rEtyPattern.search(cell)
            )
    
    # @staticmethod
    def isRakeLinkName(cell):
        if not cell or cell.strip().lower() == "nan":
            return False
        
        # if 2 letter, but in the stationmap, its not a linkname
        # but its the 
        # Currently, matches only AB with dagger so the stationmap check is
        # redundant.
        match = TimeTableParser.rLinkNamePattern.match(cell)
        if match:
            # if match.group(0) in TimeTableParser.stationMap:
            #     return False
            # else:
            return True # 2 letter string not in the station map

    @staticmethod
    def extractServiceHeader(serviceCol):
        '''Extract service ID and Rake size and zone requirement'''
        # Isolate the 5-6 rows below row# of stations in the various columns
        # Then parse again, 
        # Any integer is the service id 
        # if more integers, process them in a second pass
        # as special services. (where you consider dates, etc.)
        idRegion =  serviceCol[:6]
        # print(idRegion)
        ids = []
        rakeSize = 15 # default size
        zone = None
        for cell in idRegion: # cell contents are always str
            cell = cell.strip()
            if TimeTableParser.rCentralRailwaysPattern.match(cell):
                zone = ServiceZone.CENTRAL

            # return true 
            if TimeTableParser.isServiceID(cell):
                # numeric or ETY-style
                matchEty = TimeTableParser.rEtyPattern.search(cell)
                if matchEty:
                    ids.append(matchEty.group(0))  # store the ETY token as string
                else:
                    ids.append(int(re.search(r'\d+', cell).group())) # extract the integer ex 93232 L/SPL
                    if (cell.startswith("9")):
                        zone = ServiceZone.SUBURBAN
            
            # get the linkName
            # Assume WTT linknames are inaccurate - retrieve from the summary sheet.
            linkName = None
            # if TimeTableParser.isRakeLinkName(cell): # XX, and optionally a cross
            #     match = TimeTableParser.rLinkNamePattern.search(cell) # extract the XX
            #     if match:
            #         linkName = match.group(1)
            #         print(f"Rake Link Name: {linkName}")
            #         # record it
            #         TimeTableParser.rakeLinkNames.append(linkName)

            # check for CAR
            if "CAR" in cell.upper():
                # print(cell)
                match = re.search(r'(12|15|20|10)\s*CAR', cell, flags=re.IGNORECASE)
                assert match is not None
                rakeSize = int(match.group(1))

        return ids, rakeSize, zone, linkName

    @staticmethod
    def extractACRequirement(serviceCol):
        isAC = -1
        for cell in serviceCol:
            cell = cell.strip()
            if (isAC == 1): return True  
            if ("Air" in cell or "Condition" in cell):
                isAC += 1
        return False
    
    @staticmethod
    def extractActiveDates(serviceCol):
        pass

    def doRegisterServices(self, sheet, direction, numCols):
        serviceCols = sheet.columns
        for col in serviceCols[2:numCols]:
            idx = serviceCols.get_loc(col)
            clean = self.cleanCol(sheet, idx)
            # print(clean)
            if (clean.empty):
                continue
            # skip repeat STATION columns
            if (not clean.empty and clean.iloc[0].strip().upper() == "STATIONS"):
                print("repeat stations")
                continue

            # check for an ADAD column
            vals = clean.dropna().astype(str).str.strip().str.upper().tolist()
            isADAD = any(a == "A" and b == "D" for a, b in zip(vals, vals[1:]))
            if(isADAD):
                print("adad column, skip") # ideally eliminate from the sheet before
                continue
            
            # if we are here, the column is a service column
            # extract service ID and 
            service = Service(ServiceType.REGULAR)
            service.direction = direction
            service.rawServiceCol = clean

            sIds, rakeSize, zone, linkName = TimeTableParser.extractServiceHeader(clean)
            # assign service id(s)
            if (not len(sIds)): 
                service.type = ServiceType.STABLING # no SID
            if (len(sIds) > 1):
                service.type = ServiceType.MULTI_SERVICE # multiple SIDs

            service.serviceId = sIds
            service.rakeSizeReq = rakeSize
            service.zone = zone
            # service.rakeLinkName = linkName # initially None

            # needs AC?
            # Most AC services have specific dates.
            service.needsACRake = TimeTableParser.extractACRequirement(clean)
            # print(f"{service.serviceId}: {service.needsACRake}")

            # retrieve the station path 
            service.initStation = self.extractInitStation(clean, sheet)
            print(f"Init station for {service.serviceId}: {service.initStation.name}")

            service.finalStation = self.extractFinalStation(clean, sheet)
            if (service.finalStation):
                print(f"Final Station for {service.serviceId}: {service.finalStation.name}")

            service.linkedTo = self.extractLinkedToNext(clean, direction)
            print(f"Service {service.serviceId} linked to service: {service.linkedTo}")
            print(service)

            if direction == Direction.UP:
                self.wtt.upServices.append(service)
            elif direction == Direction.DOWN:
                self.wtt.downServices.append(service)
            else:
                print("No other possibility")
        
    # Regular service columns, we parse:
    # - Stations with arrival and departures.
    def registerServices(self):
        '''Enumerate every possible service, extract arrival-departure timings. Populate
        the Station events. For now, store up and down services seperately
        '''
        UP_TT_COLUMNS = 949 # with uniform row indexing, last = 91024
        upSheet = self.upSheet
        self.doRegisterServices(upSheet, Direction.UP, UP_TT_COLUMNS)
        

        print("Now register down services")
        downSheet = self.downSheet
        DOWN_TT_COLUMNS = 982 # with uniform row indexing, last = 91055
        self.doRegisterServices(downSheet, Direction.DOWN, DOWN_TT_COLUMNS)
        print("Down services registered")

        # print(len(TimeTableParser.rakeLinkNames))
        # print("AL" in TimeTableParser.rakeLinkNames)

        
if __name__ == "__main__":
    wttPath = "/home/armaan/Fun-CS/IITB-RAILWAYS-2025/railways-simulator-IITB/SWTT-78_ADDITIONAL_AC_SERVICES_27_NOV_2024-1.xlsx"
    wttSummaryPath = "/home/armaan/Fun-CS/IITB-RAILWAYS-2025/railways-simulator-IITB/LINK_SWTT_78_UPDATED_05.11.2024-4.xlsx"
    parsed = TimeTableParser(wttPath, wttSummaryPath)

    parsed.wtt.generateRakeCycles()

    # parsed.verify()
    
    parsed.wtt.printStatistics()


# Summary Sheet
# - Contains the serviceID of every rake cycle in the suburban network.
# - Includes info on starting point of the rake (carshed, yard, etc.)
# - Includes info on whether the train is FAST/SLOW (slow: no station skipped. Fast: Some stations skipped)


