#!/usr/bin/env python3

"""Module that sends http request, wol or text over tcp command"""

import asyncio
import logging
import ast
import shlex
import socket
import string
from typing import Any

from re import sub, search, fullmatch, IGNORECASE
from ipaddress import ip_address, IPv4Address, IPv6Address, AddressValueError
import urllib3 #Needed to optionally deactivate requests ssl verify warning message

import ucapi
from requests import request
from requests import codes as http_codes
from requests import exceptions as rq_exceptions
from wakeonlan import wake
from getmac import get_mac_address

import config
import sensor
import i18n

_LOG = logging.getLogger(__name__)



def get_mac(param: str):
    """Accepts mac, ip addresses or host names. Get the mac address or checks if the mac address is valid.\
    If the mac address can not be discovered a value error is raised"""

    try:
        ip_address(param)
        param_type = "ip"
        _LOG.debug("\""+param+"\" is an ip address. Using getmac to discover mac address")
    except ValueError:
        mac_regex = (
            r"([0-9A-F]{2}[:]){5}[0-9A-F]{2}"
            r"|([0-9A-F]{2}[-]){5}[0-9A-F]{2}"
            r"|([0-9A-F]{2}[.]){5}[0-9A-F]{2}"
            r"|[0-9A-F]{12}"
        )
        is_valid_mac = fullmatch(mac_regex, param, flags=IGNORECASE)
        if is_valid_mac:
            param_type = "mac"
            _LOG.debug("\""+param+"\" is a mac address")
        else:
            param_type = "hostname"
            _LOG.debug("\""+param+"\" could be a hostname. Using getmac to discover the mac address")

    if param_type == "ip":
        if config.Setup.get("bundle_mode"):
            raise OSError("Using an IP address for wake-on-lan is not supported when running the integration on the remote due to sandbox limitations. \
Please use the mac address instead")
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


def normalize_quotes(s: str) -> str:
    """Normalize various unicode quote characters to straight ASCII quotes.

    This handles common curly/smart quotes and fullwidth variants so the
    shlex lexer which expects '"' and "'" works reliably when users paste
    text from rich-text sources.
    """
    if not isinstance(s, str):
        return s
    trans = {
        0x201C: 0x22,  # LEFT DOUBLE QUOTATION MARK “ -> "
        0x201D: 0x22,  # RIGHT DOUBLE QUOTATION MARK ” -> "
        0x201E: 0x22,  # DOUBLE LOW-9 QUOTATION MARK „ -> "
        0x201F: 0x22,  # DOUBLE HIGH-REVERSED-9 QUOTATION MARK ‟ -> "
        0xFF02: 0x22,  # FULLWIDTH QUOTATION MARK -> "
        0x2018: 0x27,  # LEFT SINGLE QUOTATION MARK ‘ -> '
        0x2019: 0x27,  # RIGHT SINGLE QUOTATION MARK ’ -> '
        0x201A: 0x27,  # SINGLE LOW-9 QUOTATION MARK ‚ -> '
        0x201B: 0x27,  # SINGLE HIGH-REVERSED-9 QUOTATION MARK ‛ -> '
        0xFF07: 0x27,  # FULLWIDTH APOSTROPHE -> '
    }
    result = s.translate(trans)
    if result != s:
        try:
            _LOG.warning("Replaced smart/curly quotes in source parameter with straight ASCII quotes. \
Please check your input and only use straight quotes")
        except Exception:
            # Logging must not break parsing; swallow any logging errors
            pass
    return result


