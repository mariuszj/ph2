FROM --platform=linux/x86_64 telegraf:1.21.3-alpine
LABEL maintainer "Lukasz Majda <lukasz.majda@gmail.com>"

RUN apk add --update python3 py3-pip lm_sensors && \
    ln -sf python3 /usr/bin/python && \
    rm -rf /var/cache/apk/
RUN python3 -m ensurepip
RUN pip3 install --upgrade pip setuptools requests
COPY requirements.txt .
RUN pip3 install -r requirements.txt
RUN echo "@testing http://dl-cdn.alpinelinux.org/alpine/edge/testing" >> /etc/apk/repositories
RUN apk add --update --no-cache py3-numpy py3-pandas@testing py3-pandas

CMD ["telegraf", "--config", "/etc/telegraf/telegraf.conf", "--config-directory", "/etc/telegraf/telegraf.d"]