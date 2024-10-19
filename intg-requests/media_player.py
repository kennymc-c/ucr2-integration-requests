#!/usr/bin/env python3

"""Module that includes the media player command assigner that assigns a requests or wol command depending on the passed entity id"""

import asyncio
import logging
import json
from json import JSONDecodeError
from typing import Any
from re import match, IGNORECASE
from ipaddress import ip_address, IPv4Address, IPv6Address, AddressValueError
import urllib3 #Needed to optionally deactivate requests ssl verify warning message

import ucapi
from requests import get as rq_get
from requests import put as rq_put
from requests import patch as rq_patch
from requests import post as rq_post
from requests import delete as rq_delete
from requests import head as rq_head
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
        if config.Setup.get("bundle_mode"):
            raise OSError("Using an IP address for wake-on-lan is not supported when running the integration on the remote due to sandbox limitations. Please use the mac address instead")
        else:
            try:
                IPv4Address(param)
                try:
                    param = get_mac_address(ip=param)
                except Exception as e:
                    _LOG.debug(e)
                if param is not None:
                    _LOG.info("Got mac address from entered ipv4 ip: " + param)
                if param == "" or param is None:
                    raise OSError("Could not convert parameter with getmac module. Discover the mac address from an ip address or a hostname may not work on all systems. \
    Please refer to the getmac supported platforms (https://github.com/GhostofGoes/getmac?tab=readme-ov-file#platforms-currently-supported)")
            except AddressValueError:
                try:
                    IPv6Address(param)
                    try:
                        param = get_mac_address(ip6=param)
                    except Exception as e:
                        _LOG.debug(e)
                    if param is not None:
                        _LOG.info("Got mac address from entered ipv6 ip: " + param)
                    if param == "" or param is None:
                        raise OSError("Could not convert parameter with getmac module. Discover the mac address from an ip address or a hostname may not work on all systems. \
    Please refer to the getmac supported platforms (https://github.com/GhostofGoes/getmac?tab=readme-ov-file#platforms-currently-supported)")
                except AddressValueError as v:
                    raise ValueError(v) from v

    if param_type == "hostname":
        if config.Setup.get("bundle_mode"):
            raise OSError("Using a hostname for wake-on-lan is not supported when running the integration on the remote due to sandbox limitations. Please use the mac address instead")
        else:
            try:
                param = get_mac_address(hostname=param)
            except Exception as e:
                _LOG.debug(e)
            if param is not None:
                _LOG.info("Got mac address from entered hostname: " + param)
            if param == "" or param is None:
                raise OSError("Could not convert parameter with getmac module. Discover the mac address from an ip address or a hostname may not work on all systems. \
    Please refer to the getmac supported platforms (https://github.com/GhostofGoes/getmac?tab=readme-ov-file#platforms-currently-supported)")

    if param == "00:00:00:00:00:00":
        raise OSError("Got an invalid mac address. Is the ip or host in your local network? \
Discover the mac address from an ip address or a hostname may not work on all systems. \
Please refer to the getmac supported platforms (https://github.com/GhostofGoes/getmac?tab=readme-ov-file#platforms-currently-supported)")

    try:
        send_magic_packet(param)
    except ValueError as v:
        raise ValueError(v) from v
    except Exception as e:
        raise Exception(e) from e

    _LOG.info("Sent wake on lan magic packet to mac address: " + param)







