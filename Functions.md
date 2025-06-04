# LSAPIs Functions

This is a detailed outline of all the public functions created in the `LSAPIs.py`
file. There are a few other functions used internally in the module but not
listed here.

Note that the functions here are listed identified with LegalServer's convention
that a GET API call that does not specify a `uuid` is a Search API. All the
functions start with that verb/convention.

## check_custom_fields

Check if the response contains any custom fields at the top level.
Custom fields are identified by ending with an underscore followed by an integer.

Returns:
    tuple: (bool, list) where:
        - bool: True if custom fields are present, False otherwise
        - list: List of custom field keys found

### Parameters

* response_object: any python object

## check_legalserver_token

Returns `True` if two things are true:

1. An API token for the given site is present in Docassemble's Config file.
1. The Expiration date for the API token has not passed.

### Parameters

* `legalserver_site` - required string for the LegalServer Site
Abbreviation

## count_of_pro_bono_assignments

Simple function that checks how many pro bono assignments there are.

### Parameters

* `pro_bono_assignment_list` - required DAList of assignments

## country_code_from_name

This uses the PyCountry module's fuzzy search  to convert the name of the
country to the alpha_2 abbreviation. Docassemble uses the abbreviation for
location recognition, but LegalServer stores the name of the country, so this
allows access to both. If multiple countries are identified, the response is
"Unknown" and the error is logged.

There is a built in override that forces "United States" to return "US".
Otherwise, it will return "US", "UM", and "VI".

### Parameters

* `country_name_string` - required string

## get_case_additional_names

