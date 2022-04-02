from hashlib import md5
from typing import Dict, Optional, Union, Tuple

from pyowm.owm import OWM
from pyowm.weatherapi25.weather import Weather

import redis_utils as redis_utils

DEFAULT_EXCLUDE = 'minutely,daily,alerts'
DEFAULT_UNITS = 'metric'
DEFAULT_FORECAST_HOURS = 48
DEFAULT_FORECAST_TTL = 900  # 15 minutes

REDIS_FORECAST_KEY = 'owm_forecast_{}'

redis_cache = None
owm_mgr = None


def init(token: str, redis_url: Optional[str] = redis_utils.DEFAULT_REDIS_URL):
    # initialize redis database
    global redis_cache
    redis_cache = redis_utils.redis_init_from_url(redis_url)

    # initialize openweathermap
    global owm_mgr
    owm = OWM(token)
    owm_mgr = owm.weather_manager()


def hash_location(location: Tuple[Union[int, float], Union[int, float]]):
    return md5(f"{location[0]} {location[1]}".encode()).hexdigest()


class ForecastHour:
    @staticmethod
    def from_json(json_dict: Dict):
        forecast = ForecastHour()
        forecast.time = json_dict['ref_time']
        forecast.clouds = json_dict['clouds']
        press_dict = json_dict['pressure']
        forecast.pressure = press_dict['press'] if 'press' in press_dict else None
        forecast.humidity = json_dict['humidity']
        temp_dict = json_dict['temp']
        forecast.temperature = temp_dict['temp']
        forecast.feels_like = temp_dict['feels_like']
        wind_dict = json_dict['wnd']
        forecast.wind_speed = wind_dict['speed'] if 'speed' in wind_dict else None
        forecast.wind_deg = wind_dict['deg'] if 'deg' in wind_dict else None
        forecast.wind_gust = wind_dict['gust'] if 'gust' in wind_dict else None
        rain_dict = json_dict['rain']
        forecast.rain_1h = rain_dict['1h'] if '1h' in rain_dict else 0
        snow_dict = json_dict['snow']
        forecast.snow_1h = snow_dict['1h'] if '1h' in snow_dict else 0
        forecast.uvi = json_dict['uvi']
        forecast.visibility = json_dict['visibility_distance']
        forecast.dew_point = json_dict['dewpoint']
        forecast.pop = json_dict['precipitation_probability']
        forecast.status = json_dict['status']
        forecast.detailed_status = json_dict['detailed_status']

        return forecast


class Forecast:
    def __init__(self, location: Tuple[Union[int, float], Union[int, float]]):
        self.location = location
        self.hourly = []

    @staticmethod
    def get(location: Tuple[Union[int, float], Union[int, float]],
            exclude: Optional[str] = DEFAULT_EXCLUDE,
            units: Optional[str] = DEFAULT_UNITS,
            hours: Optional[int] = DEFAULT_FORECAST_HOURS,
            ttl: Optional[int] = DEFAULT_FORECAST_TTL):
        assert redis_cache
        key = REDIS_FORECAST_KEY.format(hash_location(location))
        if redis_cache.exists(key):
            return 0, None
        else:
            forecast = Forecast.from_server(
                location, exclude, units, hours, ttl)
            return 1, forecast

    @staticmethod
    def from_server(
            location: Tuple[Union[int, float], Union[int, float]],
            exclude: Optional[str] = DEFAULT_EXCLUDE,
            units: Optional[str] = DEFAULT_UNITS,
            hours: Optional[int] = DEFAULT_FORECAST_HOURS,
            ttl: Optional[int] = DEFAULT_FORECAST_TTL):
        try:
            one_call = owm_mgr.one_call(
                lat=location[0],
                lon=location[1],
                exclude=exclude,
                units=units)
            forecast = Forecast.from_weather(
                location=location,
                weather=one_call.forecast_hourly,
                hours=hours)

            forecast.cache_forecast(ttl)
            return forecast
        except:
            return None

    @staticmethod
    def from_weather(
            location: Tuple[Union[int, float], Union[int, float]],
            weather: Weather,
            hours: Optional[int] = DEFAULT_FORECAST_HOURS):
        assert weather

        forecast = Forecast(location)
        forecast.hourly = []

        for hour in weather:
            forecast_hour = ForecastHour.from_json(hour.__dict__)
            forecast.hourly.append(forecast_hour)
            if len(forecast.hourly) >= hours:
                break

        return forecast

    def cache_forecast(self, ttl: Optional[int] = DEFAULT_FORECAST_TTL):
        assert redis_cache
        key = REDIS_FORECAST_KEY.format(hash_location(self.location))
        redis_cache.set(key, 1, ex=ttl)
