#!/bin/python
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
import paho.mqtt.client as mqtt
import json
import requests
import queue
import threading
import signal
from functools import partial
import traceback

class MqttSmartthings():
    class MqttHandler():
        def __init__(self, queue, cond):
            self.queue = queue
            self.cond = cond

        def on_connect(self, client, userdata, flags, rc):
            print("On connect")
            client.subscribe("test1/test2/test3")
            print("On connect done")

        def on_disconnect(self, client, userdata, rc):
            print("On disconnect: {}".format(rc))
        
        def on_subscribe(self, client, userdata, mid, granted_qos):
            print("On subscribe {}".format(mid))

        def on_unsubscribe(self, client, userdata, mid):
            print("On unsubscribe {}".format(mid))

        def on_publish(self, client, userdata, mid):
            print("On publish {}".format(mid))

        def on_message(self, client, userdata, msg):
            try:
                print("On message({}{}) on {}: {}".format("R" if msg.retain==1 else "", msg.qos, msg.topic, msg.payload))
                command = {"command": "publish", "message": {"topic": msg.topic, "message": msg.payload, "qos": msg.qos, "retained": True if msg.retain else False}}
                self.queue.put(command)
                self.cond.acquire()
                self.cond.notify_all()
                self.cond.release()
            except Exception as e:
                print("Exception in mqtt thread: {}".format(e))
            except:
                print('An error occurred.')

    class MqttOverHTTPHandler(BaseHTTPRequestHandler):
        def __init__(self, queue, cond, *args, **kwargs):
            self.queue = queue
            self.cond = cond
            super().__init__(*args, **kwargs)

        def do_POST(self):
            length = int(self.headers.get('content-length', 0))
            body = self.rfile.read(length)
            self.send_response(200)
            self.end_headers()
            print("Body: {}".format(body))
            json_body_dict = json.loads(body)
            
            self.queue.put(json_body_dict)
            self.cond.acquire()
            self.cond.notify_all()
            self.cond.release()
            print("Received POST({}): {}".format(length, body))

    def __init__(self, mqtt_host="127.0.0.1", mqtt_port=1883, http_host="127.0.0.1", http_port=39500, http_local_port=8090):
        self.q_rcv_post_cmd = queue.Queue()
        self.q_rcv_mqtt_cmd = queue.Queue()
        self.q_rcv_cond = threading.Condition()

        self.mqtt_host = mqtt_host
        self.mqtt_port = mqtt_port
        self.http_host = http_host
        self.http_port = http_port

        self.http_local_host = "0.0.0.0"
        self.http_local_port = http_local_port

        self.mqtt_handler = self.MqttHandler(self.q_rcv_mqtt_cmd, self.q_rcv_cond)

        self.mqtt_thread = None
        self.http_thread = None
        self.process_thread = None
        self.process_thread_run = True

        self.mqtt_subscriptions = []

    def startHTTP(self):
        print("Start HTTP deamon")
        self.http_server = HTTPServer((self.http_local_host, self.http_local_port), partial(self.MqttOverHTTPHandler, self.q_rcv_post_cmd, self.q_rcv_cond))
        self.http_thread = threading.Thread(target=self.http_server.serve_forever)
        self.http_thread.start()
        

    def startMQTT(self):
        print("Start MQTT deamon")
        self.mqtt_client = mqtt.Client()
        self.mqtt_client.on_connect = self.mqtt_handler.on_connect
        self.mqtt_client.on_message = self.mqtt_handler.on_message
        self.mqtt_client.on_disconnect = self.mqtt_handler.on_disconnect
        self.mqtt_client.on_publish = self.mqtt_handler.on_publish
        self.mqtt_client.on_subscribe = self.mqtt_handler.on_subscribe
        self.mqtt_client.on_unsubscribe = self.mqtt_handler.on_unsubscribe

        self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
        self.mqtt_thread = threading.Thread(target=self.mqtt_client.loop_forever)
        self.mqtt_thread.start()

    def startProcessQ(self):
        print("Start Processing deamon")
        self.process_thread = threading.Thread(target=self.processQ)
        self.process_thread.start()

    def start(self):
        print("Starting")
        self.startMQTT()
        self.startHTTP()
        self.startProcessQ()
        print("Started")

    def stop(self):
        self.http_server.shutdown()
        self.mqtt_client.disconnect()
        self.mqtt_thread.join()
        self.http_thread.join()
        self.q_rcv_cond.acquire()
        self.process_thread_run = False
        self.q_rcv_cond.notify_all()
        self.q_rcv_cond.release()
        self.process_thread.join()

    def processQ(self):
        while self.process_thread_run:
            self.q_rcv_cond.acquire()
            if self.q_rcv_mqtt_cmd.empty() and self.q_rcv_post_cmd.empty() and self.process_thread_run:
                self.q_rcv_cond.wait()
            self.q_rcv_cond.release()

            print("Process thread loop.")
            try:
                if not self.q_rcv_mqtt_cmd.empty():
                    mqtt_cmd = self.q_rcv_mqtt_cmd.get()
                    if "command" in mqtt_cmd:
                        if mqtt_cmd["command"] == "publish":
                            # Service publish to HTTP Post
                            http_req = requests.post("http://{}:{}".format(self.http_host, self.http_port), json=mqtt_cmd, stream=False)
                            print("HTTP request status: {} {}".format(http_req.status_code, http_req.reason))
                        else:
                            print("Unknown command received on MQTT queue")
                if not self.q_rcv_post_cmd.empty():
                    post_cmd = self.q_rcv_post_cmd.get()
                    if "command" in post_cmd:
                        if post_cmd["command"] == "publish":
                            # Service publish
                            print("HTTP Command: publish")

                        elif post_cmd["command"] == "subscribe":
                            # Service subscribe
                            print("HTTP Command: subscribe")
                            self.mqtt_subscriptions += post_cmd["topic"]

                            qos = 0
                            if "qos" in post_cmd:
                                qos = post_cmd["qos"]
                            
                            self.mqtt_client.subscribe(post_cmd["topic"], qos)

                        elif post_cmd["command"] == "unsubscribe":
                            # Service unsubscribe
                            print("HTTP Command: unsubscribe")
                            self.mqtt_client.unsubscribe(post_cmd["topic"])

                        else:
                            print("Unknown command received on HTTP queue: {}".format(post_cmd["command"]))
            except Exception as e:
                print("Exception in process thread: {}".format(e))
                traceback.print_exc()


