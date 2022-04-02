### Build telegraf image

```
docker build --no-cache --force-rm .
```

### Run

```
docker-compose up --build -d
```


### Access from host

Open the .env file to get all credentials.

| Address                  | Username | Password | Service                      |
|--------------------------|----------|----------|------------------------------|
| `redis://localhost:6380` |          | admin123 | Redis database               |
| `http://localhost:8086`  | admin    | admin123 | InfluxDB Web Admin Interface |
| `http://localhost:3000`  | admin    | admin123 | Grafana Web Interface        |

### Date feed

Run files:

/next/zapis_do_bazy_moc_1
/next/zapis_do_bazy_moc_2
/next/zapis_do_bazy_pogoda_1
/netx/zapis_do_bazy_pogoda_2

### Dashboards

In Grafana import files:
/wykresy/Analiza godzinowa farma 1-1648790784139
/wykresy/Analiza godzinowa farma 2-1648791346433
/wykresy/Dashboard podstawowy farma 1-1648791353875
/wykresy/Dashboard podstawowy farma 2-1648791359823