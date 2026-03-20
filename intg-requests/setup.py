#!/usr/bin/env python3

"""Module that includes all functions needed for the setup and reconfiguration process"""

import logging

import ucapi

import config
import driver
import sensor

_LOG = logging.getLogger(__name__)



async def init():
    """Advertises the driver metadata and first setup page to the remote using driver.json"""
    await driver.api.init("driver.json", driver_setup_handler)



async def add_all_entities():
    """Adds a media player entity for each configured command in config.py and the http response sensor entity"""

    if config.Setup.get("custom_entities_set"):
        _LOG.debug("Get custom entities configuration as Python dict from runtime storage")
        custom_entities = config.Setup.get("custom_entities", python_dict=True)
        await driver.add_custom_entities(custom_entities)

    for cmd in config.Setup.all_cmds:
        try:
            entity_id = config.Setup.get("id-"+cmd)
            entity_name = config.Setup.get("name-"+cmd)
        except ValueError as v:
            _LOG.error(v)

        if driver.api.available_entities.contains(entity_id) or driver.api.configured_entities.contains(entity_id):
            _LOG.debug("Entity with id " + entity_id + " is already in storage as available or configured entity")
        else:
            #Only works when add_mp is called outside of driver.py. Otherwise an entity is not available api warning is shown after adding all entities
            await driver.add_mp(entity_id, entity_name)

    if driver.api.available_entities.contains(config.Setup.get("id-rq-sensor")) or driver.api.configured_entities.contains(config.Setup.get("id-rq-sensor")):
        _LOG.debug("Entity with id " + config.Setup.get("id-rq-sensor") + " is already in storage as available or configured entity")
    else:
        await sensor.add_rq_sensor(config.Setup.get("id-rq-sensor"), config.Setup.get("name-rq-sensor"))

    if driver.api.available_entities.contains(config.Setup.get("id-tcp-text-sensor")) or driver.api.configured_entities.contains(config.Setup.get("id-tcp-text-sensor")):
        _LOG.debug("Entity with id " + config.Setup.get("id-tcp-text-sensor") + " is already in storage as available or configured entity")
    else:
        await sensor.add_tcp_text_sensor(config.Setup.get("id-tcp-text-sensor"), config.Setup.get("name-tcp-text-sensor"))



async def driver_setup_handler(msg: ucapi.SetupDriver) -> ucapi.SetupAction:
    """
    Dispatch driver setup requests to corresponding handlers.

    Either start the setup process or handle the provided user input data.

    :param msg: the setup driver request object, either DriverSetupRequest,
                UserDataResponse or UserConfirmationResponse
    :return: the setup action on how to continue
    """

    #setup_action checks have to be done for both DriverSetupRequest and UserDataResponse message classes depending from which setup page the user is coming from
    if isinstance(msg, ucapi.DriverSetupRequest):

        if msg.reconfigure and config.Setup.get("setup_complete"):
            _LOG.info("Starting reconfiguration")
            config.Setup.set("setup_reconfigure", True)

        if msg.setup_data["setup_action"] == "advanced":
            config.Setup.set("setup_step", "advanced")
            return await show_advanced_setup(msg)

        if msg.setup_data["setup_action"] == "custom":
            config.Setup.set("setup_step", "custom")
            return await show_custom_entity_config(msg)

        if msg.setup_data["setup_action"] == "finish":
            return await finish_setup()

    if isinstance(msg, ucapi.UserDataResponse):

        if config.Setup.get("setup_step") == "handle_advanced":
            return await handle_response_advanced(msg)

        if config.Setup.get("setup_step") == "handle_custom":
            return await handle_response_custom(msg)

        if msg.input_values["setup_action"] == "advanced":
            config.Setup.set("setup_step", "advanced")
            return await show_advanced_setup(msg)

        if msg.input_values["setup_action"] == "custom":
            config.Setup.set("setup_step", "custom")
            return await show_custom_entity_config(msg)

        if msg.input_values["setup_action"] == "finish":
            return await finish_setup()

    if isinstance(msg, ucapi.AbortDriverSetup):
        _LOG.info("Setup was aborted with code: %s", msg.error)

    _LOG.error("Error during setup")
    config.Setup.set("setup_complete", False)
    return ucapi.SetupError()



