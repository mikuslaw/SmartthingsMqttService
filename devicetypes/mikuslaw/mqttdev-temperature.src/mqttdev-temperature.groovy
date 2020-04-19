/**
 *  mqttdev temperature
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
import groovy.json.JsonSlurper

metadata {
	definition (name: "mqttdev temperature", namespace: "mikuslaw", author: "Jerzy Mikucki", cstHandler: true) {
		capability "Temperature Measurement"
        capability "Notification"
        capability "Refresh"
        
        command "processMqttMessage", ["string"]
        command "notifySubscriptions"
        
	}


	simulator {
		// TODO: define status and reply messages here
	}

	tiles {
		// TODO: define your main and details tiles here
        valueTile("temperature", "device.temperature") {
        	state("temperature", label:'${currentValue}°',
            	backgroundColors:[
                	[value: 31, color: "#153591"],
                    [value: 44, color: "#1e9cbb"],
                    [value: 59, color: "#90d2a7"],
                    [value: 74, color: "#44b621"],
                    [value: 84, color: "#f1d801"],
                    [value: 95, color: "#d04e00"],
                    [value: 96, color: "#bc2323"]
				]
           )
		}

        main (["temperature"])
	}
    
    preferences {
    	input "temperature_topic", "text", title: "Mqtt Topic with Temperature", description: "Mqtt topic with Temperature", required: true, displayDuringSetup: true
    }
}

def refresh() {
	log.debug "Executing refresh"
    sendEvent(name: "mqttpoll", value: device.id, isStateChange: true)
}

// parse events into attributes
def parse(String description) {
	log.debug "Parsing '${description}'"
}

def updated() {
	log.debug "${device.name} updated"
    sendEvent(name: "mqttrefreshsubscriptions", value: device.id, isStateChange: true)
}

def updateValue(numberParam) {
	log.debug "Update temperature to ${numberParam}"
	sendEvent(name: "temperature", value: numberParam)
}

def processMqttMessage(message) {
    log.debug "Json data parsed: ${message}"
	def retained = message.retained?"R":""
	def value = null
	log.debug "Received Mqtt on ${message.topic}: ${message.message}"
    try {
    	value = message.message.toInteger()
    } catch(Exception ex) {
    	log.debug "Couldn't parse value"
    } finally {
    	updateValue(value)
    }
}

def notifySubscriptions() {
    log.debug "${device.name} request for subscription list"
    def submap = [id: device.id, topics: [temperature_topic]]
	sendEvent(name: "mqttnotifysubscriptions", value: null, data: submap, isStateChange: true)
}
