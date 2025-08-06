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
## [1.2.7]

### Added

* Support for the `appointments`, `eye_color`, `weight`,
`hair_color`, `birth_state` parameters on the Get Matter request.

## [1.2.6]

### Added

* Support for the `prefix`, `home_phone_safe`, `mobile_phone_safe`,
`other_phone_safe`, `work_phone_safe`, `fax_phone_safe`, `pronouns`,
`safe_address` parameters on the Get Matter request.

### Fixed

* Mapping of `client.mobile_number` and `client.work_phone` so that one didn't
overwrite the other.
* Mapping of `client.fax_phone` and `client.other_phone` so that one didn't
overwrite the other.
* Mapping of `client.mobile_number_note` and `client.work_phone_note` so that
one didn't overwrite the other.
* Mapping of `client.fax_phone_note` and `client.other_phone_note` so that one
didn't overwrite the other.

## [1.2.5]

### Added

* Support for the `rejection_reason` parameter on the Get Matter request.

## [1.2.4]

### Added

* Support for the `case_type` parameter on the Get Matter request.

## [1.2.3]

### Added

* Support added for the `custom_results` parameter. This required moving many
fields behind a check to make sure they are not `None`. If there are minimum
required fields that are erroring, defaults can be added in the future.
* Added support for the User `supervisors` and `supervisees` parameters.

## [1.2.2]

### Added

* Support for new `online_intake_payload` parameter.

### Changed

* Added some type checking and not null checking to prevent potential errors.
* Changed how First/Latest Pro Bono Attorneys are selected to prevent bad
potential data errors.

### Fixed

* Corrected type around user field population for `race` and `gender`.
* Fixed bug in Client Address Census Tract.
* Fixed bug in Client Military Status field.
* Added default Client Street Address of "Unknown Street Address" if the
LegalServer Street Address field is None but other address fields are populated.
* Added handling for `number_of_children`

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
* Fixed the keys for the Non-Adverse Party fields and adjusted the populate
function.
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
