# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.7.3] - 2025-05-15

### Fixed

- Automatically close connection for text over TCP entity after the command has been send

### Added

- Added an text over tcp option to decide if a response message should be awaited. If the server doesn't send any response this should be deactivated to prevent potential timeouts

### Changed

- Updated pyinstaller build image to r2-pyinstaller:3.11.12-0.3.0
- Updated dependencies

## [0.7.2] - 2025-04-04

### Fixed

- Changed handling of an exception that could occur if the http response sensor was never added as a configured entity. Instead of an exception now only an info log message is shown.

### Added

- Added an option to change what should be shown in the http response sensor and media player title if no match has been found for the configured regular expression

## [0.7.1] - 2025-03-16

### Changed

- Http request responses are now also used for the media_title attribute of the associated request method's media player entity. This allows you to add a media player widget to an activity and see the response within an activity because you can't add sensors to activities as there's no widget for them.

## [0.7.0] - 2025-03-08

### Added

- Added a sensor entity to show the http request server response message. For more infos see: [Server response sensor entity](/README.md#server-response-sensor-entity)
  
### Changed

- Changed the default integration icon from uc:integration to uc:webhook. This new icon is only available from firmware 2.2.0 or newer
- Translated some default entity names

## [0.6.0] - 2025-01-04

### Breaking changes

- HTTP requests entities can now be used with most parameters and the same syntax as the Python Requests module. This simplifies the usage and adds the possibility of e.g. adding more complex json payload or custom headers (e.g. for server authentication). More infos and examples can be found here: [Additional http requests parameters](/README.md#additional-command-parameters)
  - The previous syntax by using separator characters (§, | etc) is now called legacy syntax and can still be used by activating the legacy syntax option in the advanced setup which is off by default. Please keep in mind that the use of the legacy syntax will be removed in a future version

### Added

- The global settings for Fire and forget mode and timeouts for HTTP requests can now be overwritten as a parameter in each http request command. E.g. use ffg=True to only activate fire and forget for a specific command.

## [0.5.2] - 2024-12-25

### Fixed

- Fixed 1 second delay between consecutive http request commands
- Temporarily fixed a problem with the new web configurator via a workaround where all entities wrongly had the status "Unavailable" by adding an State:On attribute to the entity definitions, although they should actually be stateless
  - After a first time setup you may still need to click on the toggle button in the entity editor in each entity to switch to the correct On state.
  - All issues have been reported to UC as a bug as even stateless entities like these have a state shown in the new configurator and can be toggled even if they don't support this feature and only On/Off state attributes ([Issue 422](https://github.com/unfoldedcircle/feature-and-bug-tracker/issues/422))

## [0.5.1] - 2024-12-18

### Added

- Text over TCP: Added support for C++ and hex style control characters to e.g. add a new line, tab or a carriage return
  - C++ style characters can be escaped with a single additional backslash (e.g. \\\n)
  - Hex style characters can be escaped with "0\\\\\\" (e.g. 0\\\\\\0x09)

## [0.5.0] - 2024-12-15

### Added

- Added text over TCP entity. This protocol is used by some home automation systems, IoT devices or tools like [win-remote-control](https://github.com/moefh/win-remote-control)
  - Example: 192.168.1.1:1234, "Hello World"
- Option to change the default http requests user agent in the advanced setup settings

## [0.4.0] - 2024-11-07

### Added

- Send wake-on-lan magic packets to multiple addresses by separating them with a comma
- Support for all parameters from [pywakeonlan](https://github.com/remcohaszing/pywakeonlan) (interface, port, ip_address)
  - Example: XX:XX:XX:XX:XX:XX,interface=192.168.1.101

## [0.3.1] - 2024-10-19

### Added

- Ignore http requests timeout errors if fire and forget mode is active

### Changed

- Run http requests commands asynchronous in a separate thread to prevent potential websocket heartbeat timeouts if the server takes longer to respond

## [0.3.0] - 2024-09-20

### Breaking changes

- **🎉 This integration can now also run on the remote. From now on each release will have a tar.gz file attached that can be installed on the remote** (see [Run on the remote as a custom integration driver](/README.md#Run-on-the-remote-as-a-custom-integration-driver))
  - ⚠️ Running custom integrations on the remote is currently only available in beta firmware releases and requires version 1.9.2 or newer. Please keep in mind that due to the beta status there are missing firmware features that require workarounds (see link above) and that changes in future beta updates may temporarily or permanently break the functionality of this integration as a custom integration. Please wait until custom integrations are available in stable firmware releases if you don't want to take these risks.
- When running as an external integration driver the working directory when starting driver.py should now be the root of the repository. The path in docker-entry.sh has been adjusted. The configuration json file is therefore now created in the root of the integration directory. Existing users have to move config.json from the intg-requests directory

### Added

- Support for HTTP delete and head requests
- Support for adding json or xml payload data to a http request (see [Adding payload data](/README.md#adding-payload-data))
- Added an option to ignore HTTP requests errors and always return a OK/200 status code to the remote. Helpful if the server doesn't send any response or closes the connection after a command is received (fire and forget). The error message will still be logged but at debug instead of error level
- The wake-on-lan entity now supports an ipv4/v6 address or a hostname (ipv4 only) as a parameter when running as an external integration
  - This feature is not supported when running the integration on the remote due to sandbox limitations
  - Discover the mac address from an ip address or a hostname may not work on all systems. Please refer to the [getmac supported platforms](https://github.com/GhostofGoes/getmac?tab=readme-ov-file#platforms-currently-supported). Docker containers need to be run in the host network (`--net=host`)
- Add build.yml Github action to automatically build a self-contained binary of the integration and create a release draft with the current driver version as a tag/name

### Changed

- Due to the custom integration driver upload feature setup.json has been renamed to driver.json and moved to the root of the repository
- Add custom user agent for http requests (uc-intg-requests)
- Corrected the semantic version scheme in driver.json (x.x to x.x.x)

## [0.2-beta] - 2024-06-26

### Breaking changes

- This integration now uses a configuration file to store the setup state and advanced settings (see below). Existing users therefore need to run the integration setup again to create this file. Just open the integration settings and click on "Start integration setup". You don't need to enter the advanced settings.

### Added

- Added a more granular http status code response handling
- Added optional parameter to send form data in the request body as key/value pairs (see README)
- Added optional custom global entity-independent timeout and ssl verify options in the integration setup. For self signed ssl certificates to work the ssl verify option needs to be deactivated.

### Changed

- Only return an error response to the remote if the http response code is in the 400 or 500 range. Otherwise display the status code in the integration log if it's not 200/Ok

## [0.1-beta] - 2024-04-27

### Added

- First release which supports http get, post, put, patch and wake on lan
