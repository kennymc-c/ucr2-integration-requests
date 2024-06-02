#!/usr/bin/env python3

import logging
from typing import Any

import ucapi
from requests import get as rq_get
from requests import put as rq_put
from requests import patch as rq_patch
from requests import post as rq_post
from requests import codes as rq_codes
from requests import exceptions as rq_exceptions
from wakeonlan import send_magic_packet

import config

_LOG = logging.getLogger(__name__)



def mp_cmd_assigner(id: str, cmd_name: str, params: dict[str, Any] | None):

    if params["source"] != "":
        cmd_param = params["source"]
    else:
        _LOG.error("Source parameter empty")
        return ucapi.StatusCodes.BAD_REQUEST
    
    rqtimeout = config.setup.get("rq-timeout")
    
    if id == config.setup.get("id-get"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
                
            try:
                r = rq_get(cmd_param, timeout=rqtimeout)
            except rq_exceptions.Timeout as t:
                _LOG.error("Got timeout from requests module:")
                _LOG.error(t)
                return ucapi.StatusCodes.TIMEOUT
            except Exception as e:
                _LOG.error("Got error message from requests module:")
                _LOG.error(e)
                return ucapi.StatusCodes.CONFLICT

            if r.status_code == rq_codes.ok:
                _LOG.info("Send " + id + " request to: " + cmd_param)
                return ucapi.StatusCodes.OK
            else:
                try:
                    r.raise_for_status() #Check if status code in 400 or 500 range
                except rq_exceptions.HTTPError as e:
                    _LOG.error("Got error message from requests module:")
                    _LOG.error(e)
                    if 400 <= r.status_code <= 499:
                        if r.status_code == 404:
                            return ucapi.StatusCodes.NOT_FOUND
                        else:
                            return ucapi.StatusCodes.BAD_REQUEST
                    else:
                        return ucapi.StatusCodes.SERVER_ERROR
                if r.raise_for_status() == None:
                    _LOG.info("Received informational or redirection http status code: " + str(r.status_code))
                    return ucapi.StatusCodes.OK
        
        else:
            _LOG.error("Command not implemented: " + cmd_name)
            return ucapi.StatusCodes.NOT_IMPLEMENTED
    


    if id == config.setup.get("id-patch"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
                
            try:
                r = rq_patch(cmd_param, timeout=rqtimeout)
            except rq_exceptions.Timeout as t:
                _LOG.error("Got timeout from requests module:")
                _LOG.error(t)
                return ucapi.StatusCodes.TIMEOUT
            except Exception as e:
                _LOG.error("Got error message from requests module:")
                _LOG.error(e)
                return ucapi.StatusCodes.CONFLICT

            if r.status_code == rq_codes.ok:
                _LOG.info("Send " + id + " request to: " + cmd_param)
                return ucapi.StatusCodes.OK
            else:
                try:
                    r.raise_for_status() #Check if status code in 400 or 500 range
                except rq_exceptions.HTTPError as e:
                    _LOG.error("Got error message from requests module:")
                    _LOG.error(e)
                    if 400 <= r.status_code <= 499:
                        if r.status_code == 404:
                            return ucapi.StatusCodes.NOT_FOUND
                        else:
                            return ucapi.StatusCodes.BAD_REQUEST
                    else:
                        return ucapi.StatusCodes.SERVER_ERROR
                if r.raise_for_status() == None:
                    _LOG.info("Received informational or redirection http status code: " + str(r.status_code))
                    return ucapi.StatusCodes.OK
        
        else:
            _LOG.error("Command not implemented: " + cmd_name)
            return ucapi.StatusCodes.NOT_IMPLEMENTED



    if id == config.setup.get("id-post"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
                
            try:
                url, param = cmd_param.split('$')
                data = dict(pair.split('=') for pair in param.split(','))
                r = rq_post(url, data, timeout=rqtimeout)
            except rq_exceptions.Timeout as t:
                _LOG.error("Got timeout from requests module:")
                _LOG.error(t)
                return ucapi.StatusCodes.TIMEOUT
            except Exception as e:
                _LOG.error("Got error message from requests module:")
                _LOG.error(e)
                return ucapi.StatusCodes.CONFLICT

            if r.status_code == rq_codes.ok:
                _LOG.info("Send " + id + " request to: " + cmd_param)
                return ucapi.StatusCodes.OK
            else:
                try:
                    r.raise_for_status() #Check if status code in 400 or 500 range
                except rq_exceptions.HTTPError as e:
                    _LOG.error("Got error message from requests module:")
                    _LOG.error(e)
                    if 400 <= r.status_code <= 499:
                        if r.status_code == 404:
                            return ucapi.StatusCodes.NOT_FOUND
                        else:
                            return ucapi.StatusCodes.BAD_REQUEST
                    else:
                        return ucapi.StatusCodes.SERVER_ERROR
                if r.raise_for_status() == None:
                    _LOG.info("Received informational or redirection http status code: " + str(r.status_code))
                    return ucapi.StatusCodes.OK
        
        else:
            _LOG.error("Command not implemented: " + cmd_name)
            return ucapi.StatusCodes.NOT_IMPLEMENTED



    if id == config.setup.get("id-put"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
                
            try:
                r = rq_put(cmd_param, timeout=rqtimeout)
            except rq_exceptions.Timeout as t:
                _LOG.error("Got timeout from requests module:")
                _LOG.error(t)
                return ucapi.StatusCodes.TIMEOUT
            except Exception as e:
                _LOG.error("Got error message from requests module:")
                _LOG.error(e)
                return ucapi.StatusCodes.CONFLICT

            if r.status_code == rq_codes.ok:
                _LOG.info("Send " + id + " request to: " + cmd_param)
                return ucapi.StatusCodes.OK
            else:
                try:
                    r.raise_for_status() #Check if status code in 400 or 500 range
                except rq_exceptions.HTTPError as e:
                    _LOG.error("Got error message from requests module:")
                    _LOG.error(e)
                    if 400 <= r.status_code <= 499:
                        if r.status_code == 404:
                            return ucapi.StatusCodes.NOT_FOUND
                        else:
                            return ucapi.StatusCodes.BAD_REQUEST
                    else:
                        return ucapi.StatusCodes.SERVER_ERROR
                if r.raise_for_status() == None:
                    _LOG.info("Received informational or redirection http status code: " + str(r.status_code))
                    return ucapi.StatusCodes.OK
        
        else:
            _LOG.error("Command not implemented: " + cmd_name)
            return ucapi.StatusCodes.NOT_IMPLEMENTED
        


    if id == config.setup.get("id-wol"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:

            try:
                send_magic_packet(cmd_param)
            except ValueError as v:
                _LOG.error("Got error message from wakeonlan module:")
                _LOG.error(v)
                return ucapi.StatusCodes.BAD_REQUEST
            except Exception as e:
                _LOG.error("Got error message from wakeonlan module:")
                _LOG.error(e)
                return ucapi.StatusCodes.BAD_REQUEST

            _LOG.info("Send wake on lan magic packet to: " + cmd_param)
            return ucapi.StatusCodes.OK
        
        else:
            _LOG.error("Command not implemented: " + cmd_name)
            return ucapi.StatusCodes.NOT_IMPLEMENTED
