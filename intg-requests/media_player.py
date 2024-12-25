#!/usr/bin/env python3

"""Module that includes the media player command assigner that assigns a requests or wol command depending on the passed entity id"""

import asyncio
import logging
import json
from json import JSONDecodeError
from typing import Any

from re import sub, match, IGNORECASE
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



def get_mac(param: str):
    """Accepts mac, ip addresses or hostnames. Get the mac address or checks if the mac address is valid.\
    If the mac address can not be discovered a value error is raised"""

    try:
        ip_address(param)
        param_type = "ip"
        _LOG.debug("\""+param+"\" is an ip address. Using getmac to discover mac address")
    except ValueError:
        #RegEx for mac addresses with colons or hyphens
        is_valid_mac = match(r"([0-9A-F]{2}[:]){5}[0-9A-F]{2}|"r"([0-9A-F]{2}[-]){5}[0-9A-F]{2}",string=param,flags=IGNORECASE)
        try:
            bool(is_valid_mac.group())
            param_type = "mac"
            _LOG.debug("\""+param+"\"  is a mac address")
        except AttributeError:
            param_type = "hostname"
            _LOG.debug("\""+param+"\" could be a hostname. Using getmac to discover the mac address")

    if param_type == "ip":
        if config.Setup.get("bundle_mode"):
            raise OSError("Using an IP address for wake-on-lan is not supported when running the integration on the remote due to sandbox limitations. \
Please use the mac address instead")
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
                    raise OSError("Could not convert ipv4 with getmac module. Discover the mac address from an ip address or a hostname may not work on all systems. \
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
                        raise OSError("Could not convert ipv6 with getmac module. Discover the mac address from an ip address or a hostname may not work on all systems. \
    Please refer to the getmac supported platforms (https://github.com/GhostofGoes/getmac?tab=readme-ov-file#platforms-currently-supported)")
                except AddressValueError as v:
                    raise ValueError(v) from v

    if param_type == "hostname":
        if config.Setup.get("bundle_mode"):
            raise OSError("Using a hostname for wake-on-lan is not supported when running the integration on the remote due to sandbox limitations. \
Please use the mac address instead")
        else:
            try:
                param = get_mac_address(hostname=param)
            except Exception as e:
                _LOG.debug(e)
            if param is not None:
                _LOG.info("Got mac address from entered hostname: " + param)
            if param == "" or param is None:
                raise OSError("Could not convert hostname with getmac module. Discover the mac address from an ip address or a hostname may not work on all systems. \
Please refer to the getmac supported platforms (https://github.com/GhostofGoes/getmac?tab=readme-ov-file#platforms-currently-supported)")

    if param == "00:00:00:00:00:00":
        raise OSError("Got an invalid mac address. Is the ip or host in your local network? \
Discover the mac address from an ip address or a hostname may not work on all systems. \
Please refer to the getmac supported platforms (https://github.com/GhostofGoes/getmac?tab=readme-ov-file#platforms-currently-supported)")

    return param



def rq_cmd(rq_cmd_name: str, url: str, data: str = None, xml: bool = False):
    """Send a requests command to the passed url with the passed data and return the status code"""
    rq_timeout = config.Setup.get("rq_timeout")
    rq_ssl_verify = config.Setup.get("rq_ssl_verify")
    rq_fire_and_forget = config.Setup.get("rq_fire_and_forget")

    user_agent = config.Setup.get("rq_user_agent")
    headers = {"User-Agent" : user_agent}
    if xml is True:
        headers.update({"Content-Type" : "application/xml"})

    _LOG.debug("rq_cmd_name: " + rq_cmd_name + ", rq_timeout: " + str(rq_timeout) + ", rq_ssl_verify: " + str(rq_ssl_verify) + \
", rq_fire_and_forget: " + str(rq_fire_and_forget))

    if rq_ssl_verify is False:
        #Deactivate SSL verify warning message
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        #Utilise globals()[] to be able to use a variable as a function name, save server response in a variable and catch exceptions
        response = globals()[rq_cmd_name](url, data=data, headers=headers, timeout=rq_timeout, verify=rq_ssl_verify)
    except rq_exceptions.Timeout as t:
        if rq_fire_and_forget is True:
            _LOG.info("Got a timeout error but fire and forget mode is active. Return 200/OK status code to the remote")
            _LOG.debug("Ignored error: " + str(t))
            return ucapi.StatusCodes.OK
        else:
            _LOG.error("Got a timeout error from Python requests module:")
            _LOG.error(t)
            return ucapi.StatusCodes.TIMEOUT
    except Exception as e:
        if rq_fire_and_forget is True:
            _LOG.info("Got a requests error but fire and forget mode is active. Return 200/OK status code to the remote")
            _LOG.debug("Ignored error: " + str(e))
            return ucapi.StatusCodes.OK
        else:
            _LOG.error("Got error message from Python requests module:")
            _LOG.error(e)
            return ucapi.StatusCodes.CONFLICT

    if response.status_code == http_codes.ok:
        _LOG.info("Sent " + rq_cmd_name + " request to: " + url)
        if response.text != "":
            _LOG.debug("Server response: " + response.text)
        else:
            _LOG.debug("Received 200 - OK status code")
        return ucapi.StatusCodes.OK

    try:
        response.raise_for_status() #Check if status code in 400 or 500 range
    except rq_exceptions.HTTPError as e:
        _LOG.error("Got error message from Python requests module:")
        _LOG.error(e)
        if 400 <= response.status_code <= 499:
            if response.status_code == 404:
                if response.text != "":
                    _LOG.debug("Server response: " + response.text)
                return ucapi.StatusCodes.NOT_FOUND
            return ucapi.StatusCodes.BAD_REQUEST
        return ucapi.StatusCodes.SERVER_ERROR

    if response.raise_for_status() is None:
        _LOG.info("Received informational or redirection http status code: " + str(response.status_code))
        if response.text != "":
            _LOG.debug("Server response: " + response.text)
        return ucapi.StatusCodes.OK



def tcp_text_process_control_data(data):
    """
    - Hex style control characters such as "0x09" are processed and can be be escaped with a leading "0\\\" (e.g. 0\\\x09)
    - C++ control characters such as "\n", "\t" are also processed and can be escaped with a leading single additional backslash (e.g. \\n)
    """

    # Search for hex style escape characters (starting with \\)
    def replace_literal_hex(match):
        return match.group(1)

    # replace \\0xHH (with a double backslash) through string/literal value
    data = sub(r"\\\\(0x[0-9A-Fa-f]{2})", replace_literal_hex, data)

    # Match real hex style control characters (0xHH)
    def replace_control_hex(match):
        return chr(int(match.group(1), 16))

    # Replace 0xHH with the corresponding control character
    data = sub(r"(?<!\\)(0x[0-9A-Fa-f]{2})", replace_control_hex, data)

    # Process C++ style control characters (\n, \t, etc.)
    data = data.encode("utf-8").decode("unicode_escape")

    return data



async def tcp_text_cmd(cmd_param:str) -> str:
    """Send a text over tcp command to the passed address and return the status code"""
    address, data =cmd_param.split(",", 1) #Split only at the 1st comma to ignore all others that may be included in the text to be send
    host, port = address.split(":")
    timeout = config.Setup.get("tcp_text_timeout")

    port = int(port)
    data = data.strip().strip('"\'') #Remove spaces and (double) quotes at the beginning and the end
    data = tcp_text_process_control_data(data)

    try:
        reader, writer = await asyncio.open_connection(host, port)
        writer.write((data + "\n").encode("utf-8"))
        await writer.drain()

        received = ""
        received = await asyncio.wait_for(reader.read(1024), timeout)
        received = received.decode("utf-8")
    except asyncio.TimeoutError:
        _LOG.error("A timeout error occurred while connecting to the server")
        _LOG.info("Please check if the client software is running on the host")
        return ucapi.StatusCodes.TIMEOUT
    except Exception as e:
        _LOG.error("An error occurred while connecting to the server:")
        _LOG.error(e)
        _LOG.info("Please check if host and port are correct and can be reached from the network in which the integration is running")
        return ucapi.StatusCodes.BAD_REQUEST

    _LOG.info("Sent raw text " + repr(format(data)) + " over TCP to " + address)
    if received != "":
        _LOG.info("Received data: " + format(received))
    return ucapi.StatusCodes.OK



async def mp_cmd_assigner(entity_id: str, cmd_name: str, params: dict[str, Any] | None):
    """Run a requests, wol or text over tcp command depending on the passed entity id and parameter"""

    try:
        cmd_param = params["source"]
    except KeyError:
        _LOG.error("Source parameter empty")
        return ucapi.StatusCodes.BAD_REQUEST

    if entity_id in config.Setup.rq_ids:
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
            #Needed as hyphens can not be used in function and variable names and also to keep the existing entity IDs to prevent activity/macro reconfiguration.
            rq_cmd_name = entity_id.replace("http-", "rq_")

            #TODO Try to use the same syntax as requests module. Experiment with split parameters (e.g. just use first n appearances of a character)
            if "§" in cmd_param:
                _LOG.info("Passed parameter contains form data")
                url, form_string = cmd_param.split("§")
                #Convert passed string input into Python dict for requests
                form_dict = dict(pair.split("=") for pair in form_string.split(",")) #TODO Support multiple values for a single key. Will probably require a syntax change
                #Use asyncio.gather() to run the function in a separate thread and use asyncio.sleep(0) to prevent blocking the event loop
                cmd_status = await asyncio.gather(asyncio.to_thread(rq_cmd, rq_cmd_name, url, data=form_dict), asyncio.sleep(0))
                return cmd_status[0] #Return the return value of rq_cmd which is the first command in asyncio.gather()

            if "|" in cmd_param:
                _LOG.info("Passed parameter contains json data")
                url, json_string = cmd_param.split("|")
                try:
                    json_dict = json.loads(json_string)
                except JSONDecodeError as e:
                    _LOG.error("JSONDecodeError: " + str(e))
                    return ucapi.StatusCodes.CONFLICT
                cmd_status = await asyncio.gather(asyncio.to_thread(rq_cmd, rq_cmd_name, url, data=json_dict), asyncio.sleep(0))
                return cmd_status[0]

            if "^" in cmd_param:
                _LOG.info("Passed parameter contains xml data")
                url, xml_string = cmd_param.split("^")
                cmd_status = await asyncio.gather(asyncio.to_thread(rq_cmd, rq_cmd_name, url, data=xml_string, xml=True), asyncio.sleep(0))
                return cmd_status[0]

            url = cmd_param
            cmd_status = await asyncio.gather(asyncio.to_thread(rq_cmd, rq_cmd_name, url), asyncio.sleep(0))
            return cmd_status[0]

        _LOG.error("Command not implemented: " + cmd_name)
        return ucapi.StatusCodes.NOT_IMPLEMENTED



    if entity_id == config.Setup.get("id-wol"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:

            params = {}
            addresses = []
            value = ""

            if "," in cmd_param:
                _LOG.info("Passed parameter contains more than one address and/or wol parameters")
                values = cmd_param.split(",")

                for value in values:
                    value = value.strip()
                    if "=" in value:
                        name, param = value.split("=")
                        if name == "port":
                            param = int(param)
                        params[name] = param
                    else:
                        addresses.append(value)
            else:
                addresses.append(cmd_param)

            macs = []
            if addresses:
                for address in addresses:
                    try:
                        mac = get_mac(address)
                    except ValueError as v:
                        _LOG.error(v)
                        _LOG.error("Used WoL parameter \"" + value + "\" is not a valid hostname, mac or ip address")
                        return ucapi.StatusCodes.BAD_REQUEST
                    except OSError as o:
                        _LOG.error(o)
                        return ucapi.StatusCodes.CONFLICT
                    except Exception as e:
                        _LOG.error("Got an error while retrieving the mac address")
                        _LOG.error(e)
                        return ucapi.StatusCodes.BAD_REQUEST
                    macs.append(mac)

            try:
                #TODO Run via asyncio.gather() to prevent potential blocking the event loop
                send_magic_packet(*macs, **params) #Unpack macs list with * and params dicts list with **
            except ValueError as v:
                _LOG.error(v)
                return ucapi.StatusCodes.BAD_REQUEST
            except Exception as e:
                _LOG.error("Got an error message from Python wakeonlan module:")
                _LOG.error(e)
                return ucapi.StatusCodes.BAD_REQUEST

            _LOG.info("Sent wake on lan magic packet to mac address(es)): " + str(macs))
            return ucapi.StatusCodes.OK

        _LOG.error("Command not implemented: " + cmd_name)
        return ucapi.StatusCodes.NOT_IMPLEMENTED



    if entity_id == config.Setup.get("id-tcp-text"):
        if cmd_name == ucapi.media_player.Commands.SELECT_SOURCE:
            cmd_status = await tcp_text_cmd(cmd_param)
            return cmd_status

        _LOG.error("Command not implemented: " + cmd_name)
        return ucapi.StatusCodes.NOT_IMPLEMENTED