def update_response(response: str, cmd: str):
    """Parse http request or tcp text response with configured regular expression and update the corresponding sensor entity"""

    if cmd == "http-request":
        regex = config.Setup.get("rq_response_regex")
        nomatch_option = config.Setup.get("rq_response_nomatch_option")
    elif cmd == "tcp-text":
        regex = config.Setup.get("tcp_text_response_regex")
        nomatch_option = config.Setup.get("tcp_text_response_nomatch_option")
    else:
        raise Exception("Invalid command for response parsing: " + cmd)

    if regex == "":
        parsed_response = " ".join(response.split()).replace("\\\"", "\"") #Remove all line breaks and join them with spaces
        _LOG.debug("No regular expression set for the " + cmd + " response sensor. The complete response will be used")
    else:
        match = search(regex, response)
        if match:
            parsed_response = match.group(1)
            _LOG.debug("Parsed response from configured regex: " + parsed_response)
        else:
            _LOG.warning("No matches found in the " + cmd + " response for the regular expression " + regex)

            if nomatch_option == "full":
                _LOG.debug("The full response will be used instead")
                parsed_response = response
            elif nomatch_option == "error":
                _LOG.debug("An error message will be used instead")
                parsed_response = i18n.Handler.localize(i18n.Messages.NO_MATCH)
            elif nomatch_option == "empty":
                _LOG.debug("An empty response will be used instead")
                parsed_response = ""

    try:
        if cmd == "http-request":
            sensor.update_rq_sensor(config.Setup.get("id-rq-sensor"), parsed_response)
        if cmd == "tcp-text":
            sensor.update_tcp_text_sensor(config.Setup.get("id-tcp-text-sensor"), parsed_response)
    except Exception as e:
        _LOG.error(e)



def http_request(method: str, cmd_param: str=None | dict) -> int:
    """Send a http requests command to the passed url with the passed data and return the status code"""

    rq_ssl_verify = config.Setup.get("rq_ssl_verify")
    rq_fire_and_forget = config.Setup.get("rq_fire_and_forget")
    rq_timeout = config.Setup.get("rq_timeout")
    rq_user_agent = config.Setup.get("rq_user_agent")

    params = {}

    if isinstance(cmd_param, dict): #Check if cmd_param is already a dict when coming from a custom entity config with multiple parameters
        params = dict(cmd_param)
        url = params.pop("url", None)
        if not url:
            _LOG.error("No url parameter found")
            return ucapi.StatusCodes.BAD_REQUEST
    else:
        # Normalize unicode quotes so shlex can handle pasted smart quotes
        cmd_param = normalize_quotes(cmd_param)
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

    _LOG.debug("Sending http request:")
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
            update_response(response.text, "http-request")
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
                    update_response(response.text, "http-request")
                return ucapi.StatusCodes.NOT_FOUND
            return ucapi.StatusCodes.BAD_REQUEST
        return ucapi.StatusCodes.SERVER_ERROR

    if response.raise_for_status() is None:
        _LOG.info("Received informational or redirection http status code: " + str(response.status_code))
        if response.text != "":
            _LOG.info("Server response: " + response)
            update_response(response.text, "http-request")
        return ucapi.StatusCodes.OK



def is_printable(s):
    """Check if all characters in the tcp-text response string are printable"""
    return all(c in string.printable for c in s)



