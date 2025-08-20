#!/usr/bin/env python3

"""Module that includes the media player command assigner thats sends parameters to the commands module depending on the passed entity id"""

import asyncio
import logging
from typing import Any

import ucapi
import config
import driver
import commands

_LOG = logging.getLogger(__name__)



def update_rq_media_widget(entity_id:str, response: str):
    """Update the response in the media player widget"""

    if driver.api.configured_entities.get(entity_id) is None:
        _LOG.info(f"Entity {entity_id} not found in configured entities. Skip updating attributes")
        return True

    attributes_to_send = {ucapi.media_player.Attributes.MEDIA_TITLE: response}

    try:
        driver.api.configured_entities.update_attributes(entity_id, attributes_to_send)
    except Exception as e:
        raise Exception("Error while updating attributes for entity id " + entity_id) from e

    _LOG.info("Updated entity attribute(s) " + str(attributes_to_send) + " for " + entity_id)



async def mp_cmd_assigner(entity_id: str, cmd_name: str, params: dict[str, Any] | None):
    """Run a requests, wol or text over tcp command depending on the passed entity id and parameter"""

    try:
        cmd_param = params["source"]
    except KeyError:
        _LOG.error("Source parameter empty")
        return ucapi.StatusCodes.BAD_REQUEST



    if entity_id in config.Setup.rq_ids:
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
            method = entity_id.replace("http-", "")

            # Use asyncio.gather() to run the function in a separate thread and use asyncio.sleep(0) to prevent blocking the event loop
            # This is needed because the Python requests library is blocking and we want to run it in a non-blocking way
            cmd_status = await asyncio.gather(asyncio.to_thread(commands.http_request, method, cmd_param), asyncio.sleep(0))
            #Return the return value of rq_cmd which is the first command in asyncio.gather()
            return cmd_status[0]

        _LOG.error("Command not implemented: " + cmd_name)
        return ucapi.StatusCodes.NOT_IMPLEMENTED



    if entity_id == config.Setup.get("id-wol"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
            cmd_status = await commands.wol(cmd_param)
            return cmd_status

        _LOG.error("Command not implemented: " + cmd_name)
        return ucapi.StatusCodes.NOT_IMPLEMENTED



    if entity_id == config.Setup.get("id-tcp-text"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
            cmd_status = await commands.tcp_text(cmd_param)
            return cmd_status

        _LOG.error("Command not implemented: " + cmd_name)
        return ucapi.StatusCodes.NOT_IMPLEMENTED
