# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- How to create a new entry:
See the documentation for Keep a Changelog above.
Try to keep them in this order if possible, skipping what you don't need:

Added - for new features.
Changed - for changes in existing functionality.
Deprecated - for soon-to-be removed features.
Removed - for now removed features.
Fixed - for any bug fixes.
Security - in case of vulnerabilities.

Format:

## [Unreleased]
- 

## [1.0.0] - 2021-01-16
### Added
- 

### Changed
- 

### Deprecated
- 

### Removed
- 

### Fixed
- 

### Security
- 
-->
## [1.1.0]

### Added

* `sites` parameter in the `interviews` list consumed by LegalServer.
* `sort` and `page_limit` parameters in the search functions.
* Added functions and objects to collect documents on a case.

### Changed

* Updated reference in documentation.
* Changed the require login method in the sample interview based on a PR.

## [1.0.6]

### Added

* Added support for the new `external_id` parameters.

### Changed

* Clarified documentation based on user feedback.

## [1.0.5]

### Fixed

* Added some type ignores to account for PyCountry's classes.

## [1.0.4]

### Added

* Added support for GIS fields.

### Fixed

* Additional Names now populate properly.
* Fixed the keys for the Non-Adverse Party fields and adjusted the populate function.
* Fixed the keys for the Services fields.
* Fixed the keys for the Adverse Party fields and adjusted the populate function.
* Fixed the keys for the Events fields and adjusted the populate function.

## [1.0.3]

### Fixed

* Added missing keys to the matter list to prevent them from displaying as
custom fields.

## [1.0.2]

### Fixed

* Added dependency to python tests automated workflow to fix tests.

## [1.0.1]

### Added

* Sample Letter Interview

## [1.0.0]

### Added

* Initial Release

## [0.0.15]

### Fixed

* Resolved todos regarding tasks populating records properly.

## [0.0.14]

### Added

* Added function to retrive a LegalServer Report API request and return it as a
python dictionary. Unit tests included for either XML or JSON reports. This
required specifying the `lxml` dependency.

## [0.0.13]

### Changed

* Changed the upload a file function to return the entire LegalServer response
as a dictionary instead of just the uuid as a string. Updated tests accordingly.

## [0.0.12]

### Added

* Check for Pro Bono Users before trying to populate them.

## [0.0.11]

### Added

* Object for the current LegalServer user, i.e., the user who initiated the
Docassemble interview.
* Objects for Tasks and Non-Adverse Parties.
* Refactor for `legalserver_site_type` as a variable from LegalServer
* Better error handling for API call errors.

## [0.0.10]

### Added

* Objects for current Primary Assignment, First Pro Bono Assignment, Latest
Pro Bono Assignment, and all Pro Bono Assignments.

## [0.0.9]

### Changed

* Get filepath's filename if needed when posting a document to LegalServer.
* Enabled Black formatter

## [0.0.8]

### Added

* Explicit Docassemble dependency
* Functions for Adverse Parties
* Specific Role Privilege for the custom endpoint
* Initial draft of Python unit tests

## [0.0.7]

### Added

* Function to check if an API key exists for the given site.
* Human readable error if the key doesn't exist.
* Test to populate variables

## [0.0.6]

### Changed

* Updated for new `v2` lookup elements

## [0.0.5]

### Added

* added python modules to populate most tables

## [0.0.4]

### Changed

* Updated for `michael.test`

## [0.0.3]

### Added

* Added delete parameter to the retrieve stashed data function

## [0.0.2]

### Added

* Added inital block to retrieve stashed data

## [0.0.1]

### Added

* Successful POC passing file to the Documate endpoint