This is a keyword defined function that retrieves all the additional names
available on a case using the LegalServer [Get Case Additional Names](https://apidocs.legalserver.org/docs/ls-apis/ctyddn3f0bz92-get-case-additional-names)
API. This returns the json dictionary of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `additional_name_type` - optional string to filter on Additional Name Type
* `search_additional_name_params` - optional dictionary of search parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## get_case_adverse_parties

This is a keyword defined function that retrieves all the adverse parties
available on a case using the LegalServer [Get Case Adverse Parties](https://apidocs.legalserver.org/docs/ls-apis/by52yohjpvtbh-get-case-adverse-parties)
API. This returns the json dictionary of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `adverse_party_type` - optional string to filter on Adverse Party Type
* `search_adverse_party_params` - optional dictionary of search parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## get_case_assignments

This is a keyword defined function that retrieves all the assignments available
on a case using the LegalServer [Get Case Assignments](https://apidocs.legalserver.org/docs/ls-apis/2bb652635011a-get-case-assignments)
API. This returns the json dictionary of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `assignment_type` - optional string to filter on Assignment Type
* `search_assignment_params` - optional dictionary of search parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## get_case_charges

This is a keyword defined function that retrieves all the charges available on a
case using the LegalServer [Get Case Charges](https://apidocs.legalserver.org/docs/ls-apis/17a3bff662f12-get-case-charges)
API. This returns the json dictionary of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `charge_type` - optional string to filter on Charge Type
* `search_charge_params` - optional dictionary of search parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## get_case_contacts

This is a keyword defined function that retrieves all the contacts available on
a case using the LegalServer [Get Case Contacts](https://apidocs.legalserver.org/docs/ls-apis/d0e8009ab22f3-get-case-contacts)
API. This returns the json dictionary of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `contact_type` - optional string to filter on Contact Type
* `search_contact_params` - optional dictionary of search parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## get_case_documents

This is a keyword defined function that retrieves all the documents available on
a case using the LegalServer [Get Case Documents](https://apidocs.legalserver.org/docs/ls-apis/3c6a922f8322b-get-case-documents)
API. This returns the json dictionary of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `document_type` - optional string to filter on Document Type
* `search_document_params` - optional dictionary of search parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## get_case_events

This is a keyword defined function that retrieves all the events available on a
case using the LegalServer [Get Case Events](https://apidocs.legalserver.org/docs/ls-apis/2c5808abc9eca-get-case-events)
API. This returns the json dictionary of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `event_type` - optional string to filter on Event Type
* `search_event_params` - optional dictionary of search parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## get_case_litigations

This is a keyword defined function that retrieves all the litigations available
on a case using the LegalServer [Get Case Litigations](https://apidocs.legalserver.org/docs/ls-apis/2c5808abc9eca-get-case-litigations)
API. This returns the json dictionary of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `litigation_type` - optional string to filter on Litigation Type
* `search_litigation_params` - optional dictionary of search parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## get_case_non_adverse_parties

This is a keyword defined function that retrieves all the non-adverse parties
available on a case using the LegalServer [Get Case Non-Adverse Parties](https://apidocs.legalserver.org/)
API. This returns the json dictionary of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `non_adverse_party_type` - optional string to filter on Non-Adverse Party Type
* `search_non_adverse_party_params` - optional dictionary of search parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## get_case_notes

This is a keyword defined function that retrieves all the notes available on a
case using the LegalServer [Get Case Notes](https://apidocs.legalserver.org/docs/ls-apis/0893f4ce9c6bd-get-case-notes)
API. This returns the json dictionary of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `note_type` - optional string to filter on Note Type
* `search_note_params` - optional dictionary of search parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## get_case_services

This is a keyword defined function that retrieves all the services available on a
case using the LegalServer [Get Case Services](https://apidocs.legalserver.org/docs/ls-apis/1ee2dfa70d780-get-case-services)
API. This returns the json dictionary of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `service_type` - optional string to filter on Service Type
* `search_service_params` - optional dictionary of search parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## get_case_tasks

This is a keyword defined function that retrieves all the tasks available on a
case using the LegalServer [Get Case Tasks](https://apidocs.legalserver.org/docs/ls-apis/6ac41dc42cefd-get-case-tasks)
API. This returns the json dictionary of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `task_type` - optional string to filter on Task Type
* `search_task_params` - optional dictionary of search parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## get_documents

This is a keyword defined function that retrieves a document from LegalServer
and stores it as a DAFile. It returns both the file and a boolean about whether
a file was able to be retrieved.

### parameters

* `legalserver_site` - required
* `document_uuid` - required document UUID
* `document_name` - optional string name of the document. Defaults to
`document.pdf`

## get_event_details

Get details about a specific Event record in LegalServer.

This uses LegalServer's Get Event API to get back details of just one specific
event record.

### Parameters

* `legalserver_site` (str) - The specific LegalServer site to check for the
event on.
* `legalserver_event_uuid` (dict) - The UUID of the specific LegalServer event
to retrieve.
* `custom_fields` (list) - A optional list of custom fields to include.
* `sort` (str) - Optional string to sort the results by. Defaults to ASC.

## get_legalserver_report_data

This is a function that will get a LegalServer report and return the data in a
python dictionary.

This uses the [LegalServer Reports API](https://help.legalserver.org/article/1751-reports-api)
to get any report type data back from
LegalServer and return it as a python dictionary. LegalServer Report APIs can
return data in either JSON or XML format and this will parse either into a
python dictionary. Note that LegalServer's JSON content is not perfect. True/False
are rendered as `t` and `f` instead of JSON booleans. Also integers are
returned as strings. It is also worth noting that the Reports API typically
defaults to include hidden columns. This function defaults to exclude them
unless otherwise specified.

### Parameters

* `legalserver_site` - required
* `display_hidden_columns` - optional boolean to allow for hidden columns (in the
LegalServer Report) to be excluded or included from the results. This defaults
to `False`.
* `report number` - required integer for the specific report
* `report_params` - optional dictionary of additional filters

## get_matter_details

This is a keyword defined function that retrieves all the details available on a
case using the LegalServer [Get Matter Details](https://apidocs.legalserver.org/docs/ls-apis/50f813dcd3a33-get-matter-details)
API. This returns the json dictionary of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `custom_fields` - optional python list of string values
* `custom_fields_charges` - optional python list of string values
* `custom_fields_litigations` - optional python list of string values
* `custom_fields_services` - optional python list of string values
* `sort` - optional string to sort the results

## get_organization_details

This is a keyword defined function that gets details back on a specific
organization record. This allows for the identification of the custom fields as
well. This uses the [Get Organizations](https://apidocs.legalserver.org/docs/ls-apis/3c6a922f8322b-get-an-organization-record)
API endpoint. This returns the json dictionary of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_organization_uuid` - required
* `custom_fields` - optional python list of string values

## get_task_details

Get details about a specific Task record in LegalServer.

This uses LegalServer's Get Task API to get back details of just one specific
task record.

### Parameters

* `legalserver_site` (str) - The specific LegalServer site to check for the
task on.
* `legalserver_task_uuid` (dict) - The UUID of the specific LegalServer task
to retrieve.
* `custom_fields` (list) - A optional list of custom fields to include.
* `sort` (str) - Optional string to sort the results by. Defaults to ASC.

## get_user_details

This is a keyword defined function that gets details back on a specific user
record. This allows for the identification of the custom fields as well. This
uses the [Get User](https://apidocs.legalserver.org/docs/ls-apis/6ac41dc42cefd-get-a-user-record)
API endpoint. This returns the json dictionary of the data returned by the API.

This makes a followup API call to get the organization affiliation data for
the same user before returning all of that data in the response. This uses the
[Search User Organization Affiliation](https://apidocs.legalserver.org/docs/ls-apis/54afc62256692-search-a-user-s-organization-affiliation-records)
API endpoint.

### Parameters

* `legalserver_site` - required
* `legalserver_user_uuid` - required
* `custom_fields` - optional python list of string values

## is_zip_file

This is a small helper function to identify whether the `file_path` presented is
a zip file. This makes a difference when uploading the file to LegalServer.

### Parameters

* `file_path` - required string

## language_code_from_name

This uses the PyCountry module to convert the name of the language to the
alpha_2 abbreviation. Docassemble uses the abbreviation for language
recognition, but LegalServer stores the name of the language, so this allows
access to both.

### Parameters

* `language_name` - required string

## list_templates

This is a small helper function that allows you to get a list of all the
templates stored in the `/data/templates` folder of a given package. If no
package is specified, it will check against the current package. A list of
strings is returned.

### Parameters

* `package` - optional string name of a Docassemble package.

## populate_additional_names

This is a keyword defined function that takes a DAList of IndividualNames and
populates it with the contact details related to a case. If the general
legalserver_data from the `get_matter_details` response is not included, it will
make an API call using the `search_matter_additional_names` function. Since the
standard response from the `get_matter_details` does not include this data, it
will always make that call.

### Parameters

* `additional_name_list` - required DAList of Individuals for the contacts
* `legalserver_data` - Optional dictionary of the matter data from a LegalServer
request
* `legalserver_matter_uuid` - needed if the `legalserver_data` is not provided
* `legalserver_site` - needed if the `legalserver_data` is not provided

## populate_adverse_parties

This is a keyword defined function that takes a DAList of Persons and
populates it with the assignment details related to a case. If the general
legalserver_data from the `get_matter_details` response is not included, it will
make an API call using the `search_matter_adverse_parties` function.

### Parameters

* `adverse_party_list` - DAList of Persons. Note that if it is an Individual
Adverse Party, the `name` attribute will be set to an `IndividualName`.
* `legalserver_data` - Optional dictionary of the matter data from a LegalServer
request
* `legalserver_matter_uuid` - needed if the `legalserver_data` is not provided
* `legalserver_site` - needed if the `legalserver_data` is not
provided

## populate_associated_cases

This is a keyword defined function that takes a DAList of DAObjects and
populates it with the associated case details related to a case. If the general
legalserver_data from the `get_matter_details` response is not included, it does
not make a separate API call since there is not a dedicated endpoint.

### Parameters

* `associated_case_list` - DAList of DAObjects
* `legalserver_data` - Optional dictionary of the matter data from a LegalServer
request
* `legalserver_matter_uuid` - needed if the `legalserver_data` is not provided
* `legalserver_site` - needed if the `legalserver_data` is not provided

## populate_assignments

This is a keyword defined function that takes a DAList of DAObjects and
populates it with the assignment details related to a case. If the general
legalserver_data from the `get_matter_details` response is not included, it will
make an API call using the `search_assignment_data` function.

### Parameters

* `assignment_list` - DAList of DAObjects
* `legalserver_data` - Optional dictionary of the matter data from a LegalServer
request
* `legalserver_matter_uuid` - needed if the `legalserver_data` is not provided
* `legalserver_site` - needed if the `legalserver_data` is not
provided

## populate_case

This is a keyword defined function that takes a DAObject and populates it with
the case related details related to a case. It requires the general
legalserver_data from the `get_matter_details` response.

### Parameters

* `case` - DAObject
* `legalserver_data` - the full case data returned from the Get Matter API call
to LegalServer

## populate_charges

This is a keyword defined function that takes a DAList of DAObjects and
populates it with the charge details related to a case. If the general
legalserver_data from the `get_matter_details` response is not included, it will
make an API call using the `search_matter_charges_data` function.

### Parameters

* `charge_list` - DAList of DAObjects
* `legalserver_data` - Optional dictionary of the matter data from a LegalServer
request
* `legalserver_matter_uuid` - needed if the `legalserver_data` is not provided
* `legalserver_site` - needed if the `legalserver_data` is not provided
* `custom_fields` - Optional list of field names for custom fields to include

## populate_client

This is a keyword defined function that takes a the general legalserver_data
from the `get_matter_details` and saves the client related data to either an
Individual or a Person depending on whether the client is an individual or a
group.

### Parameters

* `client` - Either an Individual or a Person object
* `legalserver_data` - the full case data returned from the Get Matter API call
to LegalServer

## populate_contact_data

Take the data from LegalServer and populate an individual Contact Record.

This is a keyword defined function that takes a given Individual and populates
it with Contact data from LegalServer.

### Parameters

* `contact` (Individual) - required Individual for the contact.
* `contact_data` (dict) - required dictionary of the contact data from a
LegalServer request.

## populate_contacts

This is a keyword defined function that takes a DAList of Individuals and
populates it with the contact details related to a case. If the general
legalserver_data from the `get_matter_details` response is not included, it will
make an API call using the `search_contact_data` function.

### Parameters

* `contact_list` - required DAList of Individuals for the contacts
* `legalserver_data` - Optional dictionary of the matter data from a LegalServer
request
* `legalserver_matter_uuid` - needed if the `legalserver_data` is not provided
* `legalserver_site` - needed if the `legalserver_data` is not provided
* `custom_fields` - Optional list of field names for custom fields to include

## populate_current_user

This is a keyword defined function that takes an Individual object and populates
it with the user data of the user who initiated the Docassemble Interview from
LegalServer.

### Parameters

* `legalserver_current_user` - Individual object that will be returned
* `legalserver_current_user_uuid` - needed to identify the user.
* `legalserver_site` - needed to identify the site.
* `user_custom_fields` - Optional list of custom fields to gather on the User record.

## populate_event_data

Take the data from LegalServer and populate an individual Event Record.

This is a keyword defined function that takes a given DAObject and populates
it with Event data from LegalServer.

### Parameters

* `event` (DAObject) - required DAObject for the Event.
* `event_data` (dict) - required dictionary of the Event data from a
LegalServer request.

## populate_events

This is a keyword defined function that takes a DAList of DAObjects and
populates it with the event details related to a case. If the general
legalserver_data from the `get_matter_details` response is not included, it will
make an API call using the `search_event_data` function.

Note that because this package is designed to connect LegalServer cases to
Docassemble, it does not address the Outreaches key present in the LegalServer
event response.

### Parameters

* `event_list` - DAList of DAObjects
* `legalserver_data` - Optional dictionary of the matter data from a LegalServer
request
* `legalserver_matter_uuid` - needed if the `legalserver_data` is not provided
* `legalserver_site` - needed if the `legalserver_data` is not provided
* `custom_fields` - Optional list of field names for custom fields to include

## populate_first_pro_bono_assignment

This is a keyword defined function that takes an Individual object and populates
it with the user data of the earliest Pro Bono assignment on a case that has not
yet ended. This needs `populate_assignment()` run first so that it can parse the
list of assignments on the case for the expected Pro Bono assignment.

### Parameters

* `legalserver_first_pro_bono_assignment` - Individual object that will be returned
* `assignment_list` - DAList of DAObjects
* `legalserver_data` - Optional dictionary of the matter data from a LegalServer
request
* `legalserver_matter_uuid` - needed if the `legalserver_data` is not provided
* `legalserver_site` - needed if the `legalserver_data` is not provided
* `user_custom_fields` - Optional list of custom fields to gather on the User record.

## populate_given_contact

This is a keyword defined function that takes an Individual object and populates
it with the Contact data of the given LegalServer Contact.

### Parameters

* `legalserver_contact` (Individual) - Individual object that will be returned.
* `legalserver_contact_uuid` (str) - The UUID for the specific contact record.
* `legalserver_site` (str) - The site to query for the contact record.
* `contact_custom_fields` (list) - Optional list of custom fields to gather on
the Contact record.

## populate_given_event

This is a keyword defined function that takes an DAObject object and populates
it with the Event data of the given LegalServer Event.

### Parameters

* `legalserver_event` (DAObject) - DAObject object that will be returned.
* `legalserver_event_uuid` (str) - The UUID for the specific event record.
* `legalserver_site` (str) - The site to query for the event record.
* `event_custom_fields` (list) - Optional list of custom fields to gather on
the event record.

## populate_given_organization

This is a keyword defined function that takes a Person object and populates
it with the Organization data of the given LegalServer organization.

### Parameters

* `legalserver_organization` (Person) - Person object that will be returned.
* `legalserver_organization_uuid` (str) - The UUID for the specific organization
record.
* `legalserver_site` (str) - The site to query for the organization record.
* `organization_custom_fields` (list) - Optional list of custom fields to gather
on the organization record.

## populate_given_task

This is a keyword defined function that takes a DAObject object and populates
it with the task data of the given LegalServer task.

### Parameters

* `legalserver_task` (DAObject) - DAObject object that will be returned.
* `legalserver_task_uuid` (str) - The UUID for the specific task
record.
* `legalserver_site` (str) - The site to query for the task record.
* `task_custom_fields` (list) - Optional list of custom fields to gather on
the task record.

## populate_given_user

This is a keyword defined function that takes an Individual object and populates
it with the user data of the given LegalServer user.

### Parameters

* `legalserver_user` (Individual) - Individual object that will be returned.
* `legalserver_user_uuid` (str) - The UUID for the specific user
record.
* `legalserver_site` (str) - The site to query for the user record.
* `user_custom_fields` (list) - Optional list of custom fields to gather on
the user record.

## populate_income

This is a keyword defined function that takes a DAList of DAObjects and
populates it with the income details related to a case.

### Parameters

* `income_list` - DAList of DAObjects
* `legalserver_data` - Optional dictionary of the matter data from a LegalServer
request
* `legalserver_matter_uuid` - needed if the `legalserver_data` is not provided
* `legalserver_site` - needed if the `legalserver_data` is not provided

## populate_latest_pro_bono_assignment

This is a keyword defined function that takes an Individual object and populates
it with the user data of the latest Pro Bono assignment on a case that has not
yet ended. This needs `populate_assignment()` run first so that it can parse the
list of assignments on the case for the expected Pro Bono assignment.

### Parameters

* `legalserver_latest_pro_bono_assignment` - Individual object that will be returned
* `assignment_list` - DAList of DAObjects
* `legalserver_data` - Optional dictionary of the matter data from a LegalServer
request
* `legalserver_matter_uuid` - needed if the `legalserver_data` is not provided
* `legalserver_site` - needed if the `legalserver_data` is not provided
* `user_custom_fields` - Optional list of custom fields to gather on the User record.

## populate_litigations

This is a keyword defined function that takes a DAList of DAObjects and
populates it with the litigation details related to a case. If the general
legalserver_data from the `get_matter_details` response is not included, it will
make an API call using the `search_matter_litigation_data` function.

### Parameters

* `litigation_list` - DAList of DAObjects
* `legalserver_data` - Optional dictionary of the matter data from a LegalServer
request
* `legalserver_matter_uuid` - needed if the `legalserver_data` is not provided
* `legalserver_site` - needed if the `legalserver_data` is not provided
* `custom_fields` - Optional list of field names for custom fields to include

## populate_organization_data

This is a keyword defined function that takes a Person object and populates
it with the organization data of the relevant organization record.

### paramters

* `organization` (Person) - Person object that will be returned
* `organization_data` (Dict | None): dictionary of the organization data
from a LegalServer request

## populate_notes

This is a keyword defined function that takes a DAList of DAObjects and
populates it with the note details related to a case. If the general
legalserver_data from the `get_matter_details` response is not included, it will
make an API call using the `search_matter_notes_data` function.

### Parameters

* `note_list` - DAList of DAObjects
* `legalserver_data` - Optional dictionary of the matter data from a LegalServer
request
* `legalserver_matter_uuid` - needed if the `legalserver_data` is not provided
* `legalserver_site` - needed if the `legalserver_data` is not provided

## populate_primary_assignment

This is a keyword defined function that takes an Individual object and populates
it with the user data of the current primary assignment on a case. This needs
`populate_assignment()` run first so that it can parse the list of assignments
on the case for the current primary assignment.

### Parameters

* `primary_assignment` - Individual object that will be returned
* `assignment_list` - DAList of DAObjects
* `legalserver_data` - Optional dictionary of the matter data from a LegalServer
request
* `legalserver_matter_uuid` - needed if the `legalserver_data` is not provided
* `legalserver_site` - needed if the `legalserver_data` is not provided
* `user_custom_fields` - Optional list of custom fields to gather on the User record.

## populate_pro_bono_assignments

This is a keyword defined function that takes a DAList of Individuals and populates
it with the user data of all the assigned Pro Bono assignments on a case
whose assignments have not yet been ended. This needs
`populate_assignment()` run first so that it can parse the list of assignments
on the case for the current primary assignment.

### Parameters

* `pro_bono_assignment_list` - DAList object of Individual objects that will be
returned
* `assignment_list` - DAList of DAObjects
* `legalserver_data` - Optional dictionary of the matter data from a LegalServer
request
* `legalserver_matter_uuid` - needed if the `legalserver_data` is not provided
* `legalserver_site` - needed if the `legalserver_data` is not provided
* `user_custom_fields` - Optional list of custom fields to gather on the User record.

## populate_services

This is a keyword defined function that takes a DAList of DAObjects and
populates it with the service details related to a case. If the general
legalserver_data from the `get_matter_details` response is not included, it will
make an API call using the `search_matter_service_data` function.

### Parameters

* `service_list` - DAList of DAObjects
* `legalserver_data` - Optional dictionary of the matter data from a LegalServer
request
* `legalserver_matter_uuid` - needed if the `legalserver_data` is not provided
* `legalserver_site` - needed if the `legalserver_data` is not provided
* `custom_fields` - Optional list of field names for custom fields to include

## populate_task_data

Take the data from LegalServer about a given task and populate a given
DAObject with the data.

### Paramters

* `legalserver_task` (DAObject):  DAObject to be returned.
* `task_data` (dict): Dictionary of the task data from a LegalServer request.

## populate_tasks

Take the data from LegalServer and populate a list of LegalServer tasks
into a DAList of DAObjects.

This is a keyword defined function that takes a DAList of DAObjects and
populates it with the task details related to a case. If the general
legalserver_data from the `get_matter_details` response is not included, it
makes an API call using the `search_task_data` function.

### Paramters

* `task_list` (DAList[DAObject]) - DAList of DAObjects.
* `legalserver_data` (dict) - Optional dictionary of the matter data from a
LegalServer request.
* `legalserver_matter_uuid` (str) - needed if the `legalserver_data` is not
provided.
* `legalserver_site` (str) - needed if the `legalserver_data` is not provided.

## populate_user_data

This is a keyword defined function that helps populate an Individual record
with details from the Get User API response.

### Parameters

* `user` - The Individual object to be populated and returned.
* `user_data` - The get_user_details() response dictionary that has
the information to populate the record with.

## post_file_to_legalserver_documents_webhook

This is a keyword defined function that takes three required parameters and one
optional parameter. Like the other function, it requires the
`legalserver_site` and `legalserver_matter_uuid` to link back to
the case. It also takes the `file_path` of the file that was generated in
Docassemble. This can be retrieved by using `.path()` with the file variable. If
the file uploaded is a zip file, the file will be saved to the case, unzipped to
the specified folder (or the root directory if one was not supplied) and a case
note linked to those documents created. If the file is not a zip file, it will
just be saved to the case. The folder can be specified with the `subfolder`
optional parameter. This uses the [Post Documents to LegalServer as a Zip](https://apidocs.legalserver.org/docs/ls-apis/138783948082d-post-documents-to-legal-server-as-a-zip)
endpoint.

### Parameters

* `legalserver_site` - required string for the LegalServer Site
Abbreviation
* `legalserver_matter_uuid` - required string for the LegalServer Matter UUID
* `file_path` - required string for the path to the file to be sent.
* `subfolder` - optional string to identify a subfolder to store the file in
when uploaded to LegalServer
* `save_to_sharepoint` - optional boolean to save the file to the case's
SharePoint case folder instead of the LegalServer document storage.

## search_contact_data

This is a keyword defined function that searches for contacts based on a set of
criteria passed in the `contact_search_params`. This uses the Legalserver
[Search Contacts](https://apidocs.legalserver.org/docs/ls-apis/5c5868ca37157-search-contacts)
API endpoint. This returns the json list of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `contact_search_params` - optional python dictionary of any search parameters
* `custom_fields` - optional python list of string values
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## search_matter_additional_name_data

This is a keyword defined function that searches a specific matter for
additional names of the client. This uses the [Search Matter Additional Names](https://apidocs.legalserver.org/docs/ls-apis/ctyddn3f0bz92-search-a-matter-s-additional-names)
API endpoint. This returns the json list of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `matter_additional_names_search_params` - Optional dictionary of search parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## search_matter_adverse_parties

This is a keyword defined function that searches a specific matter for adverse
Parties. This uses the [Search Matter Adverse Parties](https://apidocs.legalserver.org/docs/ls-apis/by52yohjpvtbh-search-a-matter-s-adverse-parties)
API endpoint. This returns the json list of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `matter_adverse_parties_search_params` - Optional dictionary of search
parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## search_matter_assignment_data

This is a keyword defined function that searches a specific matter for
assignments. This uses the [Search Matter Assignments](https://apidocs.legalserver.org/docs/ls-apis/2bb652635011a-search-a-matter-s-assignments)
API endpoint. This returns the json list of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required string for the LegalServer Matter's UUID
* `matter_assignment_search_params` - optional python dictionary of filters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## search_matter_charges_data

This is a keyword defined function that searches a specific matter for charges.
This uses the [Search Matter Charges](https://apidocs.legalserver.org/docs/ls-apis/17a3bff662f12-get-matter-charges)
API endpoint. This returns the json list of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `charges_search_params` - Optional dictionary of search parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## search_matter_contacts_data

This is a keyword defined function that searches a specific matter for case
contacts. This uses the [Search Matter Contacts](https://apidocs.legalserver.org/docs/ls-apis/d0e8009ab22f3-get-matter-contacts)
API endpoint. This returns the json list of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `matter_contact_search_params` - Optional dictionary of search parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## search_matter_litigation_data

This is a keyword defined function that searches a specific matter for
litigations. This uses the [Search Matter Litigations](https://apidocs.legalserver.org/docs/ls-apis/2c5808abc9eca-get-matter-litigations)
API endpoint. This returns the json list of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `litigation_search_params` - Optional dictionary of search parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## search_matter_non_adverse_parties

This is a keyword defined function that searches a specific matter for Non-Adverse
Parties. This uses the [Search Matter Non-Adverse Parties](https://apidocs.legalserver.org/)
API endpoint. This returns the json list of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `matter_non_adverse_parties_search_params` - Optional dictionary of search
parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## search_matter_notes_data

This is a keyword defined function that gets back all of the notes on a case.
The notes can be filtered in the API call based on the note_type. This uses the
[Search Matter Notes](https://apidocs.legalserver.org/docs/ls-apis/0893f4ce9c6bd-get-matter-case-note)
API endpoint. They are returned as a list of notes.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `note_type` - Optional string to filter on Note Type
* `search_note_params` - Optional dictionary of search parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## search_matter_services_data

This is a keyword defined function that searches a specific matter for Services.
This uses the [Search Matter Services](https://apidocs.legalserver.org/docs/ls-apis/1ee2dfa70d780-get-matter-services)
API endpoint. This returns the json list of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `legalserver_matter_uuid` - required
* `services_search_params` - Optional dictionary of search parameters
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## search_organization_data

This is a keyword defined function that searches for organizations based on a
set of criteria passed in the `organization_search_params`. This uses the
Legalserver [Search Organizations](https://apidocs.legalserver.org/docs/ls-apis/4e4da540a1e7b-search-organizations)
API endpoint. This returns the json list of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `organization_search_params` - optional python dictionary of any search parameters
* `custom_fields` - optional python list of string values
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## search_user_data

This is a keyword defined function that searches for users based on a set of
criteria passed in the `user_search_params`. This uses the Legalserver
[Search Users](https://apidocs.legalserver.org/docs/ls-apis/71f6882a38e1d-search-users)
API endpoint. This returns the json list of the data returned by the API.

### Parameters

* `legalserver_site` - required
* `user_search_params` - optional python dictionary of any search parameters
* `custom_fields` - optional python list of string values
* `sort` - optional string to sort the results
* `page_limit` - optional limit to the number of pages returned

## search_user_organization_affiliation

This is a keyword defined function that gets back all of the organization
affiliation records on a user. This uses the Search User Organization
Affiliation API endpoint. They are returned as a list of Organization
Affiliations.

### Parameters

* `legalserver_site` - required string
* `legalserver_user_uuid` - required string

## Standard Keys

There are functions also designed to just return the list of standard keys
returned in the LegalServer API calls. This makes it easier to identify when
there are custom fields present in the API response. These exist for the
following LegalServer response objects:

* Additional Names
* Adverse Parties
* Assignments
* Charges
* Client Addresses
* Contacts
* Documents
* Events
* Incomes
* Litigations
* Matters
* Non-Adverse Parties
* Organizations
* Services
* Tasks
* Users
