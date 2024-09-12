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
        "rq_timeout": 2,
        "rq_ssl_verify": True,
        "rq_user_agent": "uc-intg-requests",
        "rq_fire_and_forget": False,
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
        "name-wol": "Wake on LAN"
    }
    __setters = ["standby", "setup_complete", "setup_reconfigure", "rq_timeout", "rq_ssl_verify", "rq_fire_and_forget", "bundle_mode", "cfg_path"]
    __storers = ["setup_complete", "rq_timeout", "rq_ssl_verify", "rq_fire_and_forget"] #Skip runtime only related values in config file

    all_cmds = ["get", "post", "patch", "put", "delete", "head", "wol"]
    rq_ids = [__conf["id-get"], __conf["id-post"], __conf["id-patch"], __conf["id-put"], __conf["id-delete"], __conf["id-head"]]
    rq_names = [__conf["name-get"], __conf["name-post"], __conf["name-patch"], __conf["name-put"], __conf["name-delete"], __conf["name-head"]]

    @staticmethod
    def get(key):
        """Get the value from the specified key in __conf"""
        if Setup.__conf[key] == "":
            raise ValueError("Got empty value for " + key + " from config storage")
        return Setup.__conf[key]


    @staticmethod
    def set(key, value):
        """Set and store a value for the specified key into the runtime storage and config file.
        Storing setup_complete flag during reconfiguration will be ignored"""
        if key in Setup.__setters:
            if Setup.__conf["setup_reconfigure"] is True and key == "setup_complete":
                _LOG.debug("Ignore setting and storing setup_complete flag during reconfiguration")
            else:
                Setup.__conf[key] = value
                _LOG.debug("Stored " + key + ": " + str(value) + " into runtime storage")

                #Store key/value pair in config file
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
                if "rq_timeout" in configfile:
                    Setup.__conf["rq_timeout"] = configfile["rq_timeout"]
                    _LOG.info("Loaded requests timeout of " + str(configfile["rq_timeout"]) + " seconds into runtime storage from " + Setup.__conf["cfg_path"])
                else:
                    _LOG.info("Skip loading custom requests timeout as it has not been changed during setup. \
                    Default value of " + str(Setup.get("rq_timeout")) + " seconds will be used")

                if "rq_ssl_verify" in configfile:
                    Setup.__conf["rq_ssl_verify"] = configfile["rq_ssl_verify"]
                    _LOG.info("Loaded http ssl verification: " + str(configfile["rq_ssl_verify"]) + " into runtime storage from " + Setup.__conf["cfg_path"])
                else:
                    _LOG.info("Skip loading http ssl verification flag as it has not been changed during setup. \
                    Default value " + str(Setup.get("rq_ssl_verify")) + " will be used")

                if "rq_fire_and_forget" in configfile:
                    Setup.__conf["rq_fire_and_forget"] = configfile["rq_fire_and_forget"]
                    _LOG.info("Loaded fire_and_forget: " + str(configfile["rq_fire_and_forget"]) + " into runtime storage from " + Setup.__conf["cfg_path"])
                else:
                    _LOG.info("Skip loading fire_and_forget as it has not been changed during setup. \
                    Default value " + str(Setup.get("rq_fire_and_forget")) + " will be used")

        else:
            _LOG.info(Setup.__conf["cfg_path"] + " does not exist (yet). Please start the setup process")
