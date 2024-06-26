import json
import os
import logging

_LOG = logging.getLogger(__name__)

CFG_FILENAME = "config.json"


class setup:
    __conf = {
    "standby": False,
    "setup_complete": False,
    "setup_reconfigure": False,
    "rq_timeout": 2,
    "rq_ssl_verify": True,
    "id-get": "http-get",
    "name-get": "HTTP Get",
    "id-post": "http-post",
    "name-post": "HTTP Post",
    "id-patch": "http-patch",
    "name-patch": "HTTP Patch",
    "id-put": "http-put",
    "name-put": "HTTP Put",
    "id-wol": "wol",
    "name-wol": "Wake on LAN"
    }
    __setters = ["standby", "setup_complete", "setup_reconfigure", "rq_timeout", "rq_ssl_verify"]
    __storers = ["setup_complete", "rq_timeout", "rq_ssl_verify"] #Skip runtime only related values in config file
    all_cmds = ["get", "post", "patch", "put", "wol"]
    rq_ids = [__conf["id-get"], __conf["id-post"], __conf["id-patch"], __conf["id-put"]]
    rq_names = [__conf["name-get"], __conf["name-post"], __conf["name-patch"], __conf["name-put"]]
    
    @staticmethod
    def get(key):
        if setup.__conf[key] != "":
            return setup.__conf[key]
        else:
            _LOG.error("Got empty value for " + key + " from config storage")

    @staticmethod
    def set(key, value):

        if key in setup.__setters:
            if setup.__conf["setup_reconfigure"] == True and key == "setup_complete":
                _LOG.debug("Ignore setting and storing setup_complete flag during reconfiguration")
            else:
                setup.__conf[key] = value
                _LOG.debug("Stored " + key + ": " + str(value) + " into runtime storage")

                #Store key/value pair in config file
                if key in setup.__storers:
                        
                    jsondata = {key: value}
                    if os.path.isfile(CFG_FILENAME):
                            try:
                                with open(CFG_FILENAME, "r+") as f:
                                    l = json.load(f)
                                    l.update(jsondata)
                                    f.seek(0)
                                    f.truncate() #Needed when the new value has less characters than the old value (e.g. false to true or 11 to 5 seconds timeout)
                                    json.dump(l, f)
                                    f.close
                                    _LOG.debug("Stored " + key + ": " + str(value) + " into " + CFG_FILENAME)
                            except OSError as o:
                                raise Exception(o)
                            except:
                                raise Exception("Error while storing " + key + ": " + str(value) + " into " + CFG_FILENAME)

                    #Create config file first if it doesn't exists yet
                    else:
                        try:
                            with open(CFG_FILENAME, "w") as f:
                                json.dump(jsondata, f)
                                f.close
                            _LOG.debug("Created " + CFG_FILENAME + " and stored " + key + ": " + str(value) + " in it")
                        except OSError as o:
                            raise Exception(o)
                        except:
                            raise Exception("Error while storing " + key + ": " + str(value) + " into " + CFG_FILENAME)
                        
                else:
                    _LOG.debug(key + " not found in __storers because it should not be stored in the config file")

        else:
            raise NameError(key + " not found in __setters because it should not be changed")
        
    @staticmethod
    def load():
        if os.path.isfile(CFG_FILENAME):

            try:
                with open(CFG_FILENAME, "r") as f:
                    configfile = json.load(f)
            except:
                raise OSError("Error while reading " + CFG_FILENAME)
            if configfile == "":
                raise OSError("Error in " + CFG_FILENAME + ". No data")

            setup.__conf["setup_complete"] = configfile["setup_complete"]
            _LOG.debug("Loaded setup_complete: " + str(configfile["setup_complete"]) + " into runtime storage from " + CFG_FILENAME)

            if not setup.__conf["setup_complete"]:
                _LOG.warning("The setup was not completed the last time. Please restart the setup process")
            else:
                if "rq_timeout" in configfile:
                    setup.__conf["rq_timeout"] = configfile["rq_timeout"]
                    _LOG.info("Loaded requests timeout of " + str(configfile["rq_timeout"]) + " seconds into runtime storage from " + CFG_FILENAME)
                else:
                    _LOG.info("Skip loading custom requests timeout as it has not been changed during setup. Default value of " + str(setup.get("rq_timeout")) + " seconds will be used")

                if "rq_ssl_verify" in configfile:
                    setup.__conf["rq_ssl_verify"] = configfile["rq_ssl_verify"]
                    _LOG.info("Loaded http ssl verification: " + str(configfile["rq_ssl_verify"]) + " into runtime storage from " + CFG_FILENAME)
                else:
                    _LOG.info("Skip loading http ssl verification flag as it has not been changed during setup. Default value " + str(setup.get("rq_ssl_verify")) + " will be used")

        else:
            _LOG.info(CFG_FILENAME + " does not exist (yet). Please start the setup process")