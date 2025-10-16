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

# to check column colour, need to create an authentication
# with google sheets. Downloading the file strips colour information.

class TimeTable:
    def __init__(self):
        self.rakes = [Rake(i) for i in range(1,100)] # each rake has an id 1-100
        self.stations = {} # stationName: <Station>

        self.upServices = []
        self.dowServices = []

        self.rakecycles = []

class Rake:
    def __init__(self, id):
        self.rakeId = None
        self.isAC = False
        self.rakeSize = None # How many cars in this rake?
        self.velocity = 1 # can make it a linear model

class RakeCycle:
    # A rake cycle is the set of stations that a particular rake covers in a 
    # day, aka Rake-Link
    def __init__(self):
        self.rake = None
        self.path = {} # {stationID: StationEvent}

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
    def __init__(self, type: ServiceType):
        self.type = type # regular, stabling, multi-service
        self.zone = None # western, central
        self.serviceId = None # a list
        self.direction = None # UP (VR->CCG) or DOWN (CCG to VR)
        self.rakeSizeReq = None # 15 is default?, 12 is specified via "12 CAR", but what are blanks?
        self.needsACRake = False

        # by default each service is active each day
        # AC services have a date restriction
        # "multi-service" services have date restrictions.
        self.activeDates = set(Day) 

        # self.rakeInUseId = None
        self.name = None

        self.initStation = None
        self.finalStation = None
        self.stationPath = [] # stations skipped can be generated.

        # service id after reversal at last station. 
        # Will be used to generate the rake cycle.
        # i.e. the next service integer ID. Will be in
        # the up timetable
        self.linkedTo = None 
    
    def getLastStation(self):
        return self.stationPath[-1]

    def getFirstStation(self):
        return self.stationPath[0]
    
class StationEvent:
    def __init__(self):
        self.platform = None
        self.tArrival = None
        self.tDeparture = None

# Activity at a station is dynamic with time
# The activity is studied to generate rake-cycles
# which is a sequence of station ids for every rake id.
class Station:
    def __init__(self, id, name):
        self.id = id
        self.name = name
        self.large = False # all caps/lowercase
        self.rakeHoldingCapacity = None # max rakes at this station at any given time.
        self.events = {} # {rakeId: [stationEvent]}

