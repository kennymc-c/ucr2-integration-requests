#!/usr/bin/env python3

"""Module that includes all functions needed for the setup and reconfiguration process"""

import logging

import ucapi

import config
import driver

_LOG = logging.getLogger(__name__)



async def init():
    """Advertises the driver metadata and first setup page to the remote using driver.json"""
    await driver.api.init("driver.json", driver_setup_handler)



async def add_mp_all():
    """Adds a media player entity for each configured command in config.py"""
    for cmd in config.Setup.all_cmds:
        try:
            entity_id = config.Setup.get("id-"+cmd)
            entity_name = config.Setup.get("name-"+cmd)
        except ValueError as v:
            _LOG.error(v)

        if driver.api.available_entities.contains(id):
            _LOG.debug("Entity with id " + entity_id + " is already in storage as available entity")
        else:
            #Only works when add_mp is called outside of driver.py. Otherwise an entity is not available api warning is shown after adding all entities
            await driver.add_mp(entity_id, entity_name)



async def driver_setup_handler(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    """
    Dispatch driver setup requests to corresponding handlers.

    Either start the setup process or handle the provided user input data.

    :param msg: the setup driver request object, either DriverSetupRequest,
                UserDataResponse or UserConfirmationResponse
    :return: the setup action on how to continue
    """
    if isinstance(msg, ucapi.DriverSetupRequest):
        return await handle_driver_setup(msg)
    if isinstance(msg, ucapi.UserDataResponse):
        return await handle_user_data_response(msg)
    elif isinstance(msg, ucapi.AbortDriverSetup):
        _LOG.info("Setup was aborted with code: %s", msg.error)

    _LOG.error("Error during setup")
    config.Setup.set("setup_complete", False)
    return ucapi.SetupError()



async def handle_driver_setup(msg: ucapi.DriverSetupRequest,) -> ucapi.SetupAction:
    """
    Start driver setup.

    Initiated by Remote Two to set up the driver.

    :param msg: value(s) of input fields in the first setup screen.
    :return: the setup action on how to continue
    """

    if msg.reconfigure and config.Setup.get("setup_complete"):
        _LOG.info("Starting reconfiguration")
        config.Setup.set("setup_reconfigure", True)


    if msg.setup_data["advanced_settings"] == "true":
        _LOG.info("Entering advanced setup settings")

        try:
            rq_timeout = config.Setup.get("rq_timeout")
            rq_ssl_verify = config.Setup.get("rq_ssl_verify")
            rq_fire_and_forget = config.Setup.get("rq_fire_and_forget")
        except ValueError as v:
            _LOG.error(v)

        _LOG.debug("Currently stored - rq_timeout: " + str(rq_timeout) + " , rq_ssl_verify: " + str(rq_ssl_verify) + " , rq_fire_and_forget: " + str(rq_fire_and_forget))

        return ucapi.RequestUserInput(
            {
                "en": "Configuration",
                "de": "Konfiguration"
            },
            [
                {
                  "id": "rq_timeout",
                  "label": {
                            "en": "Timeout for HTTP requests (max. 30 seconds):",
                            "de": "Timeout für HTTP-Anfragen (max. 30 Sekunden):"
                            },
                   "field": {"number": {
                                    "value": rq_timeout,
                                    "min": 1,
                                    "max": 30,
                                    "steps": 1,
                                    "decimals": 1,
                                    "unit":
                                        {
                                            "en": "seconds",
                                            "de": "Sekunden"
                                        }
                                        }
                            },
                },
                {
                    "id": "rq_ssl_verify",
                    "label": {
                        "en": "Verify HTTP SSL certificates:",
                        "de": "HTTP SSL-Zertifikate verifizieren:"
                        },
                    "field": {"checkbox": {
                                        "value": rq_ssl_verify
                                        }
                            },
                },
                                {
                    "id": "rq_fire_and_forget",
                    "label": {
                        "en": "Ignore HTTP requests errors (fire and forget):",
                        "de": "Fehler bei HTTP-Anfragen ignorieren (Fire and Forget):"
                        },
                    "field": {"checkbox": {
                                        "value": rq_fire_and_forget
                                        }
                            },
                },
            ],
        )

    if not config.Setup.get("setup_reconfigure"):
        await add_mp_all()
    else:
        _LOG.info("Skip adding available entities during reconfiguration setup")

    _LOG.info("Setup complete")
    config.Setup.set("setup_complete", True)
    return ucapi.SetupComplete()



async def  handle_user_data_response(msg: ucapi.UserDataResponse) -> ucapi.SetupAction:
    """
    Process user data response in a setup process.

    Driver setup callback to provide requested user data during the setup process.

    :param msg: response data from the requested user data
    :return: the setup action on how to continue: SetupComplete if finished.
    """

    rq_timeout = msg.input_values["rq_timeout"]
    rq_ssl_verify = msg.input_values["rq_ssl_verify"]
    rq_fire_and_forget = msg.input_values["rq_fire_and_forget"]

    rq_timeout = int(rq_timeout)
    try:
        config.Setup.set("rq_timeout", rq_timeout)
    except Exception as e:
        _LOG.error(e)
        config.Setup.set("setup_complete", False)
        return ucapi.SetupError()
    _LOG.info("Chosen timeout: " +  str(rq_timeout) + " seconds")

    if rq_ssl_verify == "true": #Boolean in quotes as all values are returned as strings
        try:
            config.Setup.set("rq_ssl_verify", True)
        except Exception as e:
            _LOG.error(e)
            config.Setup.set("setup_complete", False)
            return ucapi.SetupError()
        _LOG.info("HTTP SSL verification activated")
    else:
        try:
            config.Setup.set("rq_ssl_verify", False)
        except Exception as e:
            _LOG.error(e)
            config.Setup.set("setup_complete", False)
            return ucapi.SetupError()
        _LOG.info("HTTP SSL verification deactivated")

    if rq_fire_and_forget == "true": #Boolean in quotes as all values are returned as strings
        try:
            config.Setup.set("rq_fire_and_forget", True)
        except Exception as e:
            _LOG.error(e)
            config.Setup.set("setup_complete", False)
            return ucapi.SetupError()
        _LOG.info("Fire and forget mode activated. Always return OK to the remote")
    else:
        try:
            config.Setup.set("rq_fire_and_forget", False)
        except Exception as e:
            _LOG.error(e)
            config.Setup.set("setup_complete", False)
            return ucapi.SetupError()

    if not config.Setup.get("setup_reconfigure"):
        for cmd in config.Setup.all_cmds:
            entity_id = config.Setup.get("id-"+cmd)
            entity_name = config.Setup.get("name-"+cmd)
            await driver.add_mp(entity_id, entity_name)
    else:
        _LOG.info("Skip adding available entities during reconfiguration")

    _LOG.info("Setup complete")
    config.Setup.set("setup_complete", True)
    return ucapi.SetupComplete()
