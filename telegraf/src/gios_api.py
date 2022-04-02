from json_encoder import SimpleJsonEncoder
from datetime import datetime
from geopy import distance
from typing import Dict, Optional, Union, List, Tuple
import json
import redis_utils as redis_utils
import requests

GIOS_API_URL = 'https://api.gios.gov.pl/pjp-api/rest'
STATIONS_URL = GIOS_API_URL + '/station/findAll'
SENSORS_URL = GIOS_API_URL + '/station/sensors/{}'
SENSOR_VALUES_URL = GIOS_API_URL + '/data/getData/{}'
DEFAULT_SENSORS_FILTER = ['PM2.5', 'PM10']

REDIS_STATIONS_KEY = 'gios_stations'
REDIS_SENSORS_KEY = 'gios_sensors_{}'
REDIS_VALUE_KEY = 'gios_value_{}'

DEFAULT_STATIONS_TTL = 86400  # 24 hours
DEFAULT_SENSORS_TTL = 86400  # 24 hours
DEFAULT_VALUES_TTL = 900  # 15 minutes

redis_cache = None


def init(redis_url: Optional[str] = redis_utils.DEFAULT_REDIS_URL):
    global redis_cache
    redis_cache = redis_utils.redis_init_from_url(url=redis_url)


def geodestic_distance(
        l1: Tuple[Union[int, float], Union[int, float]],
        l2: Tuple[Union[int, float], Union[int, float]]):
    if not isinstance(l1, tuple) or len(l1) < 2 or \
            not isinstance(l2, tuple) or len(l2) < 2:
        raise TypeError("location must be tuple or list")
    return distance.distance(l1, l2)


def distance_in_meters(
        l1: Tuple[Union[int, float], Union[int, float]],
        l2: Tuple[Union[int, float], Union[int, float]]):
    return geodestic_distance(l1, l2).meters


def distance_in_km(
        l1: Tuple[Union[int, float], Union[int, float]],
        l2: Tuple[Union[int, float], Union[int, float]]):
    return geodestic_distance(l1, l2).km


class Sensor:
    def __init__(self):
        self.id = None
        self.param_code = None
        self.value = None

    @staticmethod
    def from_json(json_dict: Dict):
        sensor = Sensor()
        sensor.id = json_dict['id']
        if 'param' in json_dict.keys():
            param = json_dict['param']
            sensor.param_id = param['idParam']
            sensor.param_code = param['paramCode']
        else:
            sensor.param_id = json_dict['param_id']
            sensor.param_code = json_dict['param_code']

        return sensor

    def try_update_value(self, ttl: Optional[int] = DEFAULT_VALUES_TTL):
        key = REDIS_VALUE_KEY.format(self.id)
        if not redis_cache.exists(key):
            self.update_value(ttl)
            return 1
        else:
            return 0

    def update_value(self, ttl: Optional[int] = DEFAULT_VALUES_TTL):
        url = SENSOR_VALUES_URL.format(self.id)
        json_dict = requests.get(url).json()

        value = None
        for val in json_dict['values']:
            sensor_value = SensorValue.from_json(val)
            if sensor_value.value is not None:
                value = sensor_value
                break

        if value is not None:
            self.value = value
            self.cache_value(ttl)
            return True
        else:
            return False

    def cache_value(self, ttl: Optional[int] = DEFAULT_VALUES_TTL):
        json_str = json.dumps(self.value, cls=SimpleJsonEncoder)
        key = REDIS_VALUE_KEY.format(self.id)
        redis_cache.set(key, json_str, ex=ttl)


class SensorValue:
    def __init__(self):
        self.value = None
        self.date = None

    @staticmethod
    def from_json(json_dict: Dict):
        val = SensorValue()
        val.date = json_dict['date']
        val.value = json_dict['value']
        return val

    def epoch(self):
        dt = datetime.strptime(self.date, '%Y-%m-%d %H:%M:%S')
        return int(round(dt.timestamp() * 1000000000))


