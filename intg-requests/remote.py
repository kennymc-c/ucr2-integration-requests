#!/usr/bin/env python3

"""Module that includes functions to add custom remote entities with all available commands"""

import asyncio
import logging
from typing import Any
import time

import ucapi

import driver
import config
import commands

_LOG = logging.getLogger(__name__)



async def update_remote_state(entity_id: str, cmd_id: str):
    """Set the state of the remote entity to on or off"""

    attribute = {}

    if cmd_id == ucapi.remote.Commands.ON:
        attribute = {ucapi.remote.Attributes.STATE: ucapi.remote.States.ON}
    if cmd_id == ucapi.remote.Commands.OFF:
        attribute = {ucapi.remote.Attributes.STATE: ucapi.remote.States.OFF}
    if cmd_id == ucapi.remote.Commands.TOGGLE:
        try:
            stored_data = await driver.api.available_entities.get_states()
        except Exception as e:
            _LOG.error("Can't get stored states from the remote. Set state to Unknown")
            _LOG.info(str(e))
            attribute = {ucapi.remote.Attributes.STATE: ucapi.remote.States.UNKNOWN}

        current_state = next((state["attributes"]["state"] for state in stored_data if state["entity_id"] == entity_id),None)

        if current_state == ucapi.remote.States.OFF:
            attribute = {ucapi.remote.Attributes.STATE: ucapi.remote.States.ON}
        else:
            attribute = {ucapi.remote.Attributes.STATE: ucapi.remote.States.OFF}

    try:
        api_update_attributes = driver.api.configured_entities.update_attributes(entity_id, attribute)
    except Exception as e:
        raise Exception("Error while updating status attribute for entity id " + entity_id) from e

    if not api_update_attributes:
        raise Exception("Entity " + entity_id + " not found. Please make sure it's added as a configured entity on the remote")
    _LOG.info("Updated remote entity status attribute to " + str(attribute) + " for " + entity_id)



async def send_command(command: str, entity_id: str, entity_config: dict[str, Any]):
    """Send a command depend on the command type from the custom entities configuration"""

    features = entity_config.get("Features").keys()
    simple_commands =  entity_config.get("Simple Commands").keys()

    # Entity feature names that are used in the configuration have a capital first letter while entity command names are all lower case
    features = [f.lower() for f in features]

    if command.lower() in features: #command.lower() if the name is send with the wring spelling by a send command/command sequence command
        # Use command.title() to match the corresponding entity feature spelling (first letter in upper case) for the command that is used in the entity config
        cmd_type = entity_config.get("Features").get(command.title()).get("Type")
        cmd_param = entity_config.get("Features").get(command.title()).get("Parameter")
    elif command in simple_commands:
        cmd_type = entity_config.get("Simple Commands").get(command).get("Type")
        cmd_param = entity_config.get("Simple Commands").get(command).get("Parameter")
    else:
        _LOG.error(f"Feature or simple command {command} not configured in custom entity {entity_id}")
        return ucapi.StatusCodes.NOT_IMPLEMENTED

    match cmd_type:
        case "wol":
            cmd_status = await commands.wol(cmd_param)

        case "tcp-text":
            cmd_status = await commands.tcp_text(cmd_param)

        case "get" | "post" | "put" | "delete" | "patch" | "head":
            http_method = cmd_type
            _LOG.info(f"Executing HTTP request with method {http_method} and parameter {cmd_param}")
            # Use asyncio.gather() to run the function in a separate thread and use asyncio.sleep(0) to prevent blocking the event loop
            # This is needed because the Python requests library is blocking and we want to run it in a non-blocking way
            cmd_status = await asyncio.gather(asyncio.to_thread(commands.http_request, http_method, cmd_param), asyncio.sleep(0))
            #Return the return value of rq_cmd which is the first command in asyncio.gather()
            return cmd_status[0]

        case _:
            _LOG.error(f"Unknown command type {cmd_type} for custom entity {entity_id}")
            return ucapi.StatusCodes.BAD_REQUEST

    return cmd_status



async def send_command_sequence(_params: dict[str, Any], entity_id: str, entity_config: dict[str, Any]):
    """Handle send command sequence parameters and send each command with send_command()"""

    sequence = _params.get("sequence")
    repeat = _params.get("repeat")
    delay = _params.get("delay")
    hold = _params.get("hold")

    def rep_warn(command):
        if repeat != 1:
            _LOG.warning("Execution of the command " + command + " failed. Remaining " + str(repeat-1) + " repetitions will no longer be executed")

    if hold is None or hold == "":
        hold = 0
    if repeat is None:
        repeat = 1
    if delay is None:
        delay = 0
    else:
        delay = delay / 1000 #Convert milliseconds to seconds for sleep

    if repeat == 1 and delay != 0:
        _LOG.debug(str(delay) + " seconds delay will be ignored as the command will not be repeated (repeat = 1)")
        delay = 0

    _LOG.info(f"Command sequence: {sequence}")

    for command in sequence:
        _LOG.debug("Sending command: " + command)
        try:
            i = 0
            r = range(repeat)
            for i in r:
                i = i+1
                if repeat != 1:
                    _LOG.debug("Round " + str(i) + " for command " + command)
                if hold != 0:
                    cmd_start = time.time()*1000
                    while time.time()*1000 - cmd_start < hold:
                        await send_command(command, entity_id, entity_config)
                        await asyncio.sleep(0)
                else:
                    await send_command(command, entity_id, entity_config)
                    await asyncio.sleep(0)
                await asyncio.sleep(delay)
        except Exception as e:
            rep_warn(command)
            error = str(e)
            if error:
                _LOG.error(f"Failed to send command {command}: {error}")
            return ucapi.StatusCodes.BAD_REQUEST

    return ucapi.StatusCodes.OK



async def custom_remote_cmd_handler(entity: ucapi.Remote, cmd_id: str, _params: dict[str, Any] | None) -> ucapi.StatusCodes:
    """
    Custom remote entity command handler.

    Called by the integration-API if a command is sent to a configured remote entity.

    :param entity: remote entity
    :param cmd_id: command
    :param _params: optional command parameters
    :return: status of the command
    """

    if not _params:
        _LOG.info(f"Received {cmd_id} command for {entity.id}")
    else:
        _LOG.info(f"Received {cmd_id} command with parameter {_params} for entity id {entity.id}")

    custom_entities = config.Setup.get("custom_entities", python_dict=True)
    id_prefix = config.Setup.get("custom_entities_prefix")

    for entity_name, entity_config in custom_entities.items():
        if entity.id == f"{id_prefix}{entity_name.lower()}":

            match cmd_id:

                case ucapi.remote.Commands.ON | ucapi.remote.Commands.OFF | ucapi.remote.Commands.TOGGLE:
                    cmd_status = await send_command(command=cmd_id, entity_id=entity.id, entity_config=entity_config)
                    await update_remote_state(entity_id=entity.id, cmd_id=cmd_id)
                    return cmd_status

                case ucapi.remote.Commands.SEND_CMD:
                    command = _params.get("command")
                    cmd_status = await send_command(command, entity_id=entity.id, entity_config=entity_config)
                    return cmd_status

                case ucapi.remote.Commands.SEND_CMD_SEQUENCE:
                    cmd_status = await send_command_sequence(_params, entity_id=entity.id, entity_config=entity_config)
                    return cmd_status

                case _:
                    _LOG.error(f"Command \"{cmd_id}\" not implemented for custom entities")
                    return ucapi.StatusCodes.NOT_IMPLEMENTED

        _LOG.error(f"Custom entity {entity_name} not found in configuration")
        return ucapi.StatusCodes.NOT_FOUND
