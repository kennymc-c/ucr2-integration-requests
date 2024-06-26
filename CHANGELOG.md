# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

## [0.2-beta] - 2024-06-26

### Breaking changes
- This integration now uses a configuration file to store the setup state and advanced settings (see below). Existing users therefore need to run the integration setup again to create this file. Just open the integration settings and click on "Start integration setup". You don't need to enter the advanced settings.

### Added

- Added a more granular http status code response handling
- Added optional parameter to send form data in the request body as key/value pairs (see README)
- Added optional custom global entity-independent timeout and ssl verify option in the integration setup. For self signed ssl certificates to work the ssl verify option needs to be deactivated.

### Changed
- Only return an error response to the remote if the http response code is in the 400 or 500 range. Otherwise display the status code in the integration log if it's not 200/Ok

## [0.1-beta] - 2024-04-27

### Added

- First release which supports http get, post, put, patch and wake on lan
