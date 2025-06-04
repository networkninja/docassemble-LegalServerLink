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
## [1.2.1]

### Added

* `sample_file_download` interview that will download all of the files from a
LegalServer case as a zip file.
* `get_document` function to download a document from LegalServer to Docassemble.

### Changed

* Clarified documentation regarding the `interview` list provided from
Docassemble to LegalServer.
* Added string defaults for document DAObject items retrieved via
`populate_documents`

## [1.2.0]

### Added

* Additional Test for unhandled fields.
* New Matter, Service, and Charge parameters.
* Refactored Event, Task, User population functions.

### Changed

* Organizations and Adverse Parties will now use a `Name` object when
representing an organization.

### Fixed

* Removed `Content-Type` header for GET requests to LegalServer.
* Better handling of empty lists for custom fields.

## [1.1.2]

### Added

* Recent new matter parameters.

### Changed

* Reorganized LSAPIs for easier exploration.

## [1.1.1]

### Added

* Recent new user paramters are accounted for now.

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