async def show_setup_action(msg: ucapi.DriverSetupRequest) -> ucapi.RequestUserInput:
    """Show the setup action screen to the user"""
    setup_action_dropdown_items = config.Setup.get("setup_action_dropdown_items")
    config.Setup.set("setup_step", "action")

    return ucapi.RequestUserInput(
        {
            "en": "Setup Actions",
            "de": "Einrichtungsoptionen"
        },
        [
        {
            "id": "setup_action",
            "label": {
                "en": "Choose a setup action",
                "de": "Wähle eine Einrichtungsoption aus"
            },
            "field": {"dropdown": {
                                    "value": setup_action_dropdown_items[0]["id"],
                                    "items": setup_action_dropdown_items
                                    }
                                },
        }
        ]
    )



async def show_advanced_setup(msg) -> ucapi.RequestUserInput:
    """
    Start driver setup.

    Initiated by the Remote to set up the driver.

    :param msg: value(s) of input fields in the first setup screen.
    :return: the setup action on how to continue
    """

    _LOG.info("Entering advanced setup settings")

    try:
        tcp_text_timeout = config.Setup.get("tcp_text_timeout")
        tcp_text_response_wait = config.Setup.get("tcp_text_response_wait")
        tcp_text_terminator = config.Setup.get("tcp_text_terminator")
        tcp_text_terminator_dropdown_items = config.Setup.get("tcp_text_terminator_dropdown_items")
        tcp_text_response_regex = config.Setup.get("tcp_text_response_regex")
        tcp_text_response_nomatch_option = config.Setup.get("tcp_text_response_nomatch_option")
        regex_nomatch_dropdown_items = config.Setup.get("regex_nomatch_dropdown_items")
        rq_timeout = config.Setup.get("rq_timeout")
        rq_ssl_verify = config.Setup.get("rq_ssl_verify")
        rq_fire_and_forget = config.Setup.get("rq_fire_and_forget")
        rq_user_agent = config.Setup.get("rq_user_agent")
        rq_response_regex = config.Setup.get("rq_response_regex")
        rq_response_nomatch_option = config.Setup.get("rq_response_nomatch_option")
    except ValueError as v:
        _LOG.error(v)

    #Get the index of the currently stored value from the corresponding dropdown items list to set it as the default value for the dropdown
    index_tcp_text_terminator = next((i for i, d in enumerate(tcp_text_terminator_dropdown_items) if d.get("id") == tcp_text_terminator), 0)
    index_tcp_text_response_nomatch_option = next((i for i, d in enumerate(regex_nomatch_dropdown_items) if d.get("id") == tcp_text_response_nomatch_option), 0)
    index_rq_response_nomatch_option = next((i for i, d in enumerate(regex_nomatch_dropdown_items) if d.get("id") == rq_response_nomatch_option), 0)

    _LOG.debug(f"Currently stored - tcp_text_timeout: {str(tcp_text_timeout)}, tcp_text_response_wait: {str(tcp_text_response_wait)}, \
tcp_text_terminator: {repr(tcp_text_terminator)}, tcp_text_response_regex: {str(tcp_text_response_regex)}, tcp_text_response_nomatch_option: \
{str(tcp_text_response_nomatch_option)}, rq_timeout: {str(rq_timeout)}, rq_ssl_verify: {str(rq_ssl_verify)}, rq_fire_and_forget: {str(rq_fire_and_forget)}, \
rq_user_agent: {str(rq_user_agent)}, rq_response_regex: {str(rq_response_regex)}, \
rq_response_nomatch_option: {str(rq_response_nomatch_option)}")

    config.Setup.set("setup_step", "handle_advanced")

    return ucapi.RequestUserInput(
        {
            "en": "Advanced Configuration",
            "de": "Erweiterte Konfiguration"
        },
        [
            {
                "id": "tcp-text-settings",
                "label": {"en": "Text over TCP:", "de": "Text über TCP:"},
                "field": { "label": { "value": {} }}
            },
            {
                "id": "tcp_text_timeout",
                "label": {
                        "en": "Timeout for Text over TCP (max. 30 seconds):",
                        "de": "Timeout für Text über TCP (max. 30 Sekunden):"
                        },
                "field": {"number": {
                                "value": tcp_text_timeout,
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
                "id": "tcp_text_response_wait",
                "label": {
                    "en": "Wait for a text over tcp response message:",
                    "de": "Auf eine Text über TCP Antwort warten:"
                    },
                "field": {"checkbox": {
                                    "value": tcp_text_response_wait
                                    }
                        },
            },
            {
                "id": "tcp_text_terminator",
                "label": {
                    "en": "Automatically add a command terminator character at the end of each text over TCP command:",
                    "de": "Automatisch ein Befehlsabschlusszeichen am Ende jedes Text über TCP-Befehls hinzufügen:"
                    },
                "field": {"dropdown": {
                                    "value": tcp_text_terminator_dropdown_items[index_tcp_text_terminator]["id"],
                                    "items": tcp_text_terminator_dropdown_items
                                    }
                        },
            },
            {
                "id": "tcp_text_response_regex",
                "label": {
                    "en": "Regular expression for parsing the text over TCP sensor response:",
                    "de": "Regulärer Ausdruck zum Parsen der Text über TCP-Sensorantwort:"
                    },
                "field": {"text": {
                                    "value": tcp_text_response_regex
                                    }
                        },
            },
            {
                "id": "tcp_text_response_nomatch_option",
                "label": {
                    "en": "Response if no match for the regular expression has been found:",
                    "de": "Antwort, falls keine Übereinstimmung mit dem regulären Ausdruck gefunden wurde:"
                    },
                "field": {"dropdown": {
                                    "value": regex_nomatch_dropdown_items[index_tcp_text_response_nomatch_option]["id"],
                                    "items": regex_nomatch_dropdown_items
                                    }
                        },
            },
            {
                "id": "http-requests-settings",
                "label": {"en": "Http requests:", "de": "HTTP-Anfragen:"},
                "field": { "label": { "value": {} }}
            },
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
                "id": "rq_user_agent",
                "label": {
                        "en": "HTTP requests user agent:",
                        "de": "HTTP-Anfragen User Agent:"
                        },
                "field": {"text": {
                                "value": rq_user_agent
                                    }
                        }
            },
            {
                "id": "rq_response_regex",
                "label": {
                    "en": "Regular expression for parsing the HTTP request sensor response:",
                    "de": "Regulärer Ausdruck zum Parsen der HTTP-Anfrage-Sensorantwort:"
                    },
                "field": {"text": {
                                    "value": rq_response_regex
                                    }
                        },
            },
            {
                "id": "rq_response_nomatch_option",
                "label": {
                    "en": "Response if no match for the regular expression has been found:",
                    "de": "Antwort, falls keine Übereinstimmung mit dem regulären Ausdruck gefunden wurde:"
                    },
                "field": {"dropdown": {
                                    "value": regex_nomatch_dropdown_items[index_rq_response_nomatch_option]["id"],
                                    "items": regex_nomatch_dropdown_items
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



async def handle_response_advanced(msg: ucapi.UserDataResponse) -> ucapi.RequestUserInput:
    """
    Process user data response in a setup process.

    Driver setup callback to provide requested user data during the setup process.

    :param msg: response data from the requested user data
    :return: the setup action on how to continue: SetupComplete if finished.
    """

    tcp_text_timeout = msg.input_values["tcp_text_timeout"]
    tcp_text_response_wait = msg.input_values["tcp_text_response_wait"]
    tcp_text_terminator = msg.input_values["tcp_text_terminator"]
    tcp_text_response_regex = msg.input_values["tcp_text_response_regex"]
    tcp_text_response_nomatch_option = msg.input_values["tcp_text_response_nomatch_option"]
    rq_timeout = msg.input_values["rq_timeout"]
    rq_ssl_verify = msg.input_values["rq_ssl_verify"]
    rq_fire_and_forget = msg.input_values["rq_fire_and_forget"]
    rq_user_agent = msg.input_values["rq_user_agent"]
    rq_response_regex = msg.input_values["rq_response_regex"]
    rq_response_nomatch_option = msg.input_values["rq_response_nomatch_option"]

    rq_timeout = int(rq_timeout)
    tcp_text_timeout = int(tcp_text_timeout)

    try:
        config.Setup.set("tcp_text_timeout", tcp_text_timeout)
    except Exception as e:
        _LOG.error(e)
        config.Setup.set("setup_complete", False)
        return ucapi.SetupError()
    _LOG.info("Text over tcp timeout: " +  str(tcp_text_timeout) + " seconds")

    if tcp_text_response_wait == "true": #Boolean as string as all values are returned as strings
        try:
            config.Setup.set("tcp_text_response_wait", True)
        except Exception as e:
            _LOG.error(e)
            config.Setup.set("setup_complete", False)
            return ucapi.SetupError()
        _LOG.info("Wait for text over tcp response: " +  str(tcp_text_response_wait))
    else:
        try:
            config.Setup.set("tcp_text_response_wait", False)
        except Exception as e:
            _LOG.error(e)
            config.Setup.set("setup_complete", False)
            return ucapi.SetupError()
        _LOG.info("Do not wait for text over tcp response: " +  str(tcp_text_response_wait))

    try:
        config.Setup.set("tcp_text_terminator", tcp_text_terminator)
    except Exception as e:
        _LOG.error(e)
        config.Setup.set("setup_complete", False)
        return ucapi.SetupError()
    _LOG.info("Text over tcp terminator: " +  str(tcp_text_terminator))

    try:
        config.Setup.set("tcp_text_response_regex", tcp_text_response_regex)
    except Exception as e:
        _LOG.error(e)
        config.Setup.set("setup_complete", False)
        return ucapi.SetupError()
    _LOG.info("Text over TCP response regular expression: \"" +  str(tcp_text_response_regex) + "\"")

    try:
        config.Setup.set("tcp_text_response_nomatch_option", tcp_text_response_nomatch_option)
    except Exception as e:
        _LOG.error(e)
        config.Setup.set("setup_complete", False)
        return ucapi.SetupError()
    _LOG.info("Text over TCP response option: \"" +  str(tcp_text_response_nomatch_option) + "\"")

    try:
        config.Setup.set("rq_timeout", rq_timeout)
    except Exception as e:
        _LOG.error(e)
        config.Setup.set("setup_complete", False)
        return ucapi.SetupError()
    _LOG.info("Http requests timeout: " +  str(rq_timeout) + " seconds")

    try:
        config.Setup.set("rq_user_agent", rq_user_agent)
    except Exception as e:
        _LOG.error(e)
        config.Setup.set("setup_complete", False)
        return ucapi.SetupError()
    _LOG.info("Http requests user agent: \"" +  str(rq_user_agent) + "\"")

    try:
        config.Setup.set("rq_response_regex", rq_response_regex)
    except Exception as e:
        _LOG.error(e)
        config.Setup.set("setup_complete", False)
        return ucapi.SetupError()
    _LOG.info("Http request response regular expression: \"" +  str(rq_response_regex) + "\"")

    try:
        config.Setup.set("rq_response_nomatch_option", rq_response_nomatch_option)
    except Exception as e:
        _LOG.error(e)
        config.Setup.set("setup_complete", False)
        return ucapi.SetupError()
    _LOG.info("Http request response option: \"" +  str(rq_response_nomatch_option) + "\"")

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
        _LOG.info("Fire and forget mode deactivated. Return the actual status code")

    return await show_setup_action(msg)



async def show_custom_entity_config(msg: ucapi.UserDataResponse) -> ucapi.RequestUserInput:
    """Show the custom entity configuration screen to the user"""

    custom_entities = config.Setup.get("custom_entities")
    custom_entities_title_case_select_options = config.Setup.get("custom_entities_title_case_select_options")
    config.Setup.set("setup_step", "handle_custom")

    #BUG \n\n causing a formatting error (wrong font and alignment) in label value field
    #TODO Create issue on bug & feature tracker with examples from the python example configuration
    return ucapi.RequestUserInput(
        {
            "en": "Custom Entity Configuration",
            "de": "Eigene Entitäten-Konfiguration"
        },
        [
            {
                "id": "custom-entities-settings",
                "label": {"en": "Custom entities configuration", "de": "Eigene Entitäten-Konfiguration"},
                "field": { "label":
                            { "value": {
                                        "en": "Create your own remote entities with pre-defined commands. More details can be found in the readme file.\
                                        \n\n⚠️ Important: If you remove an entity from the configuration you need to manually remove it from the list of available entities \
                                        after completing this setup. Removed entities will otherwise be shown as unavailable after a restart of the remote/integration.",
                                        "de": "Erstelle deine eigenen Remote-Entitäten mit vor-definierten Befehlen. Mehr Details findest du in der Readme-Datei.\
                                        \n\n⚠️ Wichtig: Wenn du eine Entität aus der Konfiguration entfernst, musst du diese Entität, nachdem du diese Einrichtung abgeschlossen hast, \
                                        aus der Liste der verfügbaren Entitäten entfernen. Entfernte Entitäten werden sonst nach einem Neustart der Fernbedienung/Integration \
                                        als nicht verfügbar angezeigt."
                                        }
                            }
                        },
            },
            {
                "id": "custom_entities",
                "label": {
                        "en": "Replace this configuration with your own",
                        "de": "Ersetzte diese Konfiguration mit deiner Eigenen"
                        },
                "field": {"textarea": {
                                "value": custom_entities,
                                    }
                        }
            },
                        {
                "id": "custom_entities_title_case_select_options",
                "label": {
                    "en": "Convert all select entity option to a title cased version and replace underscores with spaces \
                        (RECEIVER_INPUT_1 -> Receiver Input 1):",
                    "de": "In allen Optionen von Auswahl-Entitäten die Anfangsbuchstaben aller Wörter groß schreiben \
                        und Unterstriche durch Leerzeichen ersetzten (RECEIVER_INPUT_1 -> Receiver Input 1):"
                    },
                "field": {"checkbox": {
                                    "value": custom_entities_title_case_select_options
                                    }
                        },
            },
        ]
    )



async def handle_response_custom(msg: ucapi.UserDataResponse) -> ucapi.RequestUserInput:
    """Process custom entity configuration response"""

    custom_entities_new = msg.input_values["custom_entities"]
    custom_entities_old = config.Setup.get("custom_entities")
    custom_entities_title_case_select_options = msg.input_values["custom_entities_title_case_select_options"]

    if custom_entities_new != custom_entities_old:
        try:
            config.Setup.set("custom_entities", custom_entities_new)
        except Exception as e:
            _LOG.error(e)
            config.Setup.set("setup_complete", False)
            return ucapi.SetupError()
        config.Setup.set("custom_entities_set", True)
        _LOG.info("New custom entity configuration saved")

        _LOG.debug("Clearing available and configured entities to update the entity definitions with the new custom entity configuration")
        driver.api.available_entities.clear()
        driver.api.configured_entities.clear()

    if custom_entities_new == "":
        try:
            config.Setup.set("custom_entities", custom_entities_old)
        except Exception as e:
            _LOG.error(e)
            config.Setup.set("setup_complete", False)
            return ucapi.SetupError()
        _LOG.warning("The entered custom entity configuration is empty. Reset to previous resp. example configuration")

    if custom_entities_title_case_select_options == "true": #Boolean in quotes as all values are returned as strings
        try:
            config.Setup.set("custom_entities_title_case_select_options", True)
        except Exception as e:
            _LOG.error(e)
            config.Setup.set("setup_complete", False)
            return ucapi.SetupError()
        _LOG.info("Custom select entities title case mode activated. Always return OK to the remote")
    else:
        try:
            config.Setup.set("custom_entities_title_case_select_options", False)
        except Exception as e:
            _LOG.error(e)
            config.Setup.set("setup_complete", False)
            return ucapi.SetupError()
        _LOG.info("Custom select entities title case mode deactivated. Return the actual status code")

    return await show_setup_action(msg)



async def finish_setup() -> ucapi.SetupAction:
    """Finish the setup process and add all entities"""

    # Always add all entities as the configurator will hide already configured entities since firmware 2.5.3
    await add_all_entities()

    if config.Setup.get("setup_reconfigure"):
        _LOG.info("Reconfiguration complete")
    else:
        _LOG.info("Setup complete")
    config.Setup.set("setup_complete", True)
    return ucapi.SetupComplete()
