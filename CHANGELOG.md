# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

*Changes in the next release*

### Breaking changes
- **🎉 This integration can now also run on the remote. From now on each release will have a tar.gz file attached that can be installed on the remote** (see [Run on the remote](/README.md#Run-on-the-remote))
  - This requires beta firmware 1.9.2 or newer. Only from this version onwards the necessary libraries for this integration are included
- When running as an external integration the working directory when starting driver.py should now be the root of the repository. The path in docker-entry.sh has been adjusted. The configuration json file is therefore now created in the root of the integration directory. Existing users have to move config.json from the intg-requests directory
 
### Added
- Support for HTTP delete and head requests
- Support for adding json or xml payload data to a http request (see [Run on the remote](/README.md#adding-payload-data))
- The wake-on-lan entity now supports an ipv4/v6 address or a hostname (ipv4 only) as a parameter when running as an external integration
  - This feature is not supported when running the integration on the remote due to sandbox limitations
  - Discover the mac address from an ip address or a hostname may not work on all systems. Please refer to the [getmac supported platforms](https://github.com/GhostofGoes/getmac?tab=readme-ov-file#platforms-currently-supported). Docker containers need to be run in the host network (`--net=host`)
- Add build.yml Github action to automatically build a self-contained binary of the integration and create a release draft with the current driver version as a tag/name

### Changed
- Due to the custom integration upload feature setup.json has been renamed to driver.json and moved to the root of the repository
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
