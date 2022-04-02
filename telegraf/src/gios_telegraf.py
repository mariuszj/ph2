import argparse

import gios_api as gios
import redis_utils as redis_utils
import telegraf_utils as telegraf
from config import LOCATIONS

REDIS_TELEGRAF_TS_KEY = 'gios_telegraf_ts_{}'
DEFAULT_MAX_REQUESTS = 20

# parse arguments
parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-m", "--max-requests", type=int,
                    help="maximum number of requests to the GIOS API",
                    default=DEFAULT_MAX_REQUESTS)
parser.add_argument("-sl", "--stations-ttl", type=int,
                    help="stations cache ttl",
                    default=gios.DEFAULT_STATIONS_TTL)
parser.add_argument("-nl", "--sensors-ttl", type=int,
                    help="sensors cache ttl",
                    default=gios.DEFAULT_SENSORS_TTL)
parser.add_argument("-vl", "--values-ttl", type=int,
                    help="values cache ttl",
                    default=gios.DEFAULT_VALUES_TTL)
parser.add_argument("-f", "--filters", type=str,
                    help="process only selected sensors",
                    default=','.join(gios.DEFAULT_SENSORS_FILTER))
parser.add_argument("-r", "--redis", type=str,
                    help="redis database connection string",
                    default=redis_utils.DEFAULT_REDIS_URL)
args = parser.parse_args()

# initialize gios api
gios.init(redis_url=args.redis)

# get list of all stations
num_requests = 0
result, collection = gios.StationCollection.get(ttl=args.stations_ttl)
num_requests += result

# find stations closest to selected locations
nearest_stations = collection.find_nearest_stations(LOCATIONS)

# update sensors and values in selected stations
updated_sensors = []
for ns in nearest_stations:
    result = ns.load_sensors(
        ttl=args.sensors_ttl,
        filters=args.filters,
        allow_remote=num_requests < args.max_requests)
    num_requests += result

    for sensor in ns.sensors:
        if num_requests < args.max_requests:
            result = sensor.try_update_value(ttl=args.values_ttl)
            if result > 0:
                num_requests += result
                updated_sensors.append((ns, sensor))

# values that have changed, print in influx format
for station, sensor in updated_sensors:
    key = REDIS_TELEGRAF_TS_KEY.format(sensor.id)
    ts = gios.redis_cache.get(key)
    if ts == sensor.value.date:
        continue

    gios.redis_cache.set(key, sensor.value.date)
    telegraf.print_influxdb_format(
        measurement='gios',
        fields={
            'value': sensor.value.value
        },
        tags={
            'param': sensor.param_code,
            'station': station.id,
            # 'station_name': station.name,
            'city': f"{station.city}",
            # 'address': station.address,
            'district': f"{station.district}",
            'province': f"{station.province}"
        },
        timestamp=sensor.value.epoch())
