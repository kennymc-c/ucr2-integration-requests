"""This module contains some fixed variables, the Setup class which includes all fixed and customizable variables"""

import json
import os
import re
import logging
from collections import Counter, defaultdict
from yaml import safe_load, dump, YAMLError
import ucapi

_LOG = logging.getLogger(__name__)


def check_duplicate_yaml_entities(yaml_text: str):
    """Checks for duplicate entity names in the YAML custom entities configuration."""
    keys = []
    for line in yaml_text.splitlines():
        if not line.strip() or line.lstrip().startswith("#") or ":" not in line:
            continue
        indent = len(line) - len(line.lstrip())
        if indent == 0: # Only first level (no indentation)
            key = line.split(":", 1)[0].strip().strip("'\"")
            keys.append(key)
    duplicates = [k for k, v in Counter(keys).items() if v > 1]
    if duplicates:
        raise ValueError(f"Duplicate entity name(s) found: {duplicates}")



def check_duplicate_yaml_simple_commands(yaml_text: str):
    """Checks for duplicate simple command names in the YAML custom entities configuration."""

    errors = []
    current_entity = None
    in_simple_commands = False
    simple_indent = None
    cmds_by_entity = defaultdict(list)

    for line in yaml_text.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue

        # Match top-level entity
        entity_match = re.match(r"^([^\s][^:]*):\s*$", line)
        if entity_match:
            current_entity = entity_match.group(1)
            in_simple_commands = False
            continue

        # Detect Simple Commands section
        match_simple = re.match(r"^\s*Simple Commands\s*:\s*$", line)
        if match_simple:
            in_simple_commands = True
            simple_indent = len(line) - len(line.lstrip())
            continue

        if in_simple_commands and current_entity:
            line_indent = len(line) - len(line.lstrip())

            if line_indent <= simple_indent:
                in_simple_commands = False
                continue

            if line_indent == simple_indent + 2:
                cmd_match = re.match(r"^\s*([^\s][^:]*):", line)
                if cmd_match:
                    cmd_name = cmd_match.group(1).strip().strip("'\"")
                    cmds_by_entity[current_entity].append(cmd_name)

    # Check duplicates
    for entity, cmds in cmds_by_entity.items():
        duplicates = [k for k, v in Counter(cmds).items() if v > 1]
        if duplicates:
            errors.append(f"Entity \"{entity}\": {duplicates}")

    if errors:
        raise Exception("Duplicate simple command name(s) found:\n" + "\n".join(errors))



