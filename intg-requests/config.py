import logging

_LOG = logging.getLogger(__name__)



class setup:
    cmds = ["get", "post", "patch", "put", "wol"]

    __conf = {
    "standby": False,
    "rq-timeout": 2,
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
    __setters = ["standby"]

    @staticmethod
    def get(value):
        if setup.__conf[value] != "":
            return setup.__conf[value]
        else:
            _LOG.error("Got empty value from config storage")

    @staticmethod
    def set(key, value):
        if key in setup.__setters:
            setup.__conf[key] = value
            _LOG.debug("Stored " + key + ": " + str(value) + " into runtime storage")
        else:
            raise NameError("Name not accepted in set() method")