class Station:
    def __init__(self):
        self.sensors = []

    @staticmethod
    def from_json(json_dict: Dict):
        station = Station()
        station.id = json_dict['id']
        if 'stationName' in json_dict.keys():
            station.name = json_dict['stationName']
            station.lat = float(json_dict['gegrLat'])
            station.lon = float(json_dict['gegrLon'])
            station.address = json_dict['addressStreet']
            city_dict = json_dict['city']
            station.city = city_dict['name']
            commune_dict = city_dict['commune']
            station.district = commune_dict['districtName']
            station.province = commune_dict['provinceName']
        else:
            station.name = json_dict['name']
            station.lat = float(json_dict['lat'])
            station.lon = float(json_dict['lon'])
            station.address = json_dict['address']
            station.city = json_dict['city']
            station.district = json_dict['district']
            station.province = json_dict['province']

        return station

    def load_sensors(
            self,
            filters: Optional[List[str]] = DEFAULT_SENSORS_FILTER,
            ttl: Optional[int] = DEFAULT_SENSORS_TTL,
            allow_remote: Optional[bool] = True):
        result = 0
        self.load_sensors_from_cache()
        if not self.sensors and allow_remote:
            self.load_sensors_from_server(filters, ttl)
            result = 1

        return result

    def load_sensors_from_cache(self):
        key = REDIS_SENSORS_KEY.format(self.id)
        if redis_cache.exists(key):
            json_dict = json.loads(redis_cache.get(key))

            self.sensors = []
            for entry in json_dict:
                sensor = Sensor.from_json(entry)
                self.sensors.append(sensor)

    def load_sensors_from_server(
            self,
            filters: Optional[List[str]] = DEFAULT_SENSORS_FILTER,
            ttl: Optional[int] = DEFAULT_SENSORS_TTL):
        url = SENSORS_URL.format(self.id)
        json_dict = requests.get(url).json()

        self.sensors = []
        for s in json_dict:
            sensor = Sensor.from_json(s)
            if sensor.param_code in filters:
                self.sensors.append(sensor)

        self.cache_sensors(ttl)

    def cache_sensors(self, ttl: Optional[int] = DEFAULT_SENSORS_TTL):
        key = REDIS_SENSORS_KEY.format(self.id)
        redis_cache.set(key, json.dumps(
            self.sensors, cls=SimpleJsonEncoder), ex=ttl)


class StationCollection:
    def __init__(self):
        self.stations = []

    @staticmethod
    def get(ttl: Optional[int] = DEFAULT_STATIONS_TTL,
            allow_remote: Optional[bool] = True):
        result = 0
        collection = StationCollection.from_cache()
        if allow_remote:
            collection = StationCollection.from_server(ttl)
            result = 1

        return result, collection

    @staticmethod
    def from_json(json_dict: Dict):
        collection = StationCollection()
        for entry in json_dict:
            station = Station.from_json(entry)
            collection.stations.append(station)

        return collection

    @staticmethod
    def from_cache():
        if redis_cache.exists(REDIS_STATIONS_KEY):
            json_dict = json.loads(redis_cache.get(REDIS_STATIONS_KEY))
            return StationCollection.from_json(json_dict)
        else:
            return StationCollection()

    @ staticmethod
    def from_server(ttl: Optional[int] = DEFAULT_STATIONS_TTL):
        json_dict = requests.get(STATIONS_URL).json()
        collection = StationCollection.from_json(json_dict)
        collection.cache_stations(ttl)
        return collection

    def find_nearest_stations(self, locations: List[Union[tuple, list]]):
        if isinstance(locations, list):
            stations = []
            for location in locations:
                sorted_stations = sorted(
                    self.stations, key=lambda station,
                    loc=location:
                        distance_in_km(loc, (station.lat, station.lon)))
                nearest = sorted_stations[0]
                if not any(st.id == nearest.id for st in stations):
                    stations.append(nearest)

            return stations
        else:
            return sorted(
                self.stations,
                key=lambda station, loc=locations:
                    location.distance_in_km(loc, (station.lat, station.lon)))[0]

    def cache_stations(self, ttl: Optional[int] = DEFAULT_STATIONS_TTL):
        assert redis_cache
        json_str = json.dumps(self.stations, cls=SimpleJsonEncoder)
        redis_cache.set(REDIS_STATIONS_KEY, json_str, ex=ttl)
