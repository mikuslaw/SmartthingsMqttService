/**
 *  mqtt bridge
 *
 *  Copyright 2020 Jerzy Mikucki
 *
 *  Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
 *  in compliance with the License. You may obtain a copy of the License at:
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 *  Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 *  on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License
 *  for the specific language governing permissions and limitations under the License.
 */
metadata {
	definition (name: "mqtt bridge", namespace: "mikuslaw", author: "Jerzy Mikucki", cstHandler: true) {
		capability "Notification"
        capability "Refresh"
        
        command "unsubscribeAllTopics"
        command "subscribeToTopic", ["string"]
        command "publish", ["string", "string", "boolean"]
        command "poll"
	}


	simulator {
		// TODO: define status and reply messages here
	}

	tiles {
		// TODO: define your main and details tiles here
	}
    
    preferences {
    	input "ip", "text", title: "IP address of bridge", description: "IP Address in form 192.168.1.226", required: true, displayDuringSetup: true
		input "port", "text", title: "Port of bridge", description: "port in form of 8090", required: true, displayDuringSetup: true
		input "mac", "text", title: "MAC Address of bridge", description: "MAC Address in form of 02A1B2C3D4E5", required: true, displayDuringSetup: true		
    }
}

def refresh() {
	log.debug "Executing refresh"
    updateDeviceNetworkID()
    poll()
}

def updated() {
	log.debug "${device.name} updated"
    updateDeviceNetworkID()
}

def updateDeviceNetworkID() {
	log.debug "Executing 'updateDeviceNetworkID'"
    def formattedMac = mac.toUpperCase()
    formattedMac = formattedMac.replaceAll(":", "")
    if(device.deviceNetworkId!=formattedMac) {
        log.debug "setting deviceNetworkID = ${formattedMac}"
        device.setDeviceNetworkId("${formattedMac}")
	}
}

def unsubscribeAllTopics() {
	// send to bridge
    log.debug "Unsubscribe all topics"
    state.subscriptions = []
    
    sendMsgToBridge([command: "unsubscribe", topic: "#"])
}

def subscribeToTopic(devId, topic) {
	// send to bridge
    log.debug "Subscribing id: ${devId}, topic: ${topic}"
    sendMsgToBridge([command: "subscribe", topic: topic])  
}

def publish(topic, message, retained) {
	def retained_str =retained?"(R)":""
	log.debug "Publishing to ${retained_str}${topic}: ${message}"
    sendMsgToBridge([command: "publish", message: [topic: topic, retained: retained, message: message]])
}

def poll() {
	log.debug "Polling for new messages"
    sendMsgToBridge([command: "poll"])
}

// parse events into attributes
def parse(String description) {
	def parse_result = null
	def msg = parseLanMessage(description)
    if(msg.json == null) {
    	// Drop silently
    	// log.debug "Couldn't parse json message"
    	return
    }
    log.debug "Parsing msg json: ${msg.json}"
	
    if(msg.json.containsKey("command")) {
    	parse_result = parseCommand(msg)
    }
    
    if(parse_result == null) {
    	log.debug "Failed to parse message"
    }
    return parse_result
}

def parseCommand(msg) {
	def command = msg.json["command"]
    
    switch(command) {
    	case "publish":
        	if(msg.json.containsKey("message")) {
        		return parseCommandPublish(msg.json["message"])
            }
        	break
    	default:
        	break
    }
    
    return
}

def parseCommandPublish(message) {
	if(!message.containsKey("topic") ||
       !message.containsKey("retained") ||
       !message.containsKey("retained"))
       return
       
	return createEvent(name: "mqttpublish", value: null, data: message, isStateChange: true)
}


def sendMsgToBridge(msg_json){  
    def result = new physicalgraph.device.HubAction([
    		method: "POST",
        	body: msg_json,
        	headers: [
            	"HOST": "${ip}:${port}",
        	]]
		)
   return result
}
