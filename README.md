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