def validate_custom_entities(entities, allowed_second_level, allowed_fourth_level, allowed_types, allowed_features):
    """Validates the custom entities configuration against the allowed second level, fourth level keys and command types and duplicate simple command names."""
    errors = []

    for entity_name, entity_config in entities.items():

        # Check for non allowed second level keys
        for key in entity_config.keys():
            if key.lower() not in allowed_second_level:
                errors.append(
                    f"Invalid entry '{key}' in entity '{entity_name}'. Only {sorted(allowed_second_level)} are allowed."
                )

        # Features
        features = entity_config.get("Features", {}) or entity_config.get("features", {})
        new_features = {}

        for feat_name, feat_value in features.items():
            for k in feat_value.keys():
                if k.lower() not in allowed_fourth_level:
                    errors.append(
                        f"Invalid entry '{k}' in Features -> {feat_name} of entity '{entity_name}'. "
                        f"Only {sorted(allowed_fourth_level)} are allowed."
                    )
            if "Type" in feat_value:
                if feat_value["Type"].lower() not in allowed_types:
                    errors.append(
                        f"Invalid Type '{feat_value['Type']}' in Features -> {feat_name} of entity '{entity_name}'. "
                        f"Only {sorted(allowed_types)} are allowed."
                    )
            feat_name_lc = feat_name.lower()
            if feat_name_lc not in allowed_features:
                errors.append(
                    f"The feature \"{feat_name}\" defined for entity \"{entity_name}\" is not a valid remote entity feature."
                )
            else:
                new_features[feat_name] = feat_value

        entity_config["Features"] = new_features

        # Simple Commands
        simple_cmds = entity_config.get("Simple Commands", {}) or entity_config.get("simple commands", {})

        new_cmds = {}
        allowed_chars = "A-Za-z0-9/_.:+#*°@%()?-"
        pattern = rf"[^{allowed_chars}]"

        for cmd_name, cmd_value in simple_cmds.items():

            for k in cmd_value.keys():
                if k.lower() not in allowed_fourth_level:
                    errors.append(
                        f"Invalid entry '{k}' in Simple Commands -> {cmd_name} of entity '{entity_name}'. "
                        f"Only {sorted(allowed_fourth_level)} are allowed."
                    )

            if "Type" in cmd_value:
                if cmd_value["Type"].lower() not in allowed_types:
                    errors.append(
                        f"Invalid type '{cmd_value['Type']}' in Simple Commands -> {cmd_name} of entity '{entity_name}'. "
                        f"Only {sorted(allowed_types)} are allowed."
                    )

            new_name = re.sub(pattern, "_", cmd_name).upper()[:20]

            if new_name != cmd_name:
                _LOG.warning(
                    f"Simple command name \"{cmd_name}\" in entity \"{entity_name}\" has been corrected to '{new_name}' "
                    f"to match the simple command name requirements"
                )

            new_cmds[new_name] = cmd_value

        entity_config["Simple Commands"] = new_cmds

    if errors:
        raise Exception("Custom entities yaml configuration validation failed with the following errors:\n" + "\n".join(errors))

    return entities



def validate_yaml(yaml_string: str) -> dict:
    """
    Validates the YAML custom entities configuration against non allowed options, duplicate entity and simple command names.

    :raises Exception: If the YAML string is not valid, contains duplicates or invalid keys.
    :returns: A validated Python dictionary of custom entities.
    :param yaml_string: YAML string to validate
    :param allowed_simple_chars: characters that are allowed in simple command names
    """

    # safe_load() does not support to check for duplicate keys and removes them automatically as they are not allowed in a Python dict.
    # Therefore we need to do this with the YAML string instead of the parsed Python dict

    duplicate_errors = []
    try:
        check_duplicate_yaml_entities(yaml_string)
    except Exception as e:
        duplicate_errors.append(str(e))
    try:
        check_duplicate_yaml_simple_commands(yaml_string)
    except Exception as e:
        duplicate_errors.append(str(e))
    if duplicate_errors:
        raise ValueError("Duplicate(s) have been found:\n" + "\n".join(duplicate_errors))

    allowed_features = [feature.value for feature in ucapi.remote.Features]

    if "on_off" in allowed_features:
        allowed_features.extend(["on", "off"])
        allowed_features.remove("on_off")

    allowed_second_level = {"features", "simple commands"}
    allowed_fourth_level = {"type", "parameter"}
    allowed_types = set([cmd.lower() for cmd in Setup.all_cmds])

    # Now convert the YAML string to a Python dict for further validation that works with the parsed dict
    try:
        entities = safe_load(yaml_string)
    except YAMLError as e:
        raise ValueError("The entered configuration is not valid YAML: " + str(e)) from e

    variables = entities.get("_vars", {}) # Get variables block if it exists to add it again after validation
    entities.pop("_vars", {})  # Remove variable block if it exists for validation process

    validated_config = validate_custom_entities(entities, allowed_second_level, allowed_fourth_level, allowed_types, allowed_features)

    #If the _vars block exists add it again at the top after validation
    if variables:
        validated_config = {"_vars": variables, **validated_config}

    return validated_config



