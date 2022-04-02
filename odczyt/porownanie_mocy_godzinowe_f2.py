import numpy as np
import pandas as pd
import datetime as dt
from datetime import datetime
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS

bucket = "photovoltaic"
org = "photovoltaic.org"
token = "photovoltaic.token"
url="http://influxdb:8086/"

client = influxdb_client.InfluxDBClient(
    url=url,
    token=token,
    org=org
)

write_api = client.write_api(write_options=SYNCHRONOUS)
query_api = client.query_api()


data_frame = query_api.query_data_frame('''
from(bucket: "photovoltaic")
    |> range(start: 2021-01-01T00:00:00Z, stop: 2022-01-01T00:00:00Z)
    |> filter(fn: (r) => r["_measurement"] == "moce")
    |> filter(fn: (r) => r["id_farmy"] == "2")
    |> filter(fn: (r) => r["_field"] == "moc_DC" or r["_field"] == "moc_AC" or r["_field"] == "wydajnosc")
    |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
''')
data_frame['dzien_czas']= pd.to_datetime(data_frame['_time'],format='%d-%m-%Y %H:%M')
data_frame.drop(['result','table', '_start','_stop', '_measurement','_time'],1,inplace=True)



gen_1=data_frame
gen_1.drop('id_farmy',1,inplace=True)
gen_1['dzien_czas']= pd.to_datetime(gen_1['dzien_czas'],format='%d-%m-%Y %H:%M')

gen_2=gen_1.copy()
gen_2['Godziny_w_ciagu_dnia']=gen_2['dzien_czas'].dt.time
gen_2 = gen_2.reindex(columns = np.append( gen_2.columns.values, ['czas']))
x=0
for x in range(len(gen_2)):
    mytime=gen_2['Godziny_w_ciagu_dnia'].loc[x]
    day = dt.datetime.strptime('2000-01-01','%Y-%m-%d').date()
    mydatetime = dt.datetime.combine(day, mytime)
    gen_2['czas'].loc[x]=mydatetime
    x+=1


gen_1=gen_1.groupby('dzien_czas').sum().reset_index()
gen_1['Godziny_w_ciagu_dnia']=gen_1['dzien_czas'].dt.time

gen_1 = gen_1.reindex(columns = np.append( gen_1.columns.values, ['czas']))

gen_1['id_farmy'] = pd.Series([2 for x in range(len(gen_1.index))])
gen_2['id_farmy'] = pd.Series([2 for x in range(len(gen_2.index))])

x=0
for x in range(len(gen_1)):
    mytime=gen_1['Godziny_w_ciagu_dnia'].loc[x]
    day = dt.datetime.strptime('2000-01-01','%Y-%m-%d').date()
    mydatetime = dt.datetime.combine(day, mytime)
    gen_1['czas'].loc[x]=mydatetime
    x+=1


i=0
for _ in range(len(gen_1)):
    czas = gen_1['czas'].loc[i]
    record = influxdb_client.Point("wykres_dobowy").tag("id_farmy", gen_1['id_farmy'].loc[i]).tag("typ", "moc_AC").tag('zrodlo','suma').field("value", float(gen_1['moc_AC'].loc[i])).time(int(czas.timestamp()), write_precision="s")
    write_api.write(bucket=bucket, org=org, record=record)
    i+=1


i=0
for _ in range(len(gen_1)):
    czas =  gen_1['czas'].loc[i]
    record = influxdb_client.Point("wykres_dobowy").tag("id_farmy", gen_1['id_farmy'].loc[i]).tag("typ", "moc_DC").tag('zrodlo','suma').field("value", float(gen_1['moc_DC'].loc[i])).time(int(czas.timestamp()), write_precision="s")
    write_api.write(bucket=bucket, org=org, record=record)
    i+=1


i=0
for _ in range(len(gen_1)):
    czas =  gen_1['czas'].loc[i]
    record = influxdb_client.Point("wykres_dobowy").tag("id_farmy", gen_1['id_farmy'].loc[i]).tag("typ", "wydajnosc").tag('zrodlo','suma').field("value", float(gen_1['wydajnosc'].loc[i])).time(int(czas.timestamp()), write_precision="s")
    write_api.write(bucket=bucket, org=org, record=record)
    i+=1


i=0
for _ in range(len(gen_2)):
    czas = gen_2['czas'].loc[i]
    dat=gen_2.loc[i]['dzien_czas'].strftime('%m-%d')
    record = influxdb_client.Point("wykres_dobowy").tag("id_farmy", gen_2['id_farmy'].loc[i]).tag("typ", "moc_AC").tag('zrodlo',gen_2['zrodlo'].loc[i]).tag('id_dnia', str(dat)).field("value", float(gen_2['moc_AC'].loc[i])).time(int(czas.timestamp()), write_precision="s")
    write_api.write(bucket=bucket, org=org, record=record)
    i+=1


i=0
for _ in range(len(gen_2)):
    czas = gen_2['czas'].loc[i]
    dat=gen_2.loc[i]['dzien_czas'].strftime('%m-%d')
    record = influxdb_client.Point("wykres_dobowy").tag("id_farmy", gen_2['id_farmy'].loc[i]).tag("typ", "moc_DC").tag('zrodlo',gen_2['zrodlo'].loc[i]).tag('id_dnia', str(dat)).field("value", float(gen_2['moc_DC'].loc[i])).time(int(czas.timestamp()), write_precision="s")
    write_api.write(bucket=bucket, org=org, record=record)
    i+=1


i=0
for _ in range(len(gen_2)):
    czas = gen_2['czas'].loc[i]
    dat=gen_2.loc[i]['dzien_czas'].strftime('%m-%d')
    record = influxdb_client.Point("wykres_dobowy").tag("id_farmy", gen_2['id_farmy'].loc[i]).tag("typ", "wydajnosc").tag('zrodlo',gen_2['zrodlo'].loc[i]).tag('id_dnia', str(dat)).field("value", float(gen_2['wydajnosc'].loc[i])).time(int(czas.timestamp()), write_precision="s")
    write_api.write(bucket=bucket, org=org, record=record)
    i+=1
 