# Create a TimeTable object. This is then plotted
# via plotly-dash.
# Algo:
# 1. Create a list of every available service. (each service contains list of stations)
# 2. Pick a rake id. For that rake, begin 
class TimeTableParser:
    rCentralRailwaysPattern = re.compile(r'^[Cc]\.\s*[Rr][Ll][Yy]\.?$')
    rTimePattern = re.compile(r'^(?:[01]\d|2[0-3]):[0-5]\d(?::[0-5]\d)?$')

    def __init__(self, filePathXlsx):
        self.wtt = TimeTable()

        self.wttSheets = []
        self.xlsxToDf(filePathXlsx)
        self.registerStations()
        self.registerServices()

    def xlsxToDf(self, filePathXlsx):
        xlsx = pd.ExcelFile(filePathXlsx)
        for sheet in xlsx.sheet_names:
            # First row is blank, followed by the station row # onwards
            # with skipped=4. skipped=5 removes the extra white row above the main content.
            df = xlsx.parse(sheet, skiprows=4).dropna(axis=1, how='all')
            self.wttSheets.append(df)
            # remove fully blank columns
            
        self.upSheet = self.wttSheets[0]
        self.downSheet = self.wttSheets[1]
    
    # always use cleancol before working with a column
    def cleanCol(self, sheet, colIdx):
        '''Removes whitespace and NaNs from a given column
        Returns a <class 'pandas.core.series.Series'> object'''
        # iloc -> :,colIdx == every row ie. full slice (:) in the column 
        # indexed by colIdx
        clean = sheet.iloc[:, colIdx].dropna().astype(str)

        # are non-NaN entries all whitespace?
        if clean.str.fullmatch(r'\s*').all():
            # return blank column
            return pd.Series(dtype=str)
        
        if (colIdx == 0):
            mask =  clean.str.fullmatch(r'\s*')
            # invert mask to keep non-blank rows
            clean = clean[~mask]
        
        return clean

    def registerStations(self):
        '''Create an object corresponding to every station on the network'''
        sheet = self.upSheet # a dataframe
        stationCol = self.cleanCol(sheet, 0) # 0 column index of station
        # print(stationCol)

        for idx, st_name in enumerate(stationCol[1:-2]): # to skip the linkage line
            st_name = st_name.strip()
            st = Station(idx, st_name)
            print(f"Registering station {st_name}, idx {idx}")
            self.wtt.stations[st_name] = st 

    # First station with a valid time
    # "EX ..."
    # else First station in Stations i.e. VIRAR
    def extractInitStation(self, serviceCol, sheet):
        '''Determines the first arrival station in the service path.
        serviceCol: pandas.Series
        sheet: pandas.Dataframe'''

        # for every column:
        # stop at the first time string
        # in that row, look leftwards for a station name.
        # also check for A, D
        # if station name found, that station is the init station.
        ## if name in self.wtt.stations.keys(): its a starting time
        stationName = None
        for rowIdx, cell in serviceCol.items():
            if TimeTableParser.rTimePattern.match(cell):
                row = sheet.iloc[rowIdx, :].astype(str)
                stationName = str(row.iloc[0]).strip()
                # print(f"{stationName}: {cell}")

                if (not stationName): # ex. virar mismatch
                    # check row above
                    row = sheet.iloc[rowIdx - 1, :].astype(str)
                    stationName = str(row.iloc[0]).strip()
                    # print(f"{stationName}: {cell}")
                break

        station = self.wtt.stations[stationName]
        assert(station)
        return station


    def extractInitialDepot(self, serviceID):
        '''Every service must start at some yard/carshed. These
        are specified in the WTT-Summary Sheet.'''
        


        
        
        
    def extractFinalStation(self, serviceCol):
        # ARRL., Arr, ARR
        # last station with a timing
        # last station in stations, i.e. CCG
        for cell in serviceCol:
            pass

    @staticmethod
    def extractServiceHeader(serviceCol):
        '''Extract service ID and Rake size and zone requirement'''
        SERVICE_ID_LEN = 5
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

            if cell.isdigit() and len(cell) == SERVICE_ID_LEN:
                ids.append(int(cell))
                if (cell.startswith("900")):
                    zone = ServiceZone.SUBURBAN

            # check for CAR
            if "CAR" in cell.upper():
                # print(cell)
                match = re.search(r'(12|15|20|10)\s*CAR', cell, flags=re.IGNORECASE)
                assert match is not None
                rakeSize = match.group()

        return ids, rakeSize, zone

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



    # Regular service columns, we parse:
    # - Stations with arrival and departures.
    def registerServices(self):
        '''Enumerate every possible service, extract arrival-departure timings. Populate
        the Station events. For now, store up and down services seperately
        '''
        UP_TT_NON_DRD_COLUMNS = 949
        sheet = self.upSheet
        serviceCols = sheet.columns

        # create a service object for each service column
        # in UP direction
        for col in serviceCols[2:UP_TT_NON_DRD_COLUMNS]:
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
            service.direction = Direction.UP

            sIds, rakeSize, zone = TimeTableParser.extractServiceHeader(clean)
            # assign service id(s)
            if (not len(sIds)): 
                service.type = ServiceType.STABLING # no SID
            if (len(sIds) > 1):
                service.type = ServiceType.MULTI_SERVICE # multiple SIDs

            service.serviceIds = sIds
            service.rakeSizeReq = rakeSize
            service.zone = zone

            # needs AC?
            # Most AC services have specific dates.
            service.needsACRake = TimeTableParser.extractACRequirement(clean)
            # print(f"{service.serviceIds}: {service.needsACRake}")

            # retrieve the station path 
            service.initStation = self.extractInitStation(clean, sheet)
            print(f"Init station for {service.serviceIds}: {service.initStation.name}")

            # Finally
            self.wtt.upServices.append(service)

            



        




        



TimeTableParser("/home/armaan/Fun-CS/IITB-RAILWAYS-2025/railways-simulator-IITB/SWTT-78_ADDITIONAL_AC_SERVICES_27_NOV_2024-1.xlsx")

# Summary Sheet
# - Contains the serviceID of every rake cycle in the suburban network.
# - Includes info on starting point of the rake (carshed, yard, etc.)
# - Includes info on whether the train is FAST/SLOW (slow: no station skipped. Fast: Some stations skipped)


