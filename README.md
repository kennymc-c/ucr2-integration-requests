# A network multi tool integration for Unfolded Circle Remote Devices <!-- omit in toc -->

## ⚠️ Disclaimer ⚠️  <!-- omit in toc -->

This software may contain bugs that could affect system stability. Please use it at your own risk!

## <!-- omit in toc -->

Integration for Unfolded Circle Remote Devices running [Unfolded OS](https://www.unfoldedcircle.com/unfolded-os) (currently Remote Two and [Remote 3](https://www.unfoldedcircle.com)) to send http requests, wake-on-lan magic packets and text over TCP.

Using [uc-integration-api](https://github.com/aitatoi/integration-python-library), [requests](https://github.com/psf/requests), [pywakeonlan](https://github.com/remcohaszing/pywakeonlan), [getmac](https://github.com/GhostofGoes/getmac) and [pyyaml](https://github.com/yaml/pyyaml).

- [Supported entity features](#supported-entity-features)
- [Configuration](#configuration)
- [Usage](#usage)
  - [1 - Wake-on-lan](#1---wake-on-lan)
    - [Supported parameters](#supported-parameters)
  - [2 - HTTP requests](#2---http-requests)
    - [Expected http request server response code](#expected-http-request-server-response-code)
    - [Additional command parameters](#additional-command-parameters)
    - [SSL verification \& Fire and forget mode](#ssl-verification--fire-and-forget-mode)
    - [Use case examples](#use-case-examples)
    - [Show (parts) of the server response text in the remote ui](#show-parts-of-the-server-response-text-in-the-remote-ui)
  - [3 - Text over TCP](#3---text-over-tcp)
    - [Wait for a response message](#wait-for-a-response-message)
    - [Control characters](#control-characters)
      - [Escaping](#escaping)
  - [4 - Custom Entities](#4---custom-entities)
    - [⚠️ Important](#️-important)
    - [Example yaml configuration](#example-yaml-configuration)
    - [Using variables](#using-variables)
      - [Example](#example)
- [Installation](#installation)
  - [Run on the remote as a custom integration driver](#run-on-the-remote-as-a-custom-integration-driver)
    - [Limitations / Disclaimer](#limitations--disclaimer)
      - [Missing firmware features](#missing-firmware-features)
    - [1 - Download integration driver](#1---download-integration-driver)
    - [2 - Upload \& installation](#2---upload--installation)
      - [Upload in Web Configurator](#upload-in-web-configurator)
      - [Alternative - Upload via Core API or 3rd party tools](#alternative---upload-via-core-api-or-3rd-party-tools)
  - [Run on a separate device as an external integration driver](#run-on-a-separate-device-as-an-external-integration-driver)
    - [Bare metal/VM](#bare-metalvm)
      - [Requirements](#requirements)
      - [Start the integration](#start-the-integration)
    - [Docker container](#docker-container)
- [Build](#build)
  - [Build distribution binary](#build-distribution-binary)
    - [x86-64 Linux](#x86-64-linux)
    - [aarch64 Linux / Mac](#aarch64-linux--mac)
  - [Create tar.gz archive](#create-targz-archive)
- [Versioning](#versioning)
- [Changelog](#changelog)
- [Contributions](#contributions)
- [License](#license)

## Supported entity features

- Send http get, post, patch, put, delete & head requests to a specified url
  - Add [additional command parameters]((#additional-command-parameters))
  - Option to ignore HTTP requests errors and always return a OK/200 status code to the remote
    - Helpful if the server doesn't send any response or closes the connection after a command is received (fire and forget). The error message will still be logged but at debug instead of error level
- Send wake-on-lan magic packets to one or more mac addresses, ips (v4/v6) or hostnames (ipv4 only)
  - [Supported parameters](#supported-parameters)
  - Discover the mac address from an ip address or a hostname
    - Not supported when running the integration on the remote due to sandbox limitations and may not work on all systems. Please refer to the [getmac supported platforms](https://github.com/GhostofGoes/getmac?tab=readme-ov-file#platforms-currently-supported)
- Send text over TCP
  - This method can be used with some home automation systems, tools like [win-remote-control](https://github.com/moefh/win-remote-control) or for protocols like PJLink (used by a lot of projector brands like JVC, Epson or Optoma)
  - Support for c++ and hex style control characters (e.g. new line, carriage return, tabulator etc.)
  - The default timeout can be changed in the advanced setup settings

## Configuration

During the integration setup you can turn on the advanced settings to change various timeouts and others entity related settings (see [Usage](#usage)). You can run the setup process again in the integration settings to change these settings after adding entities to the remote.

For http requests it's also possible to temporally overwrite one or more settings for a specific command by adding [additional command parameters](#additional-command-parameters).

## Usage

The integration exposes a media player entity for each supported command. These entities only support the source feature. Just enter the needed data for the chosen entity (see below) in the source field after adding the input source command to your activity/macro sequence, user interface or button mapping.

This is an example for the text over TCP entity but it should explain the workflow of this integration:

https://github.com/user-attachments/assets/fb795db5-8f1f-4601-8e21-0f69d1a57e4d

Additionally you can configure custom entities that can include simple commands as well as separate on/off/toggle commands that will change the state of the entity. More details can be found below.

### 1 - Wake-on-lan

Enter the desired hostname, mac or ip address (ipv4/v6). Multiple addresses can be separated by a comma.

*Note: When running as a custom integration on the remote itself only mac addresses are supported.*

#### Supported parameters

All parameters from [pywakeonlan](https://github.com/remcohaszing/pywakeonlan) are supported (interface=, port=, ip_address=)

### 2 - HTTP requests

Enter the desired url (including http(s)://). Additional parameters can be added (see below).

#### Expected http request server response code

Your server needs to respond with a *200 OK* status or any other informational or redirection http status code (100s, 200s or 300s). If the server's response content is not empty it will be shown in the integration log. In case of a client or server error (400s or 500s) the command will fail on the remote and the error message and status code will be shown in the integration log.

If you activate the fire and forget mode the remote will always receive a *200 OK* status code (see below).

#### Additional command parameters

Almost all parameters from the Python requests module like `timeout`, `verify`, `data`, `json` or `headers` are supported (see [Python requests module parameters](https://requests.readthedocs.io/en/latest/api/#requests.request)) although not all of them have been tested with this integration. Simply separate them with a comma.

When using one or more parameters you need to use the `url` parameter for the url itself as well. If a parameter value contains commas, equal signs or quotes put it in double quotes and use single quotes inside (see examples below).

#### SSL verification & Fire and forget mode

When using a self signed ssl certificate you can globally deactivate ssl cert verification in the advanced setup or temporally for specific commands by using `verify=False` as a command parameter.

If you activate the option to ignore HTTP requests errors in the integration setup or by adding `ffg=True` as a command parameter a OK/200 status code will always be returned to the remote (fire and forget). This can be helpful if the requested server/device needs longer than the set timeout to wake up from deep sleep, generally doesn't send any response at all or closes the connection after a command is received. The error message will still be logged but at debug instead of error level.

#### Use case examples

*Note: Booleans in json data have to be written in Python style with an upper case first letter (True / False). They automatically get back converted to a valid lower case json boolean.*

| Use Case                     | Parameters     | Example                                                      |
|-----------------------------------|---------------|--------------------------------------------------------------|
| Temporally use a different timeout and activate fire and forget mode | `timeout` and `ffg`  |  `url="https://httpbin.org/get", timeout=5, ffg=True`  |
| Adding form payload data` | `data`  |  `url="https://httpbin.org/post", data="key1=value1,key2=value2"`  |
| Adding json payload data (content type is set automatically)                 | `json`    |  `url="https://httpbin.org/post", json="{'key1':'value1','key2':'value2'}"` |
| Adding xml payload data                   | `data` and `headers` |  `url="https://httpbin.org/post", data="<Tests Id='01'><Test TestId='01'><Name>Command name</Name></Test></Tests>", headers="{'Content-Type':'application/xml'}"` |

#### Show (parts) of the server response text in the remote ui

The integration exposes a sensor entity that shows the text of the response body from the last executed http request command. Responses are also used for the media_title attribute of the associated request method's media player entity. This allows you to add a media player widget to an activity and see the response within an activity because you can't add sensors to activities as there's no widget for them. If the sensor entity has not been added as a configured entity in the web configurator a info message will be shown in the integration log.

The output can be parsed to only show a specific part of the response message using regular expressions. These can be configured in the advanced setup. Sites like [regex101.com](https://regex101.com) or the AI model of your choice can help you with finding matching expressions. By default the complete response message will be used if no regular expression has been set or no matches have been found. The advanced setup has an option to use an empty response or show an error message instead if no match has been found.

### 3 - Text over TCP

This method can be used with some home automation systems, tools like [win-remote-control](https://github.com/moefh/win-remote-control) or for certain protocols like [PJLink](https://pjlink.jbmia.or.jp/english/index.htmlPJLink) (used by a lot of projector brands like JVC, Epson or Optoma)

- Generic Example: 192.168.1.1:1234, "Hello World"
- PJLink Power On Example: 192.168.1.1:4352,"%1POWR 1\r"
  - Other PJLink commands can be found in the [PJLink command descriptions](https://pjlink.jbmia.or.jp/english/data_cl2/PJLink_5-1.pdf) (from page 17)

#### Wait for a response message

By default the integration waits for a response message from the server/device and raises a timeout error if no response has been received in the configured time frame. You can change this behavior in the advanced settings if your device is not sending any response message.

#### Control characters

C++ and hex style control characters are supported to e.g. add a new line (\\n or 0x0A), tab (\\t or 0x09) or a carriage return (\\r or 0x0D)

##### Escaping

- C++ style characters can be escaped with a single additional backslash (e.g. \\\n)
- Hex style characters can be escaped with "0\\\\\\" (e.g. 0\\\\\\0x09)

### 4 - Custom Entities

If you want to have a separate entities e.g. for different devices with pre-defined simple commands as well as separate on/off/toggle commands with power state handling you can configure them in the custom entity configuration during the integration setup. This will expose a remote entity for each configured entity with all features and commands from the configuration.

The configuration is in the YAML format and contains different levels to define each entity with it's own remote entity features (on/off/toggle) and optional simple commands. Each command can be any type of supported command by this integration. Parameters for these commands can also be specified. You can find an example configuration below.

Each sub level is separated with a tab. As tabs can't be entered in the web configurator text field you need to either copy it from a text edit program or use 2 spaces instead. Simple command names can be up to 20 characters long, need to be in upper case and can only contain ```A-Z```, ```a-z```, ```0-9``` and ```/_.:+#*°@%()?-```. These names get automatically corrected and shortened during setup if they don't meet the requirements. Any non allowed character gets replaced with an underscore (```_```). If you add new commands or features to an existing entity you need to remove and re-add the entity from the configured entity list afterwards.

If you removed an entity from the configuration file it doesn't get automatically removed from your configured entities. You have to do this manually. If you restart the integration they will also be shown as unavailable.

#### ⚠️ Important

- Please backup your configuration somewhere else if you're running the integration as a custom integration on the remote as custom integrations are not yet included in the remote backup file
- The name for the ```On``` and ```Off``` features have to be written in quotes as they get converted into boolean values otherwise

#### Example yaml configuration

```yaml
Entity1:
  Features:
    'Off':
      Type: get
      Parameter: 192.168.1.102/api/commands/off
    'On':
      Type: wol
      Parameter:
        address:
        - ec:bd:d4:01:e9:39
        - 88:59:b7:25:b9:a5
        port: 12345
        interface: 192.168.1.1
    Toggle:
      Type: get
      Parameter: 192.168.1.102/api/commands/toggle
  Simple Commands:
    INPUT_1:
      Type: post
      Parameter:
        url: https://httpbin.org/post
        json:
          command: input
          number: 1
    MENU:
      Type: tcp-text
      Parameter:
        address: 192.168.1.101:12345
        text: menu\r
```

#### Using variables

To make your configuration more flexible you can also define your own varibales in a special ```_vars``` block. Recalling them works by using ${varaible_name}

##### Example

```yaml
_vars:
  entity1_api_url: http://192.168.1.101/api/commands

Entity1:
  Features:
    'Off':
      Type: get
      Parameter: ${entitiy1_api_url}/off
```

## Installation

### Run on the remote as a custom integration driver

#### Limitations / Disclaimer

*⚠️ This requires firmware version 1.9.2 or newer (installing firmware versions above 1.7.14 for Remote Two currently need beta updates to be enabled).*

##### Missing firmware features

- The configuration file of custom integrations are not included in backups.
- You currently can't update custom integrations.
  - As a workaround you first need to delete the integration twice until it's not shown anymore on the integration page and then re-upload and re-configure the new version
  - Do not remove any entities exposed by this integration from any activity or macro after you removed the integration and wait until the new version has been uploaded and configured again
  - You may also need to re-add entities to the main pages after the update as they are automatically removed. Your activities and macros will stay the same and will not need any reconfiguration.

#### 1 - Download integration driver

Download the uc-intg-requests-x.x.x-aarch64.tar.gz archive in the assets section from the [latest release](https://github.com/kennymc-c/ucr2-integration-requests/releases/latest).

#### 2 - Upload & installation

##### Upload in Web Configurator

Since firmware version 2.2.0 you can upload custom integrations in the web configurator. Go to *Integrations* in the top menu, on the top right click on *Add new/Install custom_ and choose the downloaded tar.gz file.

##### Alternative - Upload via Core API or 3rd party tools

```shell
curl --location 'http://$IP/api/intg/install' \
--user 'web-configurator:$PIN' \
--form 'file=@"uc-intg-sonysdcp-$VERSION-aarch64.tar.gz"'
```

There is also a Core API GUI available at https://*Remote-IP*/doc/core-rest. Click on Authorize to log in (username: web-configurator, password: your PIN), scroll down to POST intg/install, click on Try it out, choose a file and then click on Execute.

Alternatively you can also use the inofficial [UC Remote Toolkit](https://github.com/albaintor/UC-Remote-Two-Toolkit)

### Run on a separate device as an external integration driver

#### Bare metal/VM

##### Requirements

- Python 3.11
- Install Libraries:  
  (using a [virtual environment](https://docs.python.org/3/library/venv.html) is highly recommended)

```shell
pip3 install -r requirements.txt
```

##### Start the integration

```shell
python3 intg-requests/driver.py
```

#### Docker container

For the mDNS advertisement to work correctly it's advised to start the integration in the host network (`--net=host`). You can also set the websocket listening port with the environment variable `UC_INTEGRATION_HTTP_PORT`, set the listening interface with `UC_INTEGRATION_INTERFACE` or change the default debug log level with `UC_LOG_LEVEL`. See available [environment variables](https://github.com/unfoldedcircle/integration-python-library#environment-variables)
in the Python integration library.

All data is mounted to `/usr/src/app`:

```shell
docker run --net=host -n 'ucr2-integration-requests' -v './ucr2-integration-requests':'/usr/src/app/':'rw' 'python:3.11' /usr/src/app/docker-entry.sh
```

## Build

Instead of downloading the integration driver archive from the release assets you can also build and create the needed distribution binary and tar.gz archive yourself.

For Python based integrations Unfolded Circle recommends to use `pyinstaller` to create a distribution binary that has everything in it, including the Python runtime and all required modules and native libraries.

### Build distribution binary

First we need to compile the driver on the target architecture because `pyinstaller` does not support cross compilation.

The `--onefile` option to create a one-file bundled executable should be avoided:

- Higher startup cost, since the wrapper binary must first extract the archive.
- Files are extracted to the /tmp directory on the device, which is an in-memory filesystem.  
  This will further reduce the available memory for the integration drivers!

We use the `--onedir` option instead.

#### x86-64 Linux

On x86-64 Linux we need Qemu to emulate the aarch64 target platform:

```bash
sudo apt install qemu binfmt-support qemu-user-static
docker run --rm --privileged multiarch/qemu-user-static --reset -p yes
```

Run pyinstaller:

```shell
docker run --rm --name builder \
    --platform=aarch64 \
    --user=$(id -u):$(id -g) \
    -v "$PWD":/workspace \
    docker.io/unfoldedcircle/r2-pyinstaller:3.11.6-0.2.0  \
    bash -c \
      "cd /workspace && \
      python -m pip install -r requirements.txt && \
      pyinstaller --clean --onedir --name int-requests intg-requests/driver.py"
```

#### aarch64 Linux / Mac

On an aarch64 host platform, the build image can be run directly (and much faster):

```shell
docker run --rm --name builder \
    --user=$(id -u):$(id -g) \
    -v "$PWD":/workspace \
    docker.io/unfoldedcircle/r2-pyinstaller:3.11.6-0.2.0  \
    bash -c \
      "cd /workspace && \
      python -m pip install -r requirements.txt && \
      pyinstaller --clean --onedir --name intg-requests intg-requests/driver.py"
```

### Create tar.gz archive

Now we need to create the tar.gz archive that can be installed on the remote and contains the driver.json metadata file and the driver distribution binary inside the bin directory

```shell
mkdir -p artifacts/bin
mv dist/intg-requests/* artifacts/bin
mv artifacts/bin/intg-requests artifacts/bin/driver
cp driver.json artifacts/
tar czvf uc-intg-requests-aarch64.tar.gz -C artifacts .
rm -r dist build artifacts intg-requests.spec
```

## Versioning

I use [SemVer](http://semver.org/) for versioning. For the versions available, see the
[tags and releases in this repository](/releases).

## Changelog

The major changes found in each new release are listed in the [changelog](CHANGELOG.md)
and under the GitHub [releases](/releases).

## Contributions

Contributions to add new feature, implement #TODOs from the code or improve the code quality and stability are welcome! First check whether there are other branches in this repository that maybe already include your feature. If not, please fork this repository first and then create a pull request to merge your commits and explain what you want to change or add.

## License

This project is licensed under the [**GNU GENERAL PUBLIC LICENSE**](https://choosealicense.com/licenses/gpl-3.0/).
See the [LICENSE](LICENSE) file for details.