def substitute_yaml_vars(obj, variables):
    """Substitutes variables in the YAML configuration with their values."""
    # Regex for ${var}
    pattern = re.compile(r"\${([^}]+)}")

    if isinstance(obj, str):
        return pattern.sub(lambda m: str(variables.get(m.group(1), m.group(0))), obj)
    elif isinstance(obj, list):
        return [substitute_yaml_vars(i, variables) for i in obj]
    elif isinstance(obj, dict):
        return {k: substitute_yaml_vars(v, variables) for k, v in obj.items()}
    return obj



class Setup:
    """Setup class which includes all fixed and customizable variables including functions to set() and get() them from a runtime storage
    which includes storing them in a json config file and as well as load() them from this file"""

    _custom_entities = {}

    __conf = {
        "standby": False,
        "setup_complete": False,
        "setup_reconfigure": False,
        "bundle_mode": False,
        "setup_step": "init",
        "setup_action_dropdown_items": [
                                    {"id": "finish", "label": {"en": "Finish Setup", "de": "Einrichtung abschließen"}},
                                    {"id": "advanced", "label": {"en": "Configure advanced settings", "de": "Erweiterte Einstellungen konfigurieren"}},
                                    {"id": "custom", "label": {"en": "Configure custom entities", "de": "Eigene Entitäten konfigurieren"}}
                                ],
        "cfg_path": "config.json",
        "yaml_path": "custom_entities.yaml",
        "custom_entities_set": False,
        "custom_entities_prefix": "remote-custom-",
        "tcp_text_timeout": 2,
        "tcp_text_response_wait": True,
        "tcp_text_terminator": "\n",
        "tcp_text_terminator_dropdown_items": [
                                                {"id": "None", "label": {"en": "No command terminator", "de": "Kein Befehlsabschlusszeichen"}},
                                                {"id": "\n", "label": {"en": "\\n", "de": "\\n"}},
                                                {"id": "\r", "label": {"en": "\\r", "de": "\\r"}},
                                                {"id": "\r\n", "label": {"en": "\\r\\n", "de": "\\r\\n"}},
                                                {"id": ";", "label": {"en": ";", "de": ";"}}
                                                ],
        "rq_timeout": 2,
        "rq_ssl_verify": True,
        "rq_user_agent": "uc-intg-requests",
        "rq_fire_and_forget": False,
        "rq_response_regex": "",
        "rq_response_nomatch_option": "full",
        "rq_response_nomatch_dropdown_items": [
                                                {"id": "full", "label": {"en": "Full", "de": "Komplett"}},
                                                {"id": "empty", "label": {"en": "Empty", "de": "Leer"}},
                                                {"id": "error", "label": {"en": "Error", "de": "Fehler"}}
                                                ],
        "id-rq-sensor": "http-response",
        "name-rq-sensor": {
                        "en": "HTTP Request Response",
                        "de": "HTTP Anfrage-Antwort"
                        },
        "id-get": "http-get",
        "name-get": "HTTP Get",
        "id-post": "http-post",
        "name-post": "HTTP Post",
        "id-patch": "http-patch",
        "name-patch": "HTTP Patch",
        "id-put": "http-put",
        "name-put": "HTTP Put",
        "id-delete": "http-delete",
        "name-delete": "HTTP Delete",
        "id-head": "http-head",
        "name-head": "HTTP Head",
        "id-wol": "wol",
        "name-wol": "Wake on LAN",
        "id-tcp-text": "tcp-text",
        "name-tcp-text": {
                        "en": "Text over TCP",
                        "de": "Text über TCP"
                        }
    }
    __setters = ["standby", "setup_complete", "setup_reconfigure", "tcp_text_timeout", "tcp_text_response_wait", "tcp_text_terminator", \
                "tcp_text_terminator_dropdown_items", "rq_timeout", "rq_user_agent", "rq_ssl_verify", \
                "rq_fire_and_forget", "rq_response_regex", "rq_response_nomatch_option", "custom_entities", "custom_entities_set", \
                "bundle_mode", "cfg_path", "yaml_path", "setup_step"]
    #Skip runtime only related values in config file
    __storers = ["setup_complete", "tcp_text_timeout", "tcp_text_response_wait", "tcp_text_terminator", "tcp_text_terminator_dropdown_items", \
                "rq_timeout", "rq_user_agent", "rq_ssl_verify", "rq_fire_and_forget", \
                "rq_response_regex", "rq_response_nomatch_option", "custom_entities", "custom_entities_set"]

    all_cmds = ["get", "post", "patch", "put", "delete", "head", "wol", "tcp-text"]
    rq_ids = [__conf["id-rq-sensor"], __conf["id-get"], __conf["id-post"], __conf["id-patch"], __conf["id-put"], __conf["id-delete"], __conf["id-head"]]
    rq_names = [__conf["name-rq-sensor"], __conf["name-get"], __conf["name-post"], __conf["name-patch"], __conf["name-put"], __conf["name-delete"], __conf["name-head"]]

    @staticmethod
    def get(key, python_dict: bool = False):
        """Get the value from the specified key in __conf as string or dict from _custom_entities that can also be returned as a string"""
        if python_dict:
            if key == "custom_entities":
                yaml_path = Setup.__conf["yaml_path"]
                with open(yaml_path, "r", encoding="utf-8") as f:
                    raw = safe_load(f)
                # Read and remove variable block if it exists when loading as a dict
                variables = raw.pop("_vars", {})
                _LOG.debug("Get variables from _vars block in custom entities yaml configuration")
                return substitute_yaml_vars(raw, variables)
            raise ValueError(key + " can not only be returned as a string")
        if key == "custom_entities":
            yaml_path = Setup.__conf["yaml_path"]
            with open(yaml_path, "r", encoding="utf-8") as f:
                return f.read()
        if Setup.__conf[key] == "" and key != "rq_response_regex": #rq_response_regex can be empty
            raise ValueError("Got empty value for " + key + " from config storage")
        return Setup.__conf[key]

    @staticmethod
    def set(key, value):
        """Save a value for the specified key into the config or custom entities runtime storage and store some of them into a json or custom entities in a yaml config file.
        Saving and storing setup_complete flag during reconfiguration will be ignored as well as storing values that have not been changed from the default"""

        if key in Setup.__setters:
            if Setup.__conf["setup_reconfigure"] is True and key == "setup_complete":
                _LOG.debug("Ignore saving and storing setup_complete flag during reconfiguration")

            else:
                skip_store = False
                if key == "custom_entities":
                    if key in Setup.__storers and value == Setup._custom_entities:
                        skip_store = True
                        _LOG.debug("Skip storing " + key + " into yaml file as it has not been changed from the previous config")
                    else:
                        try:
                            validated_custom_entities_dict = validate_yaml(value)
                        except Exception as e:
                            raise Exception(str(e)) from e
                        Setup._custom_entities = validated_custom_entities_dict
                        _LOG.debug("Saved custom entities as Python dict into custom entities runtime storage")
                        # Use validated configuration dict for storing it in the yaml file
                        value = validated_custom_entities_dict

                else:
                    if key in Setup.__storers and value == Setup.__conf[key]:
                        skip_store = True
                        _LOG.debug("Skip storing " + key + ": " + str(value) + " into config file as it has not been changed \
from the default value of " + str(Setup.__conf[key]))
                    Setup.__conf[key] = value
                    _LOG.debug("Saved " + key + ": " + str(value) + " into config runtime storage")

                #Store key/value pair in json config file and custom_entities in yaml file
                if skip_store is False:
                    if key in Setup.__storers:
                        if key == "custom_entities":
                            yaml_path = Setup.__conf["yaml_path"]
                            try:
                                with open(yaml_path, "w", encoding="utf-8") as f:
                                    # Leave the keys order as in the dict with sort_keys=False which is True by default
                                    f.write(dump(value, allow_unicode=True, sort_keys=False))
                                _LOG.debug("Stored custom entities configurations as YAML string into " + yaml_path)
                            except Exception as e:
                                raise Exception("Error while storing custom entities to " + yaml_path + ": " + str(e)) from e
                        else:
                            jsondata = {key: value}
                            if os.path.isfile(Setup.__conf["cfg_path"]):
                                try:
                                    with open(Setup.__conf["cfg_path"], "r+", encoding="utf-8") as f:
                                        l = json.load(f)
                                        l.update(jsondata)
                                        f.seek(0)
                                        f.truncate() #Needed when the new value has less characters than the old value (e.g. false to true or 11 to 5 seconds timeout)
                                        json.dump(l, f)
                                        _LOG.debug("Stored " + key + ": " + str(value) + " into " + Setup.__conf["cfg_path"])
                                except OSError as o:
                                    raise Exception(o) from o
                                except Exception as e:
                                    raise Exception("Error while storing " + key + ": " + str(value) + " into " + Setup.__conf["cfg_path"]) from e

                            #Create config file first if it doesn't exists yet
                            else:
                                try:
                                    with open(Setup.__conf["cfg_path"], "w", encoding="utf-8") as f:
                                        json.dump(jsondata, f)
                                    _LOG.debug("Created " + Setup.__conf["cfg_path"] + " and stored " + key + ": " + str(value) + " in it")
                                except OSError as o:
                                    raise Exception(o) from o
                                except Exception as e:
                                    raise Exception("Error while storing " + key + ": " + str(value) + " into " + Setup.__conf["cfg_path"]) from e

                    else:
                        _LOG.debug(key + " not found in __storers because it should not be stored in the config file")

        else:
            raise NameError(key + " not found in __setters because it should not be changed")

    @staticmethod
    def load():
        """Load all variables from the config json file into the runtime storage and load custom_entities yaml as string"""
        if os.path.isfile(Setup.__conf["cfg_path"]):

            try:
                with open(Setup.__conf["cfg_path"], "r", encoding="utf-8") as f:
                    configfile = json.load(f)
            except Exception as e:
                raise OSError("Error while reading " + Setup.__conf["cfg_path"]) from e
            if configfile == "":
                raise OSError("Error in " + Setup.__conf["cfg_path"] + ". No data")

            Setup.__conf["setup_complete"] = configfile["setup_complete"]
            _LOG.debug("Loaded setup_complete: " + str(configfile["setup_complete"]) + " into runtime storage from " + Setup.__conf["cfg_path"])

            if not Setup.__conf["setup_complete"]:
                _LOG.warning("The setup was not completed the last time. Please restart the setup process")
            else:
                if "tcp_text_timeout" in configfile:
                    Setup.__conf["tcp_text_timeout"] = configfile["tcp_text_timeout"]
                    _LOG.info("Loaded custom text over tcp timeout of " + str(configfile["tcp_text_timeout"]) + " seconds \
into runtime storage from " + Setup.__conf["cfg_path"])
                else:
                    _LOG.debug("Skip loading custom text over tcp timeout as it has not been changed during setup. \
The Default value of " + str(Setup.get("tcp_text_timeout")) + " seconds will be used")

                if "tcp_text_response_wait" in configfile:
                    Setup.__conf["tcp_text_response_wait"] = configfile["tcp_text_response_wait"]
                    _LOG.info("Loaded custom text over tcp wait for response " + str(configfile["tcp_text_response_wait"]) + " flag \
into runtime storage from " + Setup.__conf["cfg_path"])
                else:
                    _LOG.debug("Skip loading custom text over tcp response wait flag as it has not been changed during setup. \
The Default value of " + str(Setup.get("tcp_text_response_wait")) + " will be used")

                if "tcp_text_terminator" in configfile:
                    Setup.__conf["tcp_text_terminator"] = configfile["tcp_text_terminator"]
                    _LOG.info("Loaded custom text over tcp command terminator " + repr(configfile["tcp_text_terminator"]) + " \
into runtime storage from " + Setup.__conf["cfg_path"])
                else:
                    _LOG.debug("Skip loading custom text over tcp command terminator as it has not been changed during setup. \
The Default value of " + repr(Setup.get("tcp_text_terminator")) + " will be used")

                if "rq_user_agent" in configfile:
                    Setup.__conf["rq_user_agent"] = configfile["rq_user_agent"]
                    _LOG.info("Loaded custom http requests user agent " + str(configfile["rq_user_agent"]) + " into runtime storage from " + Setup.__conf["cfg_path"])
                else:
                    _LOG.debug("Skip loading custom http requests user agent as it has not been changed during setup. \
The Default user agent " + str(Setup.get("rq_user_agent")) + " will be used")

                if "rq_timeout" in configfile:
                    Setup.__conf["rq_timeout"] = configfile["rq_timeout"]
                    _LOG.info("Loaded custom http requests timeout of " + str(configfile["rq_timeout"]) + " seconds into runtime storage from " + Setup.__conf["cfg_path"])
                else:
                    _LOG.debug("Skip loading custom http requests timeout as it has not been changed during setup. \
The Default value of " + str(Setup.get("rq_timeout")) + " seconds will be used")

                if "rq_ssl_verify" in configfile:
                    Setup.__conf["rq_ssl_verify"] = configfile["rq_ssl_verify"]
                    _LOG.info("Loaded custom http ssl verification: " + str(configfile["rq_ssl_verify"]) + " into runtime storage from " + Setup.__conf["cfg_path"])
                else:
                    _LOG.debug("Skip loading http ssl verification flag as it has not been changed during setup. \
The Default value " + str(Setup.get("rq_ssl_verify")) + " will be used")

                if "rq_fire_and_forget" in configfile:
                    Setup.__conf["rq_fire_and_forget"] = configfile["rq_fire_and_forget"]
                    _LOG.info("Loaded custom fire_and_forget: " + str(configfile["rq_fire_and_forget"]) + " flag into runtime storage from " + Setup.__conf["cfg_path"])
                else:
                    _LOG.debug("Skip loading fire_and_forget as it has not been changed during setup. \
The Default value " + str(Setup.get("rq_fire_and_forget")) + " will be used")

                if "rq_response_regex" in configfile:
                    Setup.__conf["rq_response_regex"] = configfile["rq_response_regex"]
                    _LOG.info("Loaded rq_response_regex: " + str(configfile["rq_response_regex"]) + " flag into runtime storage from " + Setup.__conf["cfg_path"])
                else:
                    _LOG.debug("No regular expression has not been set during setup. The complete http request response will be sent to the http request response sensor")

                if "custom_entities_set" in configfile:
                    Setup.__conf["custom_entities_set"] = configfile["custom_entities_set"]
                    _LOG.info("Loaded custom_entities_set: " + str(configfile["custom_entities_set"]) + " flag into runtime storage from " + Setup.__conf["cfg_path"])
                else:
                    _LOG.debug("Skip loading custom_entities_set as no custom configuration has been set during setup.")

        else:
            _LOG.info(Setup.__conf["cfg_path"] + " does not exist (yet). Please start the setup process")

        yaml_path = Setup.__conf["yaml_path"]
        if os.path.isfile(yaml_path):
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    Setup._custom_entities = safe_load(f)
                if Setup.__conf["custom_entities_set"] is True:
                    #Only show a log message if custom entities have been configured by the user
                    _LOG.info("Loaded custom entities from " + yaml_path + " as Python dict into runtime storage")
            except Exception as e:
                raise OSError(f"Error while reading {yaml_path}") from e
        else:
            _LOG.error(f"{yaml_path} does not exist. Custom entities could not be loaded.")
