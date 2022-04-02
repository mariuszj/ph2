import argparse
import time

import owm_api as owm
import redis_utils as redis_utils
import telegraf_utils as telegraf
from config import LOCATIONS

DEFAULT_MAX_REQUESTS = 50

# parse arguments
parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument("-t", "--token", type=str, required=True,
                    help="OpenWeatherMap api access token")
parser.add_argument("-m", "--max-requests", type=int,
                    help="maximum number of requests to the OpenWeatherMap API",
                    default=DEFAULT_MAX_REQUESTS)
parser.add_argument("-f", "--forecast", type=int,
                    help="maximum number of hours in the hourly weather forecast",
                    default=owm.DEFAULT_FORECAST_HOURS)
parser.add_argument("-l", "--ttl", type=int,
                    help="forecast cache ttl",
                    default=owm.DEFAULT_FORECAST_TTL)
parser.add_argument("-r", "--redis", type=str,
                    help="redis database connection string",
                    default=redis_utils.DEFAULT_REDIS_URL)
args = parser.parse_args()

# init owm api
owm.init(token=args.token, redis_url=args.redis)

num_requests = 0
forecasts = []
timestamp = time.time_ns()

# request for forecast in each location
for location in LOCATIONS:
    result, forecast = owm.Forecast.get(
        location=location,
        hours=args.forecast,
        ttl=args.ttl)
    if forecast is not None:
        forecasts.append(forecast)

    num_requests += result
    if num_requests >= args.max_requests:
        break

# output forecast in influx format
for forecast in forecasts:
    for index, f in enumerate(forecast.hourly, start=0):
        telegraf.print_influxdb_format(
            measurement='owm',
            fields={
                'clouds': f.clouds,
                'press': f.pressure,
                'hum': f.humidity,
                'temp': f.temperature,
                'feels_like': f.feels_like,
                'wnd_speed': f.wind_speed,
                'wnd_deg': f.wind_deg,
                'wnd_gust': f.wind_gust,
                'rain_1h': f.rain_1h,
                'snow_1h': f.snow_1h,
                'uvi': f.uvi,
                'visibility': f.visibility,
                'dew_point': f.dew_point,
                'pop': f.pop,
                'status': f.status,
                'detailed_status': f.detailed_status
            },
            tags={
                'forecast': f"{index}h",
                'location': f"{forecast.location[0]} {forecast.location[1]}"
            },
            timestamp=timestamp)
