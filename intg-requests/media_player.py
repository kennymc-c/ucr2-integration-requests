#!/usr/bin/env python3

import logging
from typing import Any

import ucapi
from requests import get as rq_get
from requests import put as rq_put
from requests import patch as rq_patch
from requests import post as rq_post
from requests import codes as http_codes
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
    
    rq_timeout = config.setup.get("rq_timeout")
    rq_ssl_verify = config.setup.get("rq_ssl_verify")

    
    if id in config.setup.rq_ids:
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
            #Needed as hyphens can not be used in function and variable names and also to keep the existing entity IDs to prevent activity/macro reconfiguration. 
            rq_cmd = id.replace("http-", "rq_")
            data = ""

            _LOG.debug("rq_cmd: " + rq_cmd + " , rq_timeout: " + str(rq_timeout) + " , rq_ssl_verify: " + str(rq_ssl_verify))

            try:
                if rq_ssl_verify == False:
                    #Deactivate SSL verify warning message from requests
                    import urllib3; urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
                if "§" in cmd_param:
                    url, param = cmd_param.split("§")
                    #Create python dictionary for requests data parameter from string input received from the remote
                    data = dict(pair.split("=") for pair in param.split(","))
                else:
                    url = cmd_param
                #Need to use globals()[] to use a variable as a function name
                r = globals()[rq_cmd](url, data, timeout=rq_timeout, verify=rq_ssl_verify)
            except rq_exceptions.Timeout as t:
                _LOG.error("Got timeout from Python requests module:")
                _LOG.error(t)
                return ucapi.StatusCodes.TIMEOUT
            except Exception as e:
                _LOG.error("Got error message from Python requests module:")
                _LOG.error(e)
                return ucapi.StatusCodes.CONFLICT

            if r.status_code == http_codes.ok:
                _LOG.info("Sent " + id + " request to: " + url)
                if r.text != "":
                    _LOG.debug(r.text)
                return ucapi.StatusCodes.OK
            else:
                try:
                    r.raise_for_status() #Check if status code in 400 or 500 range
                except rq_exceptions.HTTPError as e:
                    _LOG.error("Got error message from Python requests module:")
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
                _LOG.error("Got error message from Python wakeonlan module:")
                _LOG.error(v)
                return ucapi.StatusCodes.BAD_REQUEST
            except Exception as e:
                _LOG.error("Got error message from Python wakeonlan module:")
                _LOG.error(e)
                return ucapi.StatusCodes.BAD_REQUEST

            _LOG.info("Sent wake on lan magic packet to: " + cmd_param)
            return ucapi.StatusCodes.OK
        
        else:
            _LOG.error("Command not implemented: " + cmd_name)
            return ucapi.StatusCodes.NOT_IMPLEMENTED
