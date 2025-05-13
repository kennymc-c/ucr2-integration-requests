"""This module contains some fixed variables, the Setup class which includes all fixed and customizable variables"""

import json
import os
import logging

_LOG = logging.getLogger(__name__)



class Setup:
    """Setup class which includes all fixed and customizable variables including functions to set() and get() them from a runtime storage
    which includes storing them in a json config file and as well as load() them from this file"""

    __conf = {
        "standby": False,
        "setup_complete": False,
        "setup_reconfigure": False,
        "bundle_mode": False,
        "cfg_path": "config.json",
        "tcp_text_timeout": 2,
        "rq_timeout": 2,
        "rq_ssl_verify": True,
        "rq_user_agent": "uc-intg-requests",
        "rq_fire_and_forget": False,
        "rq_legacy": False,
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
                        },
    }
    __setters = ["standby", "setup_complete", "setup_reconfigure", "tcp_text_timeout", "rq_timeout", "rq_user_agent", "rq_ssl_verify", \
                 "rq_fire_and_forget", "rq_legacy", "rq_response_regex", "rq_response_nomatch_option", "bundle_mode", "cfg_path"]
    #Skip runtime only related values in config file
    __storers = ["setup_complete", "tcp_text_timeout", "rq_timeout", "rq_user_agent", "rq_ssl_verify", "rq_fire_and_forget", "rq_legacy", \
    "rq_response_regex", "rq_response_nomatch_option"]

    all_cmds = ["get", "post", "patch", "put", "delete", "head", "wol", "tcp-text"]
    rq_ids = [__conf["id-rq-sensor"], __conf["id-get"], __conf["id-post"], __conf["id-patch"], __conf["id-put"], __conf["id-delete"], __conf["id-head"]]
    rq_names = [__conf["name-rq-sensor"], __conf["name-get"], __conf["name-post"], __conf["name-patch"], __conf["name-put"], __conf["name-delete"], __conf["name-head"]]

    @staticmethod
    def get(key):
        """Get the value from the specified key in __conf"""
        if Setup.__conf[key] == "" and key != "rq_response_regex": #rq_response_regex can be empty
            raise ValueError("Got empty value for " + key + " from config storage")
        return Setup.__conf[key]


    @staticmethod
    def set(key, value):
        """Save a value for the specified key into the runtime storage and store some of them into the config file.
        Saving and storing setup_complete flag during reconfiguration will be ignored as well as storing values that have not been changed from the default"""
        if key in Setup.__setters:
            if Setup.__conf["setup_reconfigure"] is True and key == "setup_complete":
                _LOG.debug("Ignore saving and storing setup_complete flag during reconfiguration")
            else:
                skip_store = False
                if key in Setup.__storers and value == Setup.__conf[key]:
                    skip_store = True
                    _LOG.debug("Skip storing " + key + ": " + str(value) + " into config file as it has not been changed from the default value of " + str(Setup.__conf[key]))

                Setup.__conf[key] = value
                _LOG.debug("Saved " + key + ": " + str(value) + " into runtime storage")

                #Store key/value pair in config file
                if skip_store is False:
                    if key in Setup.__storers:
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
        """Load all variables from the config json file into the runtime storage"""
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

                if "rq_legacy" in configfile:
                    Setup.__conf["rq_legacy"] = configfile["rq_legacy"]
                    _LOG.info("Loaded rq_legacy: " + str(configfile["rq_legacy"]) + " flag into runtime storage from " + Setup.__conf["cfg_path"])
                else:
                    _LOG.info("Using the default http requests syntax as it has not been changed during setup. \
The Default value " + str(Setup.get("rq_legacy")) + " will be used")

                if "rq_response_regex" in configfile:
                    Setup.__conf["rq_response_regex"] = configfile["rq_response_regex"]
                    _LOG.info("Loaded rq_response_regex: " + str(configfile["rq_response_regex"]) + " flag into runtime storage from " + Setup.__conf["cfg_path"])
                else:
                    _LOG.debug("No regular expression has not been set during setup. The complete http request response will be sent to the http request response sensor")

        else:
            _LOG.info(Setup.__conf["cfg_path"] + " does not exist (yet). Please start the setup process")
