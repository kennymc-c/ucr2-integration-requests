# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

*Changes in the next release*

### Breaking changes
- The configuration json file is now created in the root of the repository. Existing users have to move the config.json file from the intg-requests directory
- The working directory when starting driver.py should now be the root of the repository. The path in docker-entry.sh has been adjusted.
- In preparation to the upcoming custom integration upload feature setup.json has been renamed to driver.json and moved to the root of the repository to adapt to the official UC integrations
 
### Added
- The wake-on-lan entity now supports an ipv4/v6 address or a hostname (ipv4 only) as a parameter
  - Discover the mac address from an ip address or a hostname may not work on all systems. Please refer to the [getmac supported platforms](https://github.com/GhostofGoes/getmac?tab=readme-ov-file#platforms-currently-supported). Docker containers need to be run in the host network (`--net=host`)
- Add build.yml Github action to automatically build a self-contained binary of the integration and create a release draft with the current driver version as a tag/name

### Changed
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
