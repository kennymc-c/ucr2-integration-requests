#!/usr/bin/env python3

"""Module that includes functions to add a http request response sensor entity"""

import logging

import ucapi
from re import search

import config
import driver

_LOG = logging.getLogger(__name__)

#TODO Add possibility to add additional sensor entities in advanced setup. Each sensor then can be linked to a specific http request command by using a special command parameter



async def add_rq_sensor(ent_id: str, name: str):
    """Function to add a http request response sensor entity"""

    definition = ucapi.Sensor(
        ent_id,
        name,
        features=None, #Mandatory although sensor entities have no features
        attributes={ucapi.sensor.Attributes.STATE: ucapi.sensor.States.ON, ucapi.sensor.Attributes.VALUE: ""},
        device_class=ucapi.sensor.DeviceClasses.CUSTOM,
        options=None
    )

    driver.api.available_entities.add(definition)

    _LOG.info("Added http request response sensor entity with id " + ent_id + " and name " + str(name))



def update_rq_sensor(entity_id: str, response: str):
    """Parse http request response with configured regular expression and update sensor entity value"""

    regex = config.Setup.get("rq_response_regex")

    if regex == "":
        parsed_response = response
        _LOG.debug("No regular expression set for the http request response sensor. The complete response will be sent to the http request response sensor")
    else:
        match = search(regex, response)
        if match:
            parsed_response = match.group(1)
            _LOG.debug("Parsed response: " + parsed_response)
        else:
            parsed_response = response
            _LOG.warning("No matches found in the http request response for the regular expression " + regex + ". \
The complete response will be sent to the http request response sensor")

    value = parsed_response

    attributes_to_send = {ucapi.sensor.Attributes.STATE: ucapi.sensor.States.ON, ucapi.sensor.Attributes.VALUE: value}

    try:
        api_update_attributes = driver.api.configured_entities.update_attributes(entity_id, attributes_to_send)
    except Exception as e:
        _LOG.error(e)
        raise Exception("Error while updating sensor value for entity id " + entity_id) from e

    if not api_update_attributes:
        raise Exception("Sensor entity " + entity_id + " not found. Please make sure it's added as a configured entity on the remote")

    _LOG.info("Updated http request response sensor value to " + value)
