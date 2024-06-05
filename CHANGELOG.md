# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

- added data for the post request
- command is splited with the characters | and §
- | adds the string after | to the post request
- § adds the string after § to the post as dictionary
- for § the entry for the source must be http://"URL":"PORT"§key1=value1,key2=value2

### Added

- Added a more granular http status code response handling

### Changed
- Only return an error response to the remote if the http response code is in the 400 or 500 range. Otherwise display the status code in the integration log if it's not 200/Ok

## [0.1-beta] - 2024-03-27

### Added

- First release which supports http get, post, put, patch and wake on lan
