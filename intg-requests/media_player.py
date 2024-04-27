#!/usr/bin/env python3

import logging
from typing import Any

import ucapi
from requests import get, post, patch, put
from wakeonlan import send_magic_packet

import config

_LOG = logging.getLogger(__name__)



def mp_cmd_assigner(id: str, cmd_name: str, params: dict[str, Any] | None):

    if params["source"] != "":
        cmd_param = params["source"]
    else:
        _LOG.error("Source parameter empty")
        return ucapi.StatusCodes.BAD_REQUEST
    
    if id == config.setup.get("id-get"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
                
                try:
                    r = get(cmd_param)
                except Exception as e:
                    _LOG.info("Got error message from requests module:")
                    _LOG.error(e)
                    return ucapi.StatusCodes.BAD_REQUEST
                
                if r.status_code == 200:
                    _LOG.info("Send http get request to: " + cmd_param)
                    return ucapi.StatusCodes.OK
                else:
                    msg = "Received http error code: " + str(r.status_code) + " from " + cmd_param
                    _LOG.error(msg)
                    return ucapi.StatusCodes.SERVER_ERROR
        
        else:
            _LOG.error("Command not implemented: " + cmd_name)
            return ucapi.StatusCodes.NOT_IMPLEMENTED
    


    if id == config.setup.get("id-patch"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
                
                try:
                    r = patch(cmd_param)
                except Exception as e:
                    _LOG.info("Got error message from requests module:")
                    _LOG.error(e)
                    return ucapi.StatusCodes.BAD_REQUEST
                
                if r.status_code == 200:
                    _LOG.info("Send http patch request to: " + cmd_param)
                    return ucapi.StatusCodes.OK
                else:
                    msg = "Received http error code: " + str(r.status_code) + " from " + cmd_param
                    _LOG.error(msg)
                    return ucapi.StatusCodes.SERVER_ERROR
        
        else:
            _LOG.error("Command not implemented: " + cmd_name)
            return ucapi.StatusCodes.NOT_IMPLEMENTED



    if id == config.setup.get("id-post"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
                
                try:
                    r = post(cmd_param)
                except Exception as e:
                    _LOG.info("Got error message from requests module:")
                    _LOG.error(e)
                    return ucapi.StatusCodes.BAD_REQUEST
                
                if r.status_code == 200:
                    _LOG.info("Send http post request to: " + cmd_param)
                    return ucapi.StatusCodes.OK
                else:
                    msg = "Received http error code: " + str(r.status_code) + " from " + cmd_param
                    _LOG.error(msg)
                    return ucapi.StatusCodes.SERVER_ERROR
        
        else:
            _LOG.error("Command not implemented: " + cmd_name)
            return ucapi.StatusCodes.NOT_IMPLEMENTED



    if id == config.setup.get("id-put"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
                
                try:
                    r = put(cmd_param)
                except Exception as e:
                    _LOG.info("Got error message from requests module:")
                    _LOG.error(e)
                    return ucapi.StatusCodes.BAD_REQUEST
                
                if r.status_code == 200:
                    _LOG.info("Send http put request to: " + cmd_param)
                    return ucapi.StatusCodes.OK
                else:
                    msg = "Received http error code: " + str(r.status_code) + " from " + cmd_param
                    _LOG.error(msg)
                    return ucapi.StatusCodes.SERVER_ERROR
        
        else:
            _LOG.error("Command not implemented: " + cmd_name)
            return ucapi.StatusCodes.NOT_IMPLEMENTED
        


    if id == config.setup.get("id-wol"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:

            try:
                send_magic_packet(cmd_param)
            except ValueError:
                _LOG.error(cmd_param + " is not a mac valid address")
                return ucapi.StatusCodes.BAD_REQUEST
            except Exception as e:
                _LOG.error(e)
                return ucapi.StatusCodes.BAD_REQUEST

            _LOG.info("Send WoL magic packet to: " + cmd_name)
            return ucapi.StatusCodes.OK
        
        else:
            _LOG.error("Command not implemented: " + cmd_name)
            return ucapi.StatusCodes.NOT_IMPLEMENTED