async def tcp_text(cmd_param: str, entity_config: dict[str, Any] = None) -> str:
    """Send a text over TCP command to the passed address and return the status code."""

    timeout = config.Setup.get("tcp_text_timeout")
    response_wait = config.Setup.get("tcp_text_response_wait")
    terminator = config.Setup.get("tcp_text_terminator")
    response_ok = ""
    response_error = ""

    if isinstance(cmd_param, dict): # Check if cmd_param is already a dict when coming from a custom entity config
        address = cmd_param["address"]
        data = cmd_param["text"]
        timeout = cmd_param.get("timeout", config.Setup.get("tcp_text_timeout"))
        response_ok = cmd_param.get("response_ok")
        response_error = cmd_param.get("response_error")
        # Add global tcp_response_ok and tcp_response_error from entity config if not already in cmd_param
        if not response_ok and entity_config and "tcp_response_ok" in entity_config:
            response_ok = entity_config["tcp_response_ok"]
        if not response_error and entity_config and "tcp_response_error" in entity_config:
            response_error = entity_config["tcp_response_error"]
    else:
        params = {}
        address = None
        data = ""

        # Normalize unicode quotes so shlex can handle pasted smart quotes
        cmd_param = normalize_quotes(cmd_param)
        lexer = shlex.shlex(cmd_param, posix=True)
        lexer.whitespace_split = True
        lexer.whitespace = ","
        lexer.quotes = '"'
        tokens = [token.strip() for token in lexer if token.strip()]

        for token in tokens:
            if "=" in token:
                key, value = token.split("=", 1)
                key = key.strip()
                if key in {"address", "text", "response_ok", "response_error", "timeout", "response_wait"}:
                    params[key] = value.strip()
                    continue
            if address is None:
                address = token
            elif data == "":
                data = token
            else:
                _LOG.warning("Ignored extra tcp_text parameter: %s", token)

        address = params.get("address", address)
        data = params.get("text", data)
        response_ok = params.get("response_ok", "")
        response_error = params.get("response_error", "")

        if "timeout" in params:
            try:
                timeout = int(params["timeout"])
            except ValueError:
                _LOG.error("Timeout parameter is not a valid integer: " + params["timeout"])
        if "response_wait" in params:
            response_wait_str = params["response_wait"].lower()
            if response_wait_str == "true":
                response_wait = True
            elif response_wait_str == "false":
                response_wait = False
            else:
                _LOG.error("response_wait parameter is not a valid boolean: " + params["response_wait"])

    if not address:
        _LOG.error("No address parameter found for tcp_text command")
        return ucapi.StatusCodes.BAD_REQUEST

    host, port = address.split(":")
    port = int(port)
    data = data.strip().strip('"\'')  # Remove spaces and (double) quotes

    if timeout != config.Setup.get("tcp_text_timeout"):
        _LOG.debug("Command specific timeout of " +  str(timeout) + " seconds defined")

    _LOG.debug(f"address: {address}, text: {repr(data)}, timeout: {timeout}, response_wait: {response_wait}, \
terminator: {repr(terminator)}")

    writer = None
    try:
        reader, writer = await asyncio.open_connection(host, port)
        if data.startswith("raw="):
            raw_data = data[4:].replace(" ", "").replace("0x", "")
            try:
                writer.write(bytes.fromhex(raw_data))
            except ValueError:
                _LOG.error("Invalid hex format in raw data: " + raw_data)
                return ucapi.StatusCodes.BAD_REQUEST
        else:
            data = tcp_text_process_control_data(data)
            if terminator != "None":
                _LOG.debug("Append command terminator " + repr(terminator) + " to the sent data")
                data = data + terminator
            writer.write((data).encode("utf-8"))
        await writer.drain()

        received_message = ""
        binary_message = ""
        if response_wait:
            try:
                received_data = await asyncio.wait_for(reader.read(1024), timeout)
                try:
                    received_message = received_data.decode("utf-8")
                except UnicodeDecodeError:
                    binary_message = received_data.hex(" ")
            except asyncio.TimeoutError:
                _LOG.warning("Timeout while waiting for a response message from the server")
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

    if received_message != "" or binary_message != "":
        if is_printable(received_message) and received_message.strip():
            processed_message = received_message.replace("\r", "\n")
            _LOG.info("Received text response: " + processed_message)
            update_response(processed_message, "tcp-text")
        else:
            _LOG.info("Received binary response: " + binary_message)
            update_response(binary_message, "tcp-text")

    if response_ok or response_error:

        ok_match = False
        error_match = False

        # Determine which text to use for matching (prefer processed text if available)
        match_text = ""
        if "processed_message" in locals() and processed_message:
            match_text = processed_message
        elif received_message:
            match_text = received_message
        else:
            match_text = binary_message

        if response_ok:
            _LOG.debug("Expected ok response defined: " + repr(response_ok))
            try:
                ok_match = search(flags=IGNORECASE, pattern=response_ok, string=match_text)
            except Exception:
                _LOG.error("Invalid regular expression for response_ok: " + repr(response_ok))
                return ucapi.StatusCodes.BAD_REQUEST
        if response_error:
            _LOG.debug("Expected error response defined: " + repr(response_error))
            try:
                error_match = search(flags=IGNORECASE, pattern=response_error, string=match_text)
            except Exception:
                _LOG.error("Invalid regular expression for response_error: " + repr(response_error))
                return ucapi.StatusCodes.BAD_REQUEST

        if ok_match and error_match:
            _LOG.warning("Received response matching both the expected ok and error response. Please refine your regular expressions")
            _LOG.info("Will return OK status code when both regexes match to avoid false positive error status codes")
            return ucapi.StatusCodes.OK
        if ok_match:
            _LOG.info("Received response matching the expected ok response: " + match_text)
            return ucapi.StatusCodes.OK
        if error_match:
            _LOG.info("Received response matching the expected error response: " + match_text)
            return ucapi.StatusCodes.SERVER_ERROR
        _LOG.warning("Did not receive a response matching either the ok or error response. Please check your regular expressions and the received response: " + match_text)
        return ucapi.StatusCodes.BAD_REQUEST

    return ucapi.StatusCodes.OK



