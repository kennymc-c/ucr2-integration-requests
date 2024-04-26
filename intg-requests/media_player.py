#!/usr/bin/env python3

import logging
from typing import Any

import ucapi
from requests import get, post, patch, put
from wakeonlan import send_magic_packet

import config
import driver

_LOG = logging.getLogger(__name__)



def mp_cmd_assigner(id: str, cmd_name: str, params: dict[str, Any] | None):

    def cmd_error(msg: str = None):
        if msg == None:
            _LOG.error("Error while executing the command: " + cmd_name + " with parameter " + params["source"] + " for entity id " + id)
            return ucapi.StatusCodes.SERVER_ERROR
        else:
            _LOG.error(msg)
            return ucapi.StatusCodes.BAD_REQUEST

    if params["source"] != "":
        cmd_param = params["source"]
    else:
        _LOG.error("Source parameter empty")
        return ucapi.StatusCodes.BAD_REQUEST
    

    
    if id == config.setup.get("id-get"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
                
                try:
                    r = get(cmd_param)
                except:
                    cmd_error()
                
                if r.status_code == 200:
                    return ucapi.StatusCodes.OK
                else:
                    cmd_error("Received http error code: " + str(r.status_code) + " from " + cmd_param)
        
        else:
            _LOG.error("Command not implemented: " + cmd_name)
            return ucapi.StatusCodes.NOT_IMPLEMENTED
    


    if id == config.setup.get("id-patch"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
                
                try:
                    r = patch(cmd_param)
                except:
                    cmd_error()
                
                if r.status_code == 200:
                    return ucapi.StatusCodes.OK
                else:
                    cmd_error("Received http error code: " + str(r.status_code) + " from " + cmd_param)
        
        else:
            _LOG.error("Command not implemented: " + cmd_name)
            return ucapi.StatusCodes.NOT_IMPLEMENTED



    if id == config.setup.get("id-post"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
                
                try:
                    r = post(cmd_param)
                except:
                    cmd_error()
                
                if r.status_code == 200:
                    return ucapi.StatusCodes.OK
                else:
                    cmd_error("Received http error code: " + str(r.status_code) + " from " + cmd_param)
        
        else:
            _LOG.error("Command not implemented: " + cmd_name)
            return ucapi.StatusCodes.NOT_IMPLEMENTED



    if id == config.setup.get("id-put"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
                
                try:
                    r = put(cmd_param)
                except:
                    cmd_error()
                
                if r.status_code == 200:
                    return ucapi.StatusCodes.OK
                else:
                    cmd_error("Received http error code: " + str(r.status_code) + " from " + cmd_param)
        
        else:
            _LOG.error("Command not implemented: " + cmd_name)
            return ucapi.StatusCodes.NOT_IMPLEMENTED
        


    if id == config.setup.get("id-wol"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:

            try:
                send_magic_packet(cmd_param)
            except ValueError:
                cmd_error(cmd_param + " is not a mac valid address")
            except Exception as e:
                cmd_error(e)

            _LOG.info("Send WoL magic packet to: " + cmd_name)
            return ucapi.StatusCodes.OK
        
        else:
            _LOG.error("Command not implemented: " + cmd_name)
            return ucapi.StatusCodes.NOT_IMPLEMENTED