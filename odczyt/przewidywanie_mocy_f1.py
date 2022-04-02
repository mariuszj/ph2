import numpy as np
import pandas as pd
from datetime import datetime
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
from keras.layers import Dropout
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from sklearn.preprocessing import MinMaxScaler



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
    |> filter(fn: (r) => r["id_farmy"] == "1")
    |> filter(fn: (r) => r["_field"] == "moc_DC" or r["_field"] == "moc_AC" or r["_field"] == "wydajnosc")
    |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
''')
data_frame['dzien_czas']= pd.to_datetime(data_frame['_time'],format='%d-%m-%Y %H:%M')
data_frame.drop(['result','table', '_start','_stop', '_measurement','_time'],1,inplace=True)

generacja=data_frame
generacja['dzien_czas']= pd.to_datetime(generacja['dzien_czas'],format='%d-%m-%Y %H:%M')
generacja.drop('id_farmy',1,inplace=True)
generacja['dzien']=generacja['dzien_czas']
moc=generacja.copy()
moc_sred=moc.groupby('dzien')['moc_AC','moc_DC'].agg('mean')
moc_AC=generacja['moc_AC']


data_frame2 = query_api.query_data_frame('''
from(bucket: "photovoltaic")
    |> range(start: 2021-01-01T00:00:00Z, stop: 2022-01-01T00:00:00Z)
    |> filter(fn: (r) => r["_measurement"] == "pogoda")
    |> filter(fn: (r) => r["id_farmy"] == "1")
    |> filter(fn: (r) => r["_field"] == "naslonecznienie")
    |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
''')
data_frame2['dzien_czas']= pd.to_datetime(data_frame2['_time'],format='%d-%m-%Y %H:%M')
data_frame2.drop(['result','table', '_start','_stop', '_measurement','_time'],1,inplace=True)


pogoda=data_frame2
pogoda['dzien_czas']= pd.to_datetime(pogoda['dzien_czas'],format='%Y-%m-%d %H:%M:%S')
pogoda.drop(['id_farmy','zrodlo'], axis=1, inplace=True)
pogoda=pogoda.set_index('dzien_czas')

dane_polaczone=pd.concat([pogoda, moc_sred], axis=1)
a=dane_polaczone[dane_polaczone.isna().any(axis=1)]
dane_polaczone=dane_polaczone.dropna()

dane_polaczone_AC=dane_polaczone.drop('moc_DC',1)
dane_polaczone_DC=dane_polaczone.drop('moc_AC',1)
sc = MinMaxScaler(feature_range = (0, 1))


set_scaled = sc.fit_transform(dane_polaczone_AC.iloc[:,:-1])
resh=dane_polaczone_AC.iloc[:,-1].values
resh=resh.reshape(-1,1)
set_scaled2 = sc.fit_transform(resh)

X_train = []
y_train = []
parametr=5
for i in range(parametr, set_scaled.shape[0]-500):
    X_train.append(set_scaled[i-parametr:i, 0])
    y_train.append(set_scaled2[i, -1])
X_train, y_train = np.array(X_train), np.array(y_train)
X=np.reshape(X_train,(X_train.shape[0], X_train.shape[1],1))
X_train=X
X_test = []
y_test = []
for i in range(set_scaled.shape[0]-500,set_scaled.shape[0]):
    X_test.append(set_scaled[i-parametr:i, 0])
    y_test.append(set_scaled2[i, -1])
X_test, y_test = np.array(X_test), np.array(y_test)
X_test=np.reshape(X_test,(X_test.shape[0], X_test.shape[1],1))



regressor = Sequential()
regressor.add(LSTM(units = 50, return_sequences = True, input_shape = (X_train.shape[1], X_train.shape[2])))
regressor.add(Dropout(0.2))
regressor.add(Dropout(0.2))
regressor.add(LSTM(units = 50, return_sequences = True))
regressor.add(Dropout(0.2))
regressor.add(LSTM(units = 50))
regressor.add(Dropout(0.2))
regressor.add(Dense(units = 1))
regressor.compile(optimizer = 'adam', loss = 'mean_squared_error')
regressor.fit(X_train, y_train, epochs = 5, batch_size = 16)


real_val = resh[set_scaled2.shape[0]-500:,-1]

pred = regressor.predict(X_test)
pred = sc.inverse_transform(pred)


pred_influx=pd.DataFrame(pred)
pred_influx['id_farmy'] = pd.Series([1 for x in range(len(pred_influx.index))])
pred_influx['zrodlo'] = pd.Series(['sred' for x in range(len(pred_influx.index))])
pred_influx.rename(columns={0:'predykcja','id_farmy':'id_farmy','zrodlo':'zrodlo'}, inplace=True)
pred_influx["predykcja"] = pred_influx["predykcja"].astype(float)
pred_influx['dzien_czas']=moc_sred.index[-500:]
pred_influx['dzien_czas']=pred_influx['dzien_czas'].dt.strftime('%Y-%m-%d %H:%M:%S')
pred_influx=pred_influx.set_index(pd.DatetimeIndex(pred_influx['dzien_czas']))
pred_influx.drop('dzien_czas',1, inplace=True)
write_api.write(bucket=bucket, org=org, record=pred_influx, data_frame_measurement_name='moce', data_frame_tag_columns=['id_farmy','zrodlo'])


real_val_influx=pd.DataFrame(real_val)
real_val_influx['id_farmy'] = pd.Series([1 for x in range(len(real_val_influx.index))])
real_val_influx['zrodlo'] = pd.Series(['sred' for x in range(len(real_val_influx.index))])
real_val_influx.rename(columns={0:'produkcja','id_farmy':'id_farmy','zrodlo':'zrodlo'}, inplace=True)
real_val_influx["produkcja"] = real_val_influx["produkcja"].astype(float)
real_val_influx['dzien_czas']=moc_sred.index[-500:]
real_val_influx['dzien_czas']=real_val_influx['dzien_czas'].dt.strftime('%Y-%m-%d %H:%M:%S')
real_val_influx=real_val_influx.set_index(pd.DatetimeIndex(real_val_influx['dzien_czas']))
real_val_influx.drop('dzien_czas',1, inplace=True)
write_api.write(bucket=bucket, org=org, record=real_val_influx, data_frame_measurement_name='moce', data_frame_tag_columns=['id_farmy','zrodlo'])


client.close()

write_api.__del__()
client.__del__()