async def wol(cmd_param: str | dict)  -> ucapi.StatusCodes:
    """Send a wake on lan command to the passed mac address or ip address and return the status code"""
    addresses = []

    if isinstance(cmd_param, dict): # Check if cmd_param is already a dict when coming from a custom entity config with multiple parameters or addresses
        addresses = cmd_param["address"] # Separate addresses from other command parameters
        del cmd_param["address"]
        params = cmd_param
    else:
        params = {}
        value = ""
        if "," in cmd_param:
            _LOG.info("Passed parameter contains more than one address and/or wol parameters")
            values = cmd_param.split(",")

            for value in values:
                value = value.strip()
                if "=" in value:
                    name, param = value.split("=", 1)
                    if name == "port":
                        try:
                            param = int(param)
                        except ValueError:
                            _LOG.error(f"Invalid \"port\" parameter: \"{param}\". Value must be an integer")
                            return ucapi.StatusCodes.BAD_REQUEST
                    if name == "family":
                        try:
                            param = int(param)
                        except ValueError:
                            _LOG.error(f"Invalid \"family\" parameter: \"{param}\". Value must be an integer")
                            return ucapi.StatusCodes.BAD_REQUEST
                        if param not in (2, 10, 4, 6):
                            _LOG.error(f"Invalid \"family\" parameter: \"{param}\". Value must be either 2, 10, 4 or 6")
                            return ucapi.StatusCodes.BAD_REQUEST
                        if param == 4:
                            param = socket.AF_INET
                            _LOG.debug("Using socket.AF_INET for sending the magic packet")
                        elif param == 6:
                            param = socket.AF_INET6
                            _LOG.debug("Using socket.AF_INET6 for sending the magic packet")
                        elif param == 2:
                            param = socket.AF_INET
                            _LOG.debug("Using socket.AF_INET for sending the magic packet")
                        elif param == 10:
                            param = socket.AF_INET6
                            _LOG.debug("Using socket.AF_INET6 for sending the magic packet")
                    params[name] = param
                else:
                    addresses.append(value)
        else:
            addresses.append(cmd_param)

    macs = []
    password = None
    if addresses:
        for address in addresses:
            if "/" in address:
                address, password = address.split("/")
                _LOG.info("Using SecureOn password for address: " + address)
            try:
                mac = get_mac(address)
            except ValueError as v:
                _LOG.error(v)
                _LOG.error(f"Used WoL parameter \"{value}\" is not a valid hostname, mac or ip address")
                return ucapi.StatusCodes.BAD_REQUEST
            except OSError as o:
                _LOG.error(o)
                return ucapi.StatusCodes.CONFLICT
            except Exception as e:
                _LOG.error("Got an error while retrieving the mac address")
                _LOG.error(e)
                return ucapi.StatusCodes.BAD_REQUEST
            if password:
                mac = f"{mac}/{password}"
            macs.append(mac)

    try:
        # Unpack macs list with * and params dict with **
        await asyncio.gather(asyncio.to_thread(wake, *macs, **params), asyncio.sleep(0))
    except ValueError as v:
        _LOG.error(v)
        return ucapi.StatusCodes.BAD_REQUEST
    except Exception as e:
        family = params.get("family")
        if family in (socket.AF_INET6, 10, 6) and "host" not in params:
            _LOG.warning("The requested IPv6 WoL family is not supported by the current environment. Retrying with the default IPv4 settings")
            try:
                params_without_family = dict(params)
                params_without_family.pop("family", None)
                await asyncio.gather(asyncio.to_thread(wake, *macs, **params_without_family), asyncio.sleep(0))
            except Exception as fallback_error:
                _LOG.error("Got an error message from Python wakeonlan module:")
                _LOG.error(fallback_error)
                return ucapi.StatusCodes.BAD_REQUEST
        else:
            _LOG.error("Got an error message from Python wakeonlan module:")
            _LOG.error(e)
            return ucapi.StatusCodes.BAD_REQUEST

    if macs:
        _LOG.info("Sent wake on lan magic packet to mac address(es): " + str(macs) + " with parameter(s): " + str(params))
    else:
        _LOG.info("Sent wake on lan magic packet to mac address(es)): " + str(macs))
    return ucapi.StatusCodes.OK
