FROM python

WORKDIR /usr/src/app
ADD docker/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ADD BridgeService/mqtt_smartthings_bridge.py .

EXPOSE 8090
CMD [ "python", "mqtt_smartthings_bridge.py" ]