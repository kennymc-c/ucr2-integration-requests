#!/usr/bin/env python3

"""Module that includes functions to handle custom select entities with simple commands as options"""

import logging
from typing import Any

import ucapi

import driver
import config
import remote

_LOG = logging.getLogger(__name__)



async def update_attributes(entity_id: str, option: str) -> bool:
    """Update the current option value for a select entity"""

    if driver.api.configured_entities.get(entity_id) is None:
        _LOG.info(f"Entity {entity_id} not found in configured entities. Skip updating attributes")
        return False

    attributes_to_send = {ucapi.select.Attributes.CURRENT_OPTION: option}

    try:
        driver.api.configured_entities.update_attributes(entity_id, attributes_to_send)
    except Exception as e:
        _LOG.error(f"Error while updating attributes for entity id {entity_id}: {e}")
        raise Exception("Error while updating select value for entity id " + entity_id) from e

    _LOG.info(f"Updated select entity {entity_id} to option '{option}'")
    return True



def _get_data(entity: ucapi.Select, custom_config: dict):
    """Get all options and the higher-level remote config for a select entity from the custom configuration.

    Returns a tuple with all options of the given select entity and the higher-level remote entity configuration 
    """

    remote_prefix = config.Setup.get("custom_entities_prefix")
    select_prefix = config.Setup.get("custom_entities_select_prefix")

    for entity_name in custom_config.keys():
        if entity_name.lower() in entity:
            remote_name = entity_name
            remote_id = f"{remote_prefix}{remote_name.lower()}"
            break
    else:
        _LOG.error(f"No matching custom remote entity found for select entity {entity} in custom entities configuration")
        raise KeyError

    remote_config = None
    for entity_name, config_item in custom_config.items():
        if remote_id == f"{remote_prefix}{entity_name.lower()}":
            remote_config = config_item
            break
    if not remote_config:
        raise ValueError(f"No matching remote entity config found for select entity {entity}")

    selects_config = None
    for entity_name, entity_config in custom_config.items():
        if entity_name.lower() in remote_id:
            selects_config = entity_config.get("Selects", {}) or {}
            break
    if not selects_config:
        raise ValueError(f"No matching selects config found for select entity {entity}")

    select_options = None
    for select_name, select_options in selects_config.items():
        if f"{select_prefix}{remote_name.lower()}-{select_name.lower()}" == entity:
            return select_options, remote_config
    if select_options is None:
        _LOG.error(f"No options found for select entity {entity} in custom entities configuration")
        raise ValueError




async def _execute_command(select_entity_id: str, entity_config: dict[str, Any], option: str) -> ucapi.StatusCodes:
    """Send command for calculated option and update entity attributes on success."""

    _LOG.debug(f"Executing option '{option}' for entity '{select_entity_id}'")
    _LOG.debug(str(entity_config))

    cmd_status = await remote.send_command(
        entity_id=select_entity_id,
        entity_config=entity_config,
        command=option,
    )

    if cmd_status == ucapi.StatusCodes.OK:
        try:
            await update_attributes(select_entity_id, option)
        except Exception as e:
            _LOG.warning(f"Could not update select entity attributes for {select_entity_id}: {e}")

    return cmd_status



async def select_cmd_handler(entity: ucapi.Select, cmd_id: str, _params: dict | None) -> ucapi.StatusCodes:
    """
    Custom select entity command handler.

    Called by the integration-API if a command is sent to a configured select entity.

    :param entity: select entity
    :param cmd_id: command
    :param _params: optional command parameters (should contain 'value' for SELECT_OPTION command)
    :return: status of the command
    """

    if not _params:
        _LOG.info(f"Received {cmd_id} command for {entity.id}")
    else:
        _LOG.info(f"Received {cmd_id} command with parameter {_params} for entity id {entity.id}")

    custom_entities = config.Setup.get("custom_entities", python_dict=True)

    cycle = True #Using the same cycle=True default as HA as this parameter currently can't be changed by the user
    if _params:
        try:
            if _params["cycle"] == "false":
                cycle = False
        except KeyError:
            pass #BUG Cycle parameter currently not included in web configurator or commands
        #although it's not labeled as a planned feature in the core-api docs

    try:
        options , remote_config = _get_data(entity.id, custom_entities)
    except Exception:
        return ucapi.StatusCodes.NOT_FOUND

    match cmd_id:

        case ucapi.select.Commands.SELECT_OPTION:
            current_option = _params.get("option")
            return await _execute_command(select_entity_id=entity.id, entity_config=remote_config, option=current_option)

        case ucapi.select.Commands.SELECT_FIRST:
            first_option = options[0]
            return await _execute_command(select_entity_id=entity.id, entity_config=remote_config, option=first_option)

        case ucapi.select.Commands.SELECT_LAST:
            last_option = options[-1]
            return await _execute_command(select_entity_id=entity.id, entity_config=remote_config, option=last_option)

        case ucapi.select.Commands.SELECT_NEXT | ucapi.select.Commands.SELECT_PREVIOUS:
            try:
                stored_data = await driver.api.available_entities.get_states()
            except Exception as e:
                _LOG.error("Couldn't get stored states from remote. Cannot compute next or previous option")
                _LOG.info(str(e))
                return ucapi.StatusCodes.CONFLICT

            current_option = next((s.get("attributes", {}).get(ucapi.select.Attributes.CURRENT_OPTION) for s in stored_data if s.get("entity_id") == entity.id), None)

            try:
                idx = options.index(current_option) if current_option in options else -1
            except ValueError:
                idx = -1

            if idx == -1:
                _LOG.warning("Could't retrieve the current option. Will use the first option instead")
                fallback_option = options[0]
                return await _execute_command(
                    select_entity_id=entity.id,
                    entity_config=remote_config,
                    option=fallback_option,
                )

            last_index = len(options) - 1

            if cmd_id == ucapi.select.Commands.SELECT_NEXT:
                if idx == last_index:
                    if not cycle:
                        _LOG.info("Reached the end of the options list. Won't cycle to the first option as cycling is disabled for this command")
                        return ucapi.StatusCodes.OK
                    next_idx = 0
                else:
                    next_idx = idx + 1

                next_option = options[next_idx]
                return await _execute_command(
                    select_entity_id=entity.id,
                    entity_config=remote_config,
                    option=next_option,
                )

            if cmd_id == ucapi.select.Commands.SELECT_PREVIOUS:
                if idx == 0:
                    if not cycle:
                        _LOG.info("Reached the beginning of the options list. Won't cycle to the last option as cycling is disabled for this command")
                        return ucapi.StatusCodes.OK
                    prev_idx = last_index
                else:
                    prev_idx = idx - 1

                previous_option = options[prev_idx]
                return await _execute_command(
                    select_entity_id=entity.id,
                    entity_config=remote_config,
                    option=previous_option,
                )

        case _:
            _LOG.info(f"Unknown command \"{cmd_id}\" for custom select entity with id {entity.id}")
            return ucapi.StatusCodes.NOT_IMPLEMENTED
