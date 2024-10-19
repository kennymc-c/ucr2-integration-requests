# HTTP Requests & Wake on LAN Integration for Unfolded Circle Remote Devices

## ⚠️ Disclaimer ⚠️

This software may contain bugs that could affect system stability. Please use it at your own risk!

##

Integration for Unfolded Circle Remote Devices running [Unfolded OS](https://www.unfoldedcircle.com/unfolded-os) (currently [Remote Two](https://www.unfoldedcircle.com/remote-two) and the upcoming [Remote 3](https://www.unfoldedcircle.com)) to send http requests and wake-on-lan magic packets.

Using [uc-integration-api](https://github.com/aitatoi/integration-python-library), [requests](https://github.com/psf/requests), [pywakeonlan](https://github.com/remcohaszing/pywakeonlan) and [getmac](https://github.com/GhostofGoes/getmac).

### Supported features

- Send http get, post, patch, put, delete & head requests to a specified url
  - Add form, json or xml payload (see [adding payload data](#adding-payload-data))
  - Define a global custom timeout (default is 2 seconds)
  - Deactivate ssl/tls verification for self signed certificates
  - Option to ignore HTTP requests errors and always return a OK/200 status code to the remote. Helpful if the server doesn't send any response or closes the connection after a command is received (fire and forget). The error message will still be logged but at debug instead of error level
- Send wake-on-lan magic packets to a specified mac address, ip (v4/v6) or hostname (ipv4 only)
  - Discover the mac address from an ip address or a hostname is not supported when running the integration on the remote due to sandbox limitations and may not work on all systems. Please refer to the [getmac supported platforms](https://github.com/GhostofGoes/getmac?tab=readme-ov-file#platforms-currently-supported)

### Planned features

- Support for custom http headers

Additional smaller planned improvements are labeled with #TODO in the code

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

If you activate the option to ignore HTTP requests errors in the integration setup a OK/200 status code will always be returned to the remote (fire and forget). This can be helpful if the requested server/device needs longer than the set timeout to wake up from deep sleep, generally doesn't send any response at all or closes the connection after a command is received. The error message will still be logged but at debug instead of error level.

#### Adding payload data

Optional payload data can be added to the request body with a specific separator charter

| Content type                      | Separator     | Example                                                      | Notes |
|-----------------------------------|---------------|--------------------------------------------------------------|-------|
| `application/x-www-form-urlencoded` | `§` (paragraph) |  `https://httpbin.org/post§key1=value1,key2=value2`            | Multiple values for a single key are currently not supported. |
| `application/json`                 | `\|` (pipe)     |  `https://httpbin.org/post\|{"key1":"value1","key2":"value2"}` | |
| `application/xml`                   | `^` (caret)     |  `https://httpbin.org/post^<Tests Id="01"><Test TestId="01"><Name>Command name</Name></Test></Tests>` | |

#### Only one payload type per requests is supported

If your actual url contains one or more of the above separators or other special characters that are not url reserved control characters you need to url-encode them first (e.g. with <https://www.urlencoder.io>)

## Installation

### Run on the remote as a custom integration driver

*⚠️ This feature is currently only available in beta firmware releases and requires version 1.9.2 or newer. Please keep in mind that due to the beta status there are missing firmware features that require workarounds (see below) and that changes in future beta updates may temporarily or permanently break the functionality of this integration as a custom integration. Please wait until custom integrations are available in stable firmware releases if you don't want to take these risks.*

#### Missing firmware features

- The configuration file of custom integrations are not included in backups.
- You currently can't update custom integrations. You need to delete the integration from the integrations menu first and then re-upload the new version. Do not edit any activity or macros that includes entities from this integration after you removed the integration and wait until the new version has been uploaded and installed. You also need to add re-add entities to the main pages after the update as they are automatically removed. An update function will probably be added once the custom integrations feature will be available in stable firmware releases.

#### Download integration driver

Download the uc-intg-requests-x.x.x-aarch64.tar.gz archive in the assets section from the [latest release](https://github.com/kennymc-c/ucr2-integration-requests/releases/latest)

#### Install custom integration driver on the remote

The custom integration driver installation is currently only possible via the Core API.

```shell
curl --location 'http://$IP/api/intg/install' \
--user 'web-configurator:$PIN' \
--form 'file=@"uc-intg-requests-$VERSION-aarch64.tar.gz"'
```

There is also a Core API GUI available at https://[Remote-IP]/doc/core-rest/. Scroll down to POST intg/install and click on Try it out, choose a file and then click on Execute.

UC plans to integrate the upload function to the web configurator once they get enough positive feedback from developers (and users). The current status can be tracked in this issue: [#79](https://github.com/unfoldedcircle/feature-and-bug-tracker/issues/79).

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
