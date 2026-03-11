#!/usr/bin/env python3

"""Main driver file. Run this module to start the integration driver"""

import os
import sys
import asyncio
import logging
from typing import Any

import ucapi

import config
import media_player
import remote
import selects
import setup

_LOG = logging.getLogger("driver")  # avoid having __main__ in log messages

loop = asyncio.get_event_loop() #TODO Change to new_event_loop() when using Python 3.12+
api = ucapi.IntegrationAPI(loop)



async def startcheck():
    """
    Called at the start of the integration driver to load the config file into the runtime storage and add a media player entity for all configured cmds
    """
    try:
        config.Setup.load()
    except OSError as o:
        _LOG.critical(o)
        _LOG.critical("Stopping integration driver")
        raise SystemExit(0) from o

    if config.Setup.get("setup_complete"):
        await setup.add_all_entities()



async def add_mp(entity_id: str, entity_name: str):
    # Only works when in driver.py. When in media_player.py the response to get_available entities is an empty list
    """
    Creates the media player entity definition and adds the entity to the remote via the api

    :param id: media_player entity id
    :param name: media_player entity name
    """

    definition = ucapi.MediaPlayer(
        entity_id,
        entity_name,
        [
            ucapi.media_player.Features.SELECT_SOURCE
        ],
        attributes={ucapi.media_player.Attributes.STATE: ucapi.media_player.States.ON},
        cmd_handler=mp_cmd_handler
    )

    api.available_entities.add(definition)

    _LOG.info("Added media player entity with id " + entity_id + " and name " + str(entity_name))



async def mp_cmd_handler(entity: ucapi.MediaPlayer, cmd_id: str, _params: dict[str, Any] | None) -> ucapi.StatusCodes:
    """
    Media Player command handler.

    Called by the integration-API if a command is sent to a configured media_player-entity.

    :param entity: media_player entity
    :param cmd_id: command
    :param _params: optional command parameters
    :return: status of the command
    """

    if not _params:
        _LOG.info(f"Received {cmd_id} command for {entity.id}")
    else:
        _LOG.info(f"Received {cmd_id} command with parameter {_params} for entity id {entity.id}")

    return await media_player.mp_cmd_assigner(entity.id, cmd_id, _params)



async def add_custom_entities(custom_entities: dict[str, Any]) -> None:
    """
    Adds custom remote and optional select entities using the custom entities configuration.

    :param custom_entities: dictionary of custom entities
    """

    custom_prefix = config.Setup.get("custom_entities_prefix")
    select_prefix = config.Setup.get("custom_entities_select_prefix")

    for entity_name, entity_config in custom_entities.items():
        _LOG.info(f"Adding custom entity \"{entity_name}\"")

        features = []
        attributes = {}

        entity_id = f"{custom_prefix}{entity_name.lower()}"
        features = list(entity_config.get("Features", {}).keys())
        simple_commands = list(entity_config.get("Simple Commands", {}).keys())

        if features:
            if "On" and "Off" in features:
                features.remove("On")
                features.remove("Off")
                features.append(ucapi.remote.Features.ON_OFF)
            if "Toggle" in features:
                features.remove("Toggle")
                features.append(ucapi.remote.Features.TOGGLE)
            attributes = {ucapi.remote.Attributes.STATE: ucapi.remote.States.UNKNOWN}

        #TODO Support for button mappings and ui pages in yaml config
        definition = ucapi.Remote(
            identifier=entity_id,
            name=entity_name,
            features=features,
            attributes=attributes,
            simple_commands=simple_commands,
            cmd_handler=remote.custom_remote_cmd_handler
        )

        api.available_entities.add(definition)

        # Add Select entities for each Select entry
        selects_config = entity_config.get("Selects", {}) or {}
        for select_name, select_options in selects_config.items():
            if not isinstance(select_options, list):
                _LOG.warning(f"Select '{select_name}' in entity '{entity_name}' is not a list, skipping")
                continue

            select_entity_id = f"{select_prefix}{entity_name.lower()}-{select_name.lower()}"

            _LOG.info(f"Adding select entity \"{select_entity_id}\"")

            select_definition = ucapi.Select(
                identifier=select_entity_id,
                name=f"{entity_name} - {select_name}",
                attributes={ucapi.select.Attributes.STATE: ucapi.select.States.ON},
                #Other attributes will be updated/set during the subscribe entities event
                cmd_handler=selects.select_cmd_handler
            )

            api.available_entities.add(select_definition)



@api.listens_to(ucapi.Events.CONNECT)
async def on_intg_connect() -> None:
    """
    Connect notification from Remote.

    Just reply with connected as there is no permanent connection to a device that needs to be re-established
    """
    _LOG.info("Received connect event message from remote")

    await api.set_device_state(ucapi.DeviceStates.CONNECTED)



@api.listens_to(ucapi.Events.DISCONNECT)
async def on_intg_disconnect() -> None:
    """
    Disconnect notification from the Remote.

    Just reply with disconnected as there is no permanent connection to a device that needs to be closed
    """
    _LOG.info("Received disconnect event message from remote")

    await api.set_device_state(ucapi.DeviceStates.DISCONNECTED)



@api.listens_to(ucapi.Events.CLIENT_CONNECTED)
async def on_client_connect() -> None:
    """
    Websocket client connect notification from Remote.
    """
    _LOG.debug("Remote websocket client connected to this integration websockets server")
    _LOG.debug("There are currently %d websocket clients connected to this integration websockets server", int(api.client_count))



