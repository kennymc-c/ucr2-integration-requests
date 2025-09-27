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



async def send_command(entity_id: str, entity_config: dict[str, Any], command: str = None) -> ucapi.StatusCodes:
    """Send a command depending on the command type from the custom entities configuration"""

    features = entity_config.get("Features").keys()
    simple_commands =  entity_config.get("Simple Commands").keys()

    # Entity feature names that are used in the configuration have a capital first letter while entity command names are all lower case
    features = [f.lower() for f in features]

    if command.lower() in features: #command.lower() if the name is send with the wrong spelling by a send command/command sequence command
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



async def handle_params(entity_id: str, entity_config: dict[str, Any], _params: dict[str, Any]) -> ucapi.StatusCodes:
    """Calculate parameters for the command and send it with send_command()"""

    command = _params.get("command")
    sequence = _params.get("sequence")
    repeat = _params.get("repeat")
    delay = _params.get("delay")
    hold = _params.get("hold")

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

    def rep_warn(command):
        if repeat != 1:
            if sequence:
                _LOG.warning("Execution of command " + command + " from command sequence " + str(sequence) + " failed. \
Remaining " + str(repeat-1) + " sequence repetition(s) will no longer be executed")
            else:
                _LOG.warning("Execution of command " + command + " failed. Remaining " + str(repeat-1) + " repetition(s) will no longer be executed")

    i = 0
    r = range(repeat)

    for i in r:
        i = i+1
        if repeat != 1:
            if sequence:
                _LOG.debug("Round " + str(i) + " for command sequence " + str(sequence))
            else:
                _LOG.debug("Round " + str(i) + " for command " + command)

        if hold != 0:
            if sequence:
                for seq_command in sequence:
                    #Hold each command of the sequence
                    cmd_start = time.time()*1000
                    _LOG.debug("Executing command " + seq_command + " from sequence " + str(sequence) + " for hold time of " + str(hold) + " milliseconds")
                    while time.time()*1000 - cmd_start < hold:
                        cmd_status = await send_command(entity_id, entity_config, seq_command)
                        if cmd_status != ucapi.StatusCodes.OK:
                            rep_warn(seq_command)
                            return cmd_status
            else:
                cmd_start = time.time()*1000
                _LOG.debug("Executing command " + command + " for hold time of " + str(hold) + " milliseconds")
                while time.time()*1000 - cmd_start < hold:
                    cmd_status = await send_command(entity_id, entity_config, command)
                    if cmd_status != ucapi.StatusCodes.OK:
                        rep_warn(command)
                        return cmd_status
                    await asyncio.sleep(0)

            await asyncio.sleep(0)

        else:
            if sequence:
                for seq_command in sequence:
                    _LOG.debug("Executing command " + seq_command + " from sequence " + str(sequence))
                    cmd_status = await send_command(entity_id, entity_config, seq_command)
                    if cmd_status != ucapi.StatusCodes.OK:
                        rep_warn(seq_command)
                        return cmd_status
            else:
                _LOG.debug("Executing command " + command)
                cmd_status = await send_command(entity_id, entity_config, command)
                if cmd_status != ucapi.StatusCodes.OK:
                    rep_warn(command)
                    return cmd_status
            await asyncio.sleep(0)

        if i < repeat:
            await asyncio.sleep(delay)

    return cmd_status



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

    if _params:
        try:
            command = _params.get("command")
            if command is None or command == "":
                _LOG.error("Command parameter is empty")
                return ucapi.StatusCodes.BAD_REQUEST
        except KeyError:
            sequence = _params.get("sequence")
            if sequence is None or sequence == "":
                _LOG.error("Sequence parameter is empty")
                return ucapi.StatusCodes.BAD_REQUEST

    custom_entities = config.Setup.get("custom_entities", python_dict=True)
    id_prefix = config.Setup.get("custom_entities_prefix")

    #Search for the entity configuration by matching the entity id with the configured custom entities
    entity_config = None
    for entity_name, config_item in custom_entities.items():
        if entity.id == f"{id_prefix}{entity_name.lower()}":
            entity_config = config_item
            break

    if entity_config is None:
        _LOG.error(f"Custom entity {entity.id} not found in configuration")
        return ucapi.StatusCodes.NOT_FOUND

    match cmd_id:
        case ucapi.remote.Commands.ON | ucapi.remote.Commands.OFF | ucapi.remote.Commands.TOGGLE:
            cmd_status = await send_command(entity_id=entity.id, entity_config=entity_config, command=cmd_id)
            if cmd_status == ucapi.StatusCodes.OK:
                await update_remote_state(entity_id=entity.id, cmd_id=cmd_id)
            else:
                _LOG.info(f"Command {cmd_id} for entity id {entity.id} failed. State will not be updated")
            return cmd_status

        case ucapi.remote.Commands.SEND_CMD | ucapi.remote.Commands.SEND_CMD_SEQUENCE:
            cmd_status = await handle_params(entity_id=entity.id, entity_config=entity_config, _params=_params)
            return cmd_status

        case _:
            _LOG.error(f"Command \"{cmd_id}\" not implemented for custom entities")
            return ucapi.StatusCodes.NOT_IMPLEMENTED
