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





def _resolve_select_option(item, use_title_case: bool) -> tuple[str, str]:
    """
    Returns (command_id, display_label) for a single select option item.

    Handles two stored formats:
      - plain string  → "INPUT_2"
      - flat dict     → {"INPUT_1": "Video Input 1"}
    """
    if isinstance(item, dict) and len(item) == 1:
        cmd = list(item.keys())[0]
        displayname = list(item.values())[0]
        return cmd, str(displayname) if displayname else cmd
    cmd = str(item)
    label = cmd.replace("_", " ").title() if use_title_case else cmd
    return cmd, label



async def set_all_attributes():
    """Set all option attributes for all select entities"""

    custom_entities = config.Setup.get("custom_entities", python_dict=True)
    select_prefix = config.Setup.get("custom_entities_select_prefix")
    use_title_case = config.Setup.get("custom_entities_title_case_select_options")

    for entity_name, entity_config in custom_entities.items():

        selects_config = entity_config.get("Selects", {}) or {}
        for select_name, select_options in selects_config.items():
            select_entity_id = f"{select_prefix}{entity_name.lower()}-{select_name.lower()}"

            # Build parallel lists: command ids (for execution) and display labels (for the UI)
            all_options = []   # display labels shown in the UI
            for option in select_options:
                _cmd, label = _resolve_select_option(option, use_title_case)
                all_options.append(label)

            current_option = all_options[0] if all_options else ""

            _LOG.debug(f"Update options to: {all_options}")
            _LOG.debug(f"Update current option to: {current_option}")

            attributes = {
                ucapi.select.Attributes.OPTIONS: all_options,
                ucapi.select.Attributes.CURRENT_OPTION: current_option,
                ucapi.select.Attributes.STATE: ucapi.select.States.ON
            }

            # BUG WORKAROUND Always send DeviceStates.CONNECTED when updating select entity attributes
            await driver.api.set_device_state(ucapi.DeviceStates.CONNECTED)
            driver.api.available_entities.update_attributes(select_entity_id, attributes)



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




async def _execute_command(select_entity_id: str, entity_config: dict[str, Any], command: str, label: str | None = None) -> ucapi.StatusCodes:
    """Send simple command and update entity attributes with the display label on success.
    
    :param command: simple command id to send (e.g. INPUT_1)
    :param label: display label used for the attribute update; defaults to command if not given
    """

    if label is None:
        label = command

    _LOG.debug(f"Executing command '{command}' (label: '{label}') for entity '{select_entity_id}'")
    _LOG.debug(str(entity_config))

    cmd_status = await remote.send_command(
        entity_id=select_entity_id,
        entity_config=entity_config,
        command=command,
    )

    if cmd_status == ucapi.StatusCodes.OK:
        try:
            await update_attributes(select_entity_id, label)
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

    cycle = True #https://github.com/unfoldedcircle/core-api/blob/0cb10a6066eba1abc26b687d1d0e41bea7f3efd7/doc/entities/entity_select.md?plain=1#L137
    if _params:
        try:
            if _params["cycle"] == "false":
                cycle = False
        except KeyError:
            pass  #Needed for next/previous commands created before 2.9.0 that don't include any parameters

    try:
        options, remote_config = _get_data(entity.id, custom_entities)
    except Exception:
        return ucapi.StatusCodes.NOT_FOUND

    use_title_case = config.Setup.get("custom_entities_title_case_select_options")

    # Build list of (cmd_id, display_label) tuples once for all command types.
    # _resolve_select_option handles both plain strings and {"CMD": "Displayname"} dicts.
    resolved: list[tuple[str, str]] = [_resolve_select_option(o, use_title_case) for o in options]

    match cmd_id:

        case ucapi.select.Commands.SELECT_OPTION:
            requested_label = _params.get("option")
            # Find the pair whose display label matches what the UI sent
            pair = next(((cmd, lbl) for cmd, lbl in resolved if lbl == requested_label), None)
            if pair is None:
                _LOG.warning(f"Option '{requested_label}' not found in resolved options for {entity.id}")
                return ucapi.StatusCodes.BAD_REQUEST
            return await _execute_command(entity.id, remote_config, command=pair[0], label=pair[1])

        case ucapi.select.Commands.SELECT_FIRST:
            cmd, lbl = resolved[0]
            return await _execute_command(entity.id, remote_config, command=cmd, label=lbl)

        case ucapi.select.Commands.SELECT_LAST:
            cmd, lbl = resolved[-1]
            return await _execute_command(entity.id, remote_config, command=cmd, label=lbl)

        case ucapi.select.Commands.SELECT_NEXT | ucapi.select.Commands.SELECT_PREVIOUS:
            try:
                stored_data = await driver.api.available_entities.get_states()
            except Exception as e:
                _LOG.error("Couldn't get stored states from remote. Cannot compute next or previous option")
                _LOG.info(str(e))
                return ucapi.StatusCodes.CONFLICT

            current_label = next(
                (s.get("attributes", {}).get(ucapi.select.Attributes.CURRENT_OPTION)
                 for s in stored_data if s.get("entity_id") == entity.id),
                None
            )

            # Match by display label (what is stored in the attribute)
            idx = next((i for i, (_, lbl) in enumerate(resolved) if lbl == current_label), -1)

            if idx == -1:
                _LOG.warning("Couldn't retrieve the current option. Will use the first option instead")
                cmd, lbl = resolved[0]
                return await _execute_command(entity.id, remote_config, command=cmd, label=lbl)

            last_index = len(resolved) - 1

            if cmd_id == ucapi.select.Commands.SELECT_NEXT:
                if idx == last_index:
                    if not cycle:
                        _LOG.info("Reached the end of the options list. Won't cycle to the first option as cycling is disabled")
                        return ucapi.StatusCodes.OK
                    next_idx = 0
                else:
                    next_idx = idx + 1
                cmd, lbl = resolved[next_idx]
                return await _execute_command(entity.id, remote_config, command=cmd, label=lbl)

            if cmd_id == ucapi.select.Commands.SELECT_PREVIOUS:
                if idx == 0:
                    if not cycle:
                        _LOG.info("Reached the beginning of the options list. Won't cycle to the last option as cycling is disabled")
                        return ucapi.StatusCodes.OK
                    prev_idx = last_index
                else:
                    prev_idx = idx - 1
                cmd, lbl = resolved[prev_idx]
                return await _execute_command(entity.id, remote_config, command=cmd, label=lbl)

        case _:
            _LOG.info(f"Unknown command \"{cmd_id}\" for custom select entity with id {entity.id}")
            return ucapi.StatusCodes.NOT_IMPLEMENTED
