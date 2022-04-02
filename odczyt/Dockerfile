FROM python:3.7
RUN apt-get update && apt-get -y install cron vim
WORKDIR /app
RUN pip3 install numpy pandas influxdb_client keras tensorflow sklearn
COPY crontab /etc/cron.d/crontab
RUN chmod 0644 /etc/cron.d/crontab
RUN /usr/bin/crontab /etc/cron.d/crontab
COPY porownanie_mocy_godzinowe_f1.py porownanie_mocy_godzinowe_f1.py
COPY porownanie_mocy_godzinowe_f2.py porownanie_mocy_godzinowe_f2.py
COPY przewidywanie_mocy_f1.py przewidywanie_mocy_f1.py
COPY przewidywanie_mocy_f2.py przewidywanie_mocy_f2.py
RUN echo $PYTHONPATH
# run crond as main process of container
CMD ["cron", "-f"]
