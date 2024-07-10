# HTTP Get/Post/Put/Patch & Wake on LAN Integration for Unfolded Circle Remote Two and Remote 3

## ⚠️ WARNING ⚠️

### Disclaimer: This software may contain serious bugs that could affect system stability. Please use it at your own risk!

##

Integration for Unfolded Circle [Remote Two](https://www.unfoldedcircle.com/remote-two) and [Remote 3](https://www.unfoldedcircle.com) running [Unfolded OS](https://www.unfoldedcircle.com/unfolded-os) to send http requests and wake-on-lan magic packets.

Using [uc-integration-api](https://github.com/aitatoi/integration-python-library), [requests](https://github.com/psf/requests), [pywakeonlan](https://github.com/remcohaszing/pywakeonlan) and [getmac](https://github.com/GhostofGoes/getmac).


### Supported features

- Send http get, post, patch, put, delete & head requests to a specified url
  - Add form or json payload (see [adding payload data](#adding-payload-data))
  - Define a global custom timeout (default is 2 seconds)
  - Deactivate ssl/tls verification for self signed certificates
- Send Wake on LAN magic packets to a specified mac address, ip (v4/v6) or hostname (ipv4 only)
  - Discover the mac address from an ip address or a hostname may not work on all systems. Please refer to the [getmac supported platforms](https://github.com/GhostofGoes/getmac?tab=readme-ov-file#platforms-currently-supported)


### Planned features

- Support for sending raw payload data (e.g. xml) in the http request body

*Planned improvements are labeled with #TODO in the code*


## Configuration

During the integration setup you can change the default http request timeout of 2 seconds to a custom value. You also can deactivate the ssl certificate verification. This is needed for self signed ssl certificates. You can run the setup process again in the integration settings to change these settings after adding entities to the remote.

## Usage

The integration exposes a media player entity for each supported request command. These entities only support the source feature. Just enter the desired url (including http(s)://) or mac address in the source field when you configure your activity/macro sequences or activity ui.

### Wake-on-lan

Choose the Wake on lan entity from the integration setup and add it to an activity or macro. Enter the desired hostname, mac or ip address (ipv4/v6) in the source field when you configure your activity/macro sequence or activity ui.

### HTTP requests

Choose one or more HTTP request method entities from the integration setup and add it to an activity or macro. Enter the desired url (including http(s)://) in the source field when you configure your activity/macro sequences or activity ui.

#### Expected server response

For http requests your server needs to respond with a *200 OK* status or any other informational or redirection http status codes (100s, 200s or 300s). If the server's response content is not empty it will be shown in the integration log. In case of a client or server error (400s or 500s) the command will fail on the remote and the error message and status code will be shown in the integration log.

#### Adding payload data

Optional payload data can be added to the request body with a specific separator charter

| Content type                      | Separator     | Example                                                      | Notes |
|-----------------------------------|---------------|--------------------------------------------------------------|-------|
| `application/x-www-form-urlencoded` | `§` (paragraph) |  `https://httpbin.org/post§key1=value1,key2=value2`            | Multiple values for a single key are currently not supported. 
| `application/json `                 | `\|` (pipe)     |  `https://httpbin.org/post\|{"key1":"value1","key2":"value2"}` |
| `application/xml`                   | `^` (caret)     |  `https://httpbin.org/post^<Tests Id="01"><Test TestId="01"><Name>Command name</Name></Test></Tests>` |

**Only one payload type per requests is supported**

If your actual url contains one or more of the above separators or other special characters that are not url reserved control characters you need to url-encode them first (e.g. with https://www.urlencoder.io)

## Installation

### Run on the remote

#### Download integration

Download the tar.gz archive in the assets section from the [latest release](https://github.com/kennymc-c/ucr2-integration-requests/releases/latest)

#### Upload to the remote

TBA

### Run as an external integration on a separate server

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

For the mDNS advertisement (auto discovery of the integration) to work correctly and to be able to use wake-on-lan with an ip address or a hostname instead of a mac address the integration needs to be run in the host network (`--net=host`). You can also set the websocket listening port with the environment variable `UC_INTEGRATION_HTTP_PORT`, set the listening interface with `UC_INTEGRATION_INTERFACE` or change the default debug log level with `UC_LOG_LEVEL`. See available [environment variables](https://github.com/unfoldedcircle/integration-python-library#environment-variables)
in the Python integration library.

All data is mounted to `/usr/src/app`:

```shell
docker run --net=host -n 'ucr2-integration-requests' -v './ucr2-integration-requests':'/usr/src/app/':'rw' 'python:3.11' /usr/src/app/docker-entry.sh
```

## Build self-contained binary for Remote Two

*Note: Uploading custom integrations to the remote is not yet supported with the current firmware. The status can be tracked in this issue: [#79](https://github.com/unfoldedcircle/feature-and-bug-tracker/issues/79)*

Unfolded Circle recommends to create a single binary file that has everything in it as python on embedded systems is a nightmare.

To do that, we need to compile it on the target architecture as `pyinstaller` does not support cross compilation.

### x86-64 Linux

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
    docker.io/unfoldedcircle/r2-pyinstaller:3.11.6  \
    bash -c \
      "python -m pip install -r requirements.txt && \
      pyinstaller --clean --onefile --name intg-requests intg-requests/driver.py"
```

### aarch64 Linux / Mac

On an aarch64 host platform, the build image can be run directly (and much faster):

```shell
docker run --rm --name builder \
    --user=$(id -u):$(id -g) \
    -v "$PWD":/workspace \
    docker.io/unfoldedcircle/r2-pyinstaller:3.11.6  \
    bash -c \
      "python -m pip install -r requirements.txt && \
      pyinstaller --clean --onefile --name intg-requests intg-requests/driver.py"
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
