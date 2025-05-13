#!/usr/bin/env python3

"""Module that includes the media player command assigner that assigns a requests or wol command depending on the passed entity id"""

import asyncio
import logging
import json
from json import JSONDecodeError
from typing import Any
import ast
import shlex

from re import sub, match, search, IGNORECASE
from ipaddress import ip_address, IPv4Address, IPv6Address, AddressValueError
import urllib3 #Needed to optionally deactivate requests ssl verify warning message

import ucapi
from requests import request
from requests import codes as http_codes
from requests import exceptions as rq_exceptions
from wakeonlan import send_magic_packet
from getmac import get_mac_address

import config
import sensor
import driver

_LOG = logging.getLogger(__name__)



def get_mac(param: str):
    """Accepts mac, ip addresses or host names. Get the mac address or checks if the mac address is valid.\
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


def parse_rq_response(response: str):
    """Parse http request response with configured regular expression"""

    regex = config.Setup.get("rq_response_regex")
    nomatch_option = config.Setup.get("rq_response_nomatch_option")

    if regex == "":
        parsed_response = response
        _LOG.debug("No regular expression set for the http request response sensor. The complete response will be used")
    else:
        match = search(regex, response)
        if match:
            parsed_response = match.group(1)
            _LOG.debug("Parsed response from configured regex: " + parsed_response)
        else:
            _LOG.warning("No matches found in the http request response for the regular expression " + regex)

            if nomatch_option == "full":
                _LOG.debug("The full response will be used instead")
                parsed_response = response
            elif nomatch_option == "error":
                _LOG.debug("An error message will be used instead")
                #TODO #WAIT Add a translation for the error message when get_localization_cfg() is implemented in the Python API
                parsed_response = "No match found"
            elif nomatch_option == "empty":
                _LOG.debug("An empty response will be used instead")
                parsed_response = ""

    return parsed_response



def update_response(method:str, response: str):
    """Update the response in the sensor entity and media player widget"""

    entity_id = "http-" + method

    parsed_response = parse_rq_response(response)

    try:
        sensor.update_rq_sensor(config.Setup.get("id-rq-sensor"), parsed_response)
    except ModuleNotFoundError as f:
        _LOG.info(f)
    except Exception as e:
        _LOG.error(e)

    update_rq_media_widget(entity_id, parsed_response)



def update_rq_media_widget(entity_id:str, response: str):
    """Update the response in the media player widget"""

    attributes_to_send = {ucapi.media_player.Attributes.MEDIA_TITLE: response}

    try:
        api_update_attributes = driver.api.configured_entities.update_attributes(entity_id, attributes_to_send)
    except Exception as e:
        raise Exception("Error while updating attributes for entity id " + entity_id) from e

    if not api_update_attributes:
        raise Exception("Entity " + entity_id + " not found. Please make sure it's added as a configured entity on the remote")
    else:
        _LOG.info("Updated entity attribute(s) " + str(attributes_to_send) + " for " + entity_id)



def rq_cmd(method: str, cmd_param: str=None) -> int:
    """Send a requests command to the passed url with the passed data and return the status code"""

    rq_ssl_verify = config.Setup.get("rq_ssl_verify")
    rq_fire_and_forget = config.Setup.get("rq_fire_and_forget")
    rq_timeout = config.Setup.get("rq_timeout")
    rq_user_agent = config.Setup.get("rq_user_agent")

    params = {}

    #TODO Remove legacy syntax in a future version
    if config.Setup.get("rq_legacy"):
        _LOG.warning("You are using the legacy http requests syntax. Please update your configuration to use the new syntax as described in the documentation. \
The legacy syntax will be removed in a future version")

        if "§" in cmd_param:
            _LOG.info("Passed parameter contains form data")
            url, form_string = cmd_param.split("§")
            #Convert passed string input into Python dict for requests
            params["data"] = dict(pair.split("=") for pair in form_string.split(","))

        elif "|" in cmd_param:
            _LOG.info("Passed parameter contains json data")
            url, json_string = cmd_param.split("|")
            try:
                params["json"] = json.loads(json_string)
            except JSONDecodeError as e:
                _LOG.error("JSONDecodeError: " + str(e))
                return ucapi.StatusCodes.CONFLICT

        elif "^" in cmd_param:
            _LOG.info("Passed parameter contains xml data")
            url, params["data"] = cmd_param.split("^")
            params["headers"] = {"Content-Type" : "application/xml"}

        else:
            url = cmd_param

    else:
        if cmd_param.startswith(("http://", "https://")):
            url = cmd_param
        else:
            lexer = shlex.shlex(cmd_param, posix=True) # Use shlex to handle command argument like parameters
            lexer.whitespace_split = True
            lexer.whitespace = "," #Use comma as separator
            lexer.quotes = '"' #Handle everything in double quotes as one value

            #Parse the cmd_param string into a dictionary of parameters
            for param in lexer:
                try:
                    key, value = param.split("=", 1)
                except ValueError:
                    if key is None or "":
                        key = "Unknown key"
                        _LOG.error("The parameter key is incorrectly formatted. Please use a syntax like key=\"value\" in the source parameter")
                    _LOG.error("The parameter value for \"" + key + " \" is not in the correct format. \
Please put it in double quotes and use single quotes inside when the value itself contains double quotes")
                    return ucapi.StatusCodes.BAD_REQUEST

                #Prevent boolean values from being passed as strings
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False

                try:
                    value = ast.literal_eval(value) #Try to convert value to Python data type (e.g. dicts)
                except (ValueError, SyntaxError):
                    #Use value as string if ast.literal_eval fails
                    pass

                params[key.strip()] = value

            url = params.pop("url", None)
            if not url:
                _LOG.error("A url is required. Please use a syntax like url=\"http://example.com\" in the source parameter")
                return ucapi.StatusCodes.BAD_REQUEST

            if "ffg" in params:
                rq_fire_and_forget = params.pop("ffg")
                _LOG.debug("Custom fire and forget setting " +  str(rq_fire_and_forget) + " defined with 'ffg' command parameter. \
Ignoring global setting: " + str(config.Setup.get("rq_fire_and_forget")))

    if "headers" in params:
        if "User-Agent" not in params["headers"]:
            params["headers"].update({"User-Agent": rq_user_agent})
        else:
            _LOG.info("Custom user agent defined in headers command parameter. Ignoring global http requests user agent: " + rq_user_agent)
    else:
        params["headers"] = {"User-Agent": rq_user_agent}

    if "timeout" in params:
        _LOG.info("Custom timeout of " +  str(params["timeout"]) + " seconds defined with 'timeout' command parameter. \
Ignoring global http requests timeout of " + str(rq_timeout) + " seconds")
    else:
        params["timeout"] = rq_timeout

    if "verify" in params:
        _LOG.info("Custom SSL verification setting " +  str(params["verify"]) + " defined with 'verify' command parameter. \
Ignoring global ssl verification setting: " + str(rq_ssl_verify))
        if not params["verify"]:
            #Deactivate SSL verify warning message
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    else:
        params["verify"] = rq_ssl_verify
        if not rq_ssl_verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    _LOG.debug("method: " + method + ", fire_and_forget: " + str(rq_fire_and_forget) + ", url: " + url + ", params: " + str(params))

    try:
        response = request(method, url, **params)
    except rq_exceptions.Timeout as t:
        if rq_fire_and_forget:
            _LOG.info("Got a timeout error but fire and forget mode is active. Return 200/OK status code to the remote")
            _LOG.debug("Ignored error: " + str(t))
            return ucapi.StatusCodes.OK
        _LOG.error("Got a timeout error from Python requests module:")
        _LOG.error(t)
        return ucapi.StatusCodes.TIMEOUT
    except Exception as e:
        if rq_fire_and_forget:
            _LOG.info("Got a requests error but fire and forget mode is active. Return 200/OK status code to the remote")
            _LOG.debug("Ignored error: " + str(e))
            return ucapi.StatusCodes.OK
        _LOG.error("Got error message from Python requests module:")
        _LOG.error(e)
        return ucapi.StatusCodes.CONFLICT

    if response.status_code == http_codes.ok:
        _LOG.info("Sent http-" + method + " request to: " + url)
        if response.text != "":
            _LOG.info("Server response: " + response.text)
            update_response(method, response.text)
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
                    _LOG.info("Server response: " + response.text)
                    update_response(method, response.text)
                return ucapi.StatusCodes.NOT_FOUND
            return ucapi.StatusCodes.BAD_REQUEST
        return ucapi.StatusCodes.SERVER_ERROR

    if response.raise_for_status() is None:
        _LOG.info("Received informational or redirection http status code: " + str(response.status_code))
        if response.text != "":
            _LOG.info("Server response: " + response)
            update_response(method, response.text)
        return ucapi.StatusCodes.OK



async def tcp_text_cmd(cmd_param: str) -> str:
    """Send a text over TCP command to the passed address and return the status code."""
    address, data = cmd_param.split(",", 1)  # Split only at the 1st comma
    host, port = address.split(":")
    timeout = config.Setup.get("tcp_text_timeout")

    port = int(port)
    data = data.strip().strip('"\'')  # Remove spaces and (double) quotes
    data = tcp_text_process_control_data(data)

    writer = None

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
    finally:
        if writer:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception as e:
                _LOG.error("An error occurred while closing the connection:")
                _LOG.error(e)
        else:
            _LOG.error("The server could not be reached or the connection was rejected")

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
            method = entity_id.replace("http-", "")

            #Use asyncio.gather() to run the function in a separate thread and use asyncio.sleep(0) to prevent blocking the event loop
            cmd_status = await asyncio.gather(asyncio.to_thread(rq_cmd, method, cmd_param), asyncio.sleep(0))
            #Return the return value of rq_cmd which is the first command in asyncio.gather()
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
                await asyncio.gather(asyncio.to_thread(send_magic_packet, *macs, *params), asyncio.sleep(0)) #Unpack macs list with * and params dicts list with **
                #send_magic_packet(*macs, **params) #Unpack macs list with * and params dicts list with **
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