async def mp_cmd_assigner(entity_id: str, cmd_name: str, params: dict[str, Any] | None):
    """Run a requests or wol command depending on the passed entity id and parameter"""

    if params["source"] != "":
        cmd_param = params["source"]
    else:
        _LOG.error("Source parameter empty")
        return ucapi.StatusCodes.BAD_REQUEST
    

    def async_rq_cmd(rq_cmd: str, url: str, data: str = None, xml: bool = False):
        global cmd_status

        rq_timeout = config.Setup.get("rq_timeout")
        rq_ssl_verify = config.Setup.get("rq_ssl_verify")
        rq_fire_and_forget = config.Setup.get("rq_fire_and_forget")

        user_agent = config.Setup.get("rq_user_agent")
        headers = {"User-Agent" : user_agent} #TODO Add integration version number to user agent
        if xml is True:
            headers.update({"Content-Type" : "application/xml"})

        _LOG.debug("rq_cmd: " + rq_cmd + " , rq_timeout: " + str(rq_timeout) + " , rq_ssl_verify: " + str(rq_ssl_verify) + " , rq_fire_and_forget: " + str(rq_fire_and_forget))

        if rq_ssl_verify is False:
            #Deactivate SSL verify warning message
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        try:
            r = globals()[rq_cmd](url, data=data, headers=headers, timeout=rq_timeout, verify=rq_ssl_verify)
        except rq_exceptions.Timeout as t:
            if rq_fire_and_forget is True:
                _LOG.info("Got a timeout error but fire and forget mode is active. Return 200/OK status code to the remote")
                _LOG.debug("Ignored error: " + str(t))
                cmd_status = ucapi.StatusCodes.OK
            else:
                _LOG.error("Got a timeout error from Python requests module:")
                _LOG.error(t)
                cmd_status = ucapi.StatusCodes.TIMEOUT
        except Exception as e:
            if rq_fire_and_forget is True:
                _LOG.info("Got a requests error but fire and forget mode is active. Return 200/OK status code to the remote")
                _LOG.debug("Ignored error: " + str(e))
                cmd_status = ucapi.StatusCodes.OK
            else:
                _LOG.error("Got error message from Python requests module:")
                _LOG.error(e)
                cmd_status = ucapi.StatusCodes.CONFLICT

        if cmd_status == "":
            if r.status_code == http_codes.ok:
                _LOG.info("Sent " + rq_cmd + " request to: " + url)
                if r.text != "":
                    _LOG.debug("Server response: " + r.text)
                else:
                    _LOG.debug("Received 200 - OK status code")
                cmd_status = ucapi.StatusCodes.OK

            try:
                r.raise_for_status() #Check if status code in 400 or 500 range
            except rq_exceptions.HTTPError as e:
                _LOG.error("Got error message from Python requests module:")
                _LOG.error(e)
                if 400 <= r.status_code <= 499:
                    if r.status_code == 404:
                        if r.text != "":
                            _LOG.debug("Server response: " + r.text)
                        cmd_status = ucapi.StatusCodes.NOT_FOUND
                    cmd_status = ucapi.StatusCodes.BAD_REQUEST
                cmd_status = ucapi.StatusCodes.SERVER_ERROR
            if r.raise_for_status() is None:
                _LOG.info("Received informational or redirection http status code: " + str(r.status_code))
                if r.text != "":
                    _LOG.debug("Server response: " + r.text)
                cmd_status = ucapi.StatusCodes.OK


    if entity_id in config.Setup.rq_ids:
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
            #Needed as hyphens can not be used in function and variable names and also to keep the existing entity IDs to prevent activity/macro reconfiguration.
            rq_cmd = entity_id.replace("http-", "rq_")

            if "§" in cmd_param:
                _LOG.info("Passed parameter contains form data")
                url, form_string = cmd_param.split("§")
                #Convert passed string input into Python dict for requests
                form_dict = dict(pair.split("=") for pair in form_string.split(",")) #TODO Support multiple values for a single key. Will probably require a syntax change
                #Utilise globals()[] to be able to use a variable as a function name
                await asyncio.gather(asyncio.to_thread(async_rq_cmd, rq_cmd, url, data=form_dict), asyncio.sleep(1))
                return cmd_status

            elif "|" in cmd_param:
                _LOG.info("Passed parameter contains json data")
                url, json_string = cmd_param.split("|")
                try:
                    json_dict = json.loads(json_string)
                except JSONDecodeError as e:
                    _LOG.error("JSONDecodeError: " + str(e))
                    return ucapi.StatusCodes.CONFLICT
                await asyncio.gather(asyncio.to_thread(async_rq_cmd, rq_cmd, url, data=json_dict), asyncio.sleep(1))
                return cmd_status

            elif "^" in cmd_param:
                _LOG.info("Passed parameter contains xml data")
                url, xml_string = cmd_param.split("^")
                await asyncio.gather(asyncio.to_thread(async_rq_cmd, rq_cmd, url, data=xml_string, xml=True), asyncio.sleep(1))
                return cmd_status

            else:
                url = cmd_param
                await asyncio.gather(asyncio.to_thread(async_rq_cmd, rq_cmd, url), asyncio.sleep(1))
                return cmd_status

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
                return ucapi.StatusCodes.CONFLICT
            except Exception as e:
                _LOG.error("Got error message from Python wakeonlan module:")
                _LOG.error(e)
                return ucapi.StatusCodes.BAD_REQUEST

            return ucapi.StatusCodes.OK

        _LOG.error("Command not implemented: " + cmd_name)
        return ucapi.StatusCodes.NOT_IMPLEMENTED
