FROM python

WORKDIR /usr/src/app
RUN git clone https://github.com/mikuslaw/SmartthingsMqttService.git .

RUN pip install --no-cache-dir -r docker/requirements.txt

EXPOSE 8090

COPY . .
CMD [ "python", "./BridgeService/mqtt_smartthings_bridge.py" ]