@api.listens_to(ucapi.Events.CLIENT_DISCONNECTED)
async def on_client_disconnect() -> None:
    """
    Websocket client disconnect notification from the Remote.
    """
    _LOG.debug("Remote websocket client disconnected from this integration websockets server")
    client_count = int(api.client_count)
    if client_count > 0:
        _LOG.debug("There are currently %d websocket clients connected to this integration websockets server", client_count)
    else:
        _LOG.debug("No other websocket clients are currently connected to this integration websockets server")



@api.listens_to(ucapi.Events.ENTER_STANDBY)
async def on_r2_enter_standby() -> None:
    """
    Enter standby notification from Remote.

    Set standby to True and show a debug log message as there is no permanent connection to a device that needs to be closed.
    """
    _LOG.info("Received enter standby event message from remote")

    config.Setup.set("standby", True)



@api.listens_to(ucapi.Events.EXIT_STANDBY)
async def on_r2_exit_standby() -> None:
    """
    Exit standby notification from Remote.

    Set standby to False and just show a debug log message as there is no permanent connection to a device that needs to be re-established.
    """
    _LOG.info("Received exit standby event message from remote")

    config.Setup.set("standby", False)



@api.listens_to(ucapi.Events.SUBSCRIBE_ENTITIES)
async def on_subscribe_entities(entity_ids: list[str]) -> None:
    """
    Subscribe to given entities.

    :param entity_ids: entity identifiers.

    Just show a debug log message as there are no attributes to update.
    """
    _LOG.info("Received subscribe entities event for entity ids: " + str(entity_ids))

    config.Setup.set("standby", False)

    if config.Setup.get("custom_entities_set"):
        await selects.set_all_attributes()



#BUG No event when removing an entity as configured entity. Could be a UC Python library or core/web configurator bug.
# https://github.com/unfoldedcircle/integration-python-library/issues/25
@api.listens_to(ucapi.Events.UNSUBSCRIBE_ENTITIES)
async def on_unsubscribe_entities(entity_ids: list[str]) -> None:
    """
    Unsubscribe to given entities.

    :param entity_ids: entity identifiers.

    Just show a debug log message as there is not device to disconnect.
    """
    _LOG.info("Unsubscribe entities event for entity ids: %s", entity_ids)

    #TODO #WAIT Add api.configured_entities.remove(entity_ids) when the unsubscribe event is handled by the integration API



def setup_logger():
    """Get logger from all modules"""

    level = os.getenv("UC_LOG_LEVEL", "DEBUG").upper()

    logging.getLogger("ucapi.api").setLevel(level)
    logging.getLogger("ucapi.entities").setLevel(level)
    logging.getLogger("ucapi.entity").setLevel(level)
    logging.getLogger("driver").setLevel(level)
    logging.getLogger("commands").setLevel(level)
    logging.getLogger("media_player").setLevel(level)
    logging.getLogger("remote").setLevel(level)
    logging.getLogger("selects").setLevel(level)
    logging.getLogger("sensor").setLevel(level)
    logging.getLogger("setup").setLevel(level)
    logging.getLogger("config").setLevel(level)
    logging.getLogger("getmac").setLevel(level)



class JournaldFormatter(logging.Formatter):
    """Formatter for journald. Prefixes messages with priority level."""

    def format(self, record):
        """Format the log record with journald priority prefix."""
        # mapping of logging levels to journald priority levels
        # https://www.freedesktop.org/software/systemd/man/latest/sd-daemon.html#syslog-compatible-log-levels
        # Note: DEBUG app messages are logged with priority 6 (info) and INFO with priority 5 (notice)
        # This is a workaround until the log subsystem on the Remote is updated to support debug levels.
        priority = {
            logging.DEBUG: "<6>", # SD_INFO
            logging.INFO: "<5>", # SD_NOTICE
            logging.WARNING: "<4>",
            logging.ERROR: "<3>",
            logging.CRITICAL: "<2>",
        }.get(record.levelno, "<6>")
        return f"{priority}{record.name:<14s} | {record.getMessage()}"



async def main():
    """Main function that gets logging from all sub modules and starts the driver"""

    if os.getenv("INVOCATION_ID"):
        # when running under systemd: timestamps are added by the journal
        # and we use a custom formatter for journald priority levels
        handler = logging.StreamHandler()
        handler.setFormatter(JournaldFormatter())
        logging.basicConfig(handlers=[handler])
    else:
        logging.basicConfig(
            format="%(asctime)s.%(msecs)03d | %(levelname)-8s | %(name)-14s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    setup_logger()

    #Check if integration runs in a PyInstaller bundle on the remote and adjust the logging format and config file path
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):

        _LOG.info("This integration is running in a PyInstaller bundle. Probably on the remote hardware")
        config.Setup.set("bundle_mode", True)

        cfg_path = os.environ["UC_CONFIG_HOME"] + "/" + config.Setup.get("cfg_path")
        config.Setup.set("cfg_path", cfg_path)
        _LOG.info("The configuration is stored in " + cfg_path)

        yaml_path = os.environ["UC_CONFIG_HOME"] + "/" + config.Setup.get("yaml_path")
        config.Setup.set("yaml_path", yaml_path)
        _LOG.info("The custom entities yaml configuration is stored in " + yaml_path)

    await setup.init()
    await startcheck()



if __name__ == "__main__":
    try:
        loop.run_until_complete(main())
        loop.run_forever()
    except KeyboardInterrupt:
        pass
