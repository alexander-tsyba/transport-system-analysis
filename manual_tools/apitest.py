from OSMPythonTools.overpass import overpassQueryBuilder, Overpass
from OSMPythonTools.nominatim import Nominatim

nominatim = Nominatim()
osmAPI = Overpass()

city = input("Area: ")
area = nominatim.query(city).areaId()

query = overpassQueryBuilder(
    area=area,
    elementType=['relation'],
    selector=['"route"="subway"'],
    out='body'
)

result = osmAPI.query(query)

for line in result.elements():
    print(line.tag('name:en'))
    for station in line.members(shallow=False):
        if station.type() == 'node':
            print(station.tag('name:en'))
