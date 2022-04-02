import pandas as pd
import json
from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS

bucket = "photovoltaic"
org = "photovoltaic.org"
token = "photovoltaic.token"
url="http://localhost:8086/"


client = InfluxDBClient(
    url=url,
    token=token,
    org=org
)

write_api = client.write_api(write_options=SYNCHRONOUS)
pow_1=pd.read_csv('dane_mocy_miesieczne_1/052021_moc_1.csv')
pow_1.drop(columns=['wydajnosc_sum'], inplace=True)


pow_1['dzien_czas']= pd.to_datetime(pow_1['dzien_czas'],format='%d-%m-%Y %H:%M')

pow_1=pow_1.set_index(pd.DatetimeIndex(pow_1['dzien_czas']))
pow_1.drop('dzien_czas',1, inplace=True)


write_api.write(bucket=bucket, org=org, record=pow_1, data_frame_measurement_name='moce', data_frame_tag_columns=['zrodlo', 'id_farmy'])
client.close()

write_api.__del__()
client.__del__()