# class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
#     def do_GET(self):
#         self.send_response(200)
#         self.end_headers()
#         self.wfile.write(b'Hello, world!')

#     def do_POST(self):
#         content_length = int(self.headers['Content-Length'])
#         body = self.rfile.read(content_length)
#         self.send_response(200)
#         self.send_header('Content-Type', "application/json")
#         self.end_headers()
#         response = BytesIO()
#         if body == r'{"command":"poll"}':
#             response.write(r'{"command": "publish", "message": {"topic": "test1/test2/test3", "message": "21", "retained": true}}\n\r')

#         print("Body: {}".format(body))
#         self.wfile.write(response.getvalue())

# # The callback for when the client receives a CONNACK response from the server.
# def on_connect(client, userdata, flags, rc):
#     print("Connected with result code "+str(rc))

#     # Subscribing in on_connect() means that if we lose the connection and
#     # reconnect then subscriptions will be renewed.
#     # client.subscribe("$SYS/#")
#     # client.subscribe("test1/test2/test3")

# # The callback for when a PUBLISH message is received from the server.
# def on_message(client, userdata, msg):
#     #
#     try:
#         r = requests.post("http://192.168.55.53:39500/query", json={'command': 'publish', 'message': {'topic': msg.topic, 'message': msg.payload, 'retained': True if msg.retain==1 else False}}, stream=False)
#     except Exception as e:
#         print("Ex: {}".format(e.msg))
#     print(r.status_code, r.reason)
#     print(msg.topic+" "+str(msg.payload))


# httpd = HTTPServer(("0.0.0.0", 8090), SimpleHTTPRequestHandler)
# client = mqtt.Client()
# client.on_connect = on_connect
# client.on_message = on_message
# client.user_data_set(httpd)

# client.connect("192.168.55.107", 1883, 60)

# s = requests.session()
# s.keep_alive = False

# client.loop_start()
# httpd.serve_forever()

cv = threading.Condition()

def end_handler(signum, frame):
    print("\nCtrl+C pressed")
    cv.acquire()
    cv.notify_all()
    cv.release()


if __name__== "__main__":
    signal.signal(signal.SIGINT, end_handler)

    connector = MqttSmartthings(mqtt_host="192.168.55.107", mqtt_port=1883, http_host="192.168.55.53", http_port=39500)
    connector.start()

    print("Press Ctrl+C to stop")
    cv.acquire()
    cv.wait()
    cv.release()

    print("Closing")
    connector.stop()
