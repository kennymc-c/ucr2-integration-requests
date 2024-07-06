#!/usr/bin/env python3

"""Module that includes the media player command assigner that assigns a requests or wol command depending on the passed entity id"""

import logging
from typing import Any
from re import match, IGNORECASE
from ipaddress import ip_address, IPv4Address, IPv6Address, AddressValueError
import urllib3 #Needed to deactivate requests ssl verify warning message

import ucapi
from requests import get as rq_get
from requests import put as rq_put
from requests import patch as rq_patch
from requests import post as rq_post
from requests import codes as http_codes
from requests import exceptions as rq_exceptions
from wakeonlan import send_magic_packet
from getmac import get_mac_address

import config

_LOG = logging.getLogger(__name__)



def wol(param: str):
    """Sends a magic packet to a passed string. If a valid ip address or hostname is passed instead of a mac address the mac address will be automatically discovered.\
    If the mac address can not be discovered a value error is raised if """

    try:
        ip_address(param)
        param_type = "ip"
        _LOG.debug("Entered WoL parameter is an ip address. Using getmac to discover mac address")
    except ValueError:
        is_valid_mac = match(r"([0-9A-F]{2}[:]){5}[0-9A-F]{2}|"r"([0-9A-F]{2}[-]){5}[0-9A-F]{2}",string=param,flags=IGNORECASE) #RegEx for mac addresses
        try:
            bool(is_valid_mac.group())
            param_type = "mac"
            _LOG.debug("Entered WoL parameter is a mac address")
        except AttributeError:
            param_type = "hostname"
            _LOG.debug("Entered WoL parameter could be a hostname. Using getmac to discover mac address")

    if param_type == "ip":
        try:
            IPv4Address(param)
            param = get_mac_address(ip=param)
            _LOG.info("Got mac address from entered ipv4 ip: " + param)
        except AddressValueError:
            try:
                IPv6Address(param)
                param = get_mac_address(ip6=param)
                _LOG.info("Got mac address from entered ipv6 ip: " + param)
            except AddressValueError as v:
                raise ValueError(v) from v
    if param_type == "hostname":
        param = get_mac_address(hostname=param)
        if param is not None:
            _LOG.info("Got mac address from entered hostname: " + param)
        else:
            raise ValueError()

    if param == "00:00:00:00:00:00":
        raise OSError("Got an invalid mac address. Is the ip or host in your local network? \
Discover the mac address from an ip address or a hostname may not work on all systems. \
Please refer to the getmac supported platforms (https://github.com/GhostofGoes/getmac?tab=readme-ov-file#platforms-currently-supported)")
    if param is None:
        raise AddressValueError("")

    try:
        send_magic_packet(param)
    except ValueError as v:
        raise ValueError(v) from v
    except Exception as e:
        raise Exception(e) from e

    _LOG.info("Sent wake on lan magic packet to mac address: " + param)



def mp_cmd_assigner(entity_id: str, cmd_name: str, params: dict[str, Any] | None):
    """Run a requests or wol command depending on the passed entity id and parameter"""

    if params["source"] != "":
        cmd_param = params["source"]
    else:
        _LOG.error("Source parameter empty")
        return ucapi.StatusCodes.BAD_REQUEST

    rq_timeout = config.Setup.get("rq_timeout")
    rq_ssl_verify = config.Setup.get("rq_ssl_verify")

    if entity_id in config.Setup.rq_ids:
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
            #Needed as hyphens can not be used in function and variable names and also to keep the existing entity IDs to prevent activity/macro reconfiguration.
            rq_cmd = entity_id.replace("http-", "rq_")
            data = ""

            _LOG.debug("rq_cmd: " + rq_cmd + " , rq_timeout: " + str(rq_timeout) + " , rq_ssl_verify: " + str(rq_ssl_verify))

            try:
                if rq_ssl_verify is False:
                    #Deactivate SSL verify warning message from requests
                    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
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
                _LOG.info("Sent " + entity_id + " request to: " + url)
                if r.text != "":
                    _LOG.debug(r.text)
                return ucapi.StatusCodes.OK

            try:
                r.raise_for_status() #Check if status code in 400 or 500 range
            except rq_exceptions.HTTPError as e:
                _LOG.error("Got error message from Python requests module:")
                _LOG.error(e)
                if 400 <= r.status_code <= 499:
                    if r.status_code == 404:
                        return ucapi.StatusCodes.NOT_FOUND
                    return ucapi.StatusCodes.BAD_REQUEST
                return ucapi.StatusCodes.SERVER_ERROR
            if r.raise_for_status() is None:
                _LOG.info("Received informational or redirection http status code: " + str(r.status_code))
                return ucapi.StatusCodes.OK

        else:
            _LOG.error("Command not implemented: " + cmd_name)
            return ucapi.StatusCodes.NOT_IMPLEMENTED



    if entity_id == config.Setup.get("id-wol"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:

            try:
                wol(cmd_param)
            except ValueError as v:
                _LOG.error(v)
                _LOG.error("Used WoL parameter \"" + cmd_param + "\" is not a valid or reachable hostname, mac or ip address")
                return ucapi.StatusCodes.BAD_REQUEST
            except OSError as o:
                _LOG.error(o)
                return ucapi.StatusCodes.BAD_REQUEST
            except Exception as e:
                _LOG.error("Got error message from Python wakeonlan module:")
                _LOG.error(e)
                return ucapi.StatusCodes.BAD_REQUEST

            return ucapi.StatusCodes.OK

        _LOG.error("Command not implemented: " + cmd_name)
        return ucapi.StatusCodes.NOT_IMPLEMENTED
