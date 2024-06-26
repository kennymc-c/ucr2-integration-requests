#!/usr/bin/env python3

import logging
import json

import ucapi

import config
import driver

_LOG = logging.getLogger(__name__)



async def init():
    await driver.api.init("setup.json", driver_setup_handler)



async def add_mp_all():
    for cmd in config.setup.all_cmds:
        id = config.setup.get("id-"+cmd)
        name = config.setup.get("name-"+cmd)

        if driver.api.available_entities.contains(id):
            _LOG.debug("Entity with id " + id + " is already in storage as available entity")
        else:
            #Only works when add_mp is called outside of driver.py. Otherwise an entity is not available api warning is shown after adding all entities
            await driver.add_mp(id, name)
    


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
    config.setup.set("setup_complete", False)
    return ucapi.SetupError()



async def handle_driver_setup(msg: ucapi.DriverSetupRequest,) -> ucapi.SetupAction:
    """
    Start driver setup.

    Initiated by Remote Two to set up the driver.

    :param msg: value(s) of input fields in the first setup screen.
    :return: the setup action on how to continue
    """

    if msg.reconfigure and config.setup.get("setup_complete"):
        _LOG.info("Starting reconfiguration")
        config.setup.set("setup_reconfigure", True)


    if msg.setup_data["advanced_settings"] == "true":
        _LOG.info("Entering advanced setup settings")

        rq_timeout = config.setup.get("rq_timeout")
        rq_ssl_verify = config.setup.get("rq_ssl_verify")

        _LOG.debug("Currently stored - rq_timeout: " + str(rq_timeout) + " , rq_ssl_verify: " + str(rq_ssl_verify))

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
            ],
        )
    else:
        if not config.setup.get("setup_reconfigure"): 
            await add_mp_all()
        else:
            _LOG.info("Skip adding available entities during reconfiguration setup")

        _LOG.info("Setup complete")
        config.setup.set("setup_complete", True)
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

    rq_timeout = int(rq_timeout)
    try:
        config.setup.set("rq_timeout", rq_timeout)
    except Exception as e:
        _LOG.error(e)
        config.setup.set("setup_complete", False)
        return ucapi.SetupError()
    _LOG.info("Chosen timeout: " +  str(rq_timeout))
            
    if rq_ssl_verify == "true": #Boolean in quotes as all values are returned as strings
        try:
            config.setup.set("rq_ssl_verify", True)
        except Exception as e:
            _LOG.error(e)
            config.setup.set("setup_complete", False)
            return ucapi.SetupError()
        _LOG.info("HTTP SSL verification activated")
    else:
        try:
            config.setup.set("rq_ssl_verify", False)
        except Exception as e:
            _LOG.error(e)
            config.setup.set("setup_complete", False)
            return ucapi.SetupError()
        _LOG.info("HTTP SSL verification deactivated")

    if not config.setup.get("setup_reconfigure"): 
        for cmd in config.setup.all_cmds:
            id = config.setup.get("id-"+cmd)
            name = config.setup.get("name-"+cmd)
            await driver.add_mp(id, name)
    else:
        _LOG.info("Skip adding available entities during reconfiguration")

    _LOG.info("Setup complete")
    config.setup.set("setup_complete", True)
    return ucapi.SetupComplete()