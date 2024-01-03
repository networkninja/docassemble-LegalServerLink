import requests
import pycountry
import json
import defusedxml.ElementTree as etree
from datetime import date
import docassemble.base.functions
from docassemble.base.util import (
    log,
    Address,
    Individual,
    DAList,
    DAObject,
    Person,
    Organization,
    DAFile,
    IndividualName,
    zip_file,
    current_datetime,
    date_interval,
    format_datetime,
    date_difference,
    path_and_mimetype,
)
import zipfile
from typing import List, Dict, Union, Optional
import os.path
from os import listdir

__all__ = [
    "post_file_to_legalserver_documents_webhook",
    "country_code_from_name",
    "language_code_from_name",
    "check_legalserver_token",
    "get_matter_details",
    "get_user_details",
    "search_user_data",
    "search_matter_notes_data",
    "search_matter_litigation_data",
    "search_matter_services_data",
    "search_matter_contacts_data",
    "search_matter_charges_data",
    "search_event_data",
    "search_task_data",
    "search_matter_additional_names",
    "search_matter_adverse_parties",
    "search_matter_non_adverse_parties",
    "get_organization_details",
    "search_organization_data",
    "get_contact_details",
    "search_contact_data",
    "populate_income",
    "populate_notes",
    "populate_assignments",
    "populate_litigations",
    "populate_charges",
    "populate_contacts",
    "populate_services",
    "populate_events",
    "populate_tasks",
    "populate_client",
    "populate_case",
    "populate_additional_names",
    "populate_adverse_parties",
    "populate_non_adverse_parties",
    "standard_litigation_keys",
    "standard_services_keys",
    "standard_charges_keys",
    "standard_organization_keys",
    "standard_user_keys",
    "standard_contact_keys",
    "standard_task_keys",
    "standard_matter_keys",
    "standard_adverse_party_keys",
    "standard_non_adverse_party_keys",
    "standard_client_home_address_keys",
    "populate_primary_assignment",
    "populate_current_user",
    "populate_first_pro_bono_assignment",
    "populate_latest_pro_bono_assignment",
    "populate_user_data",
    "populate_pro_bono_assignments",
    "count_of_pro_bono_assignments",
    "is_zip_file",
    "get_legalserver_report_data",
    "list_templates",
]


def country_code_from_name(country_name_string: str) -> str:
    """Uses PyCountry to convert a country's name to the ISO alpha_2 code.

    This uses the PyCountry module to convert the name of the country to the alpha_2
    abbreviation. Docassemble uses the abbreviation for location recognition, but
    LegalServer stores the name of the country, so this allows access to both.

    There is an override here to force "United States" to return as "US" when it
    otherwise wouldn't because "United States" returns "US", "UM", and "VI" in
    the fuzzy search that PyCountry uses.

    Args:
        country_name_string (str): The name of a country.

    Returns:
        A string with the ISO alpha_2 code. If either a country cannot be mapped
        to the given name or multiple countries could be mapped to the name
        then `Unknown` is returned instead.
    """

    country_code = "Unknown"
    if country_name_string is not None:
        if country_name_string == "United States":
            return "US"
        else:
            try:
                country_list = pycountry.countries.search_fuzzy(country_name_string)
                if len(country_list) == 1:
                    country_code = country_list[0].alpha_2  # type: ignore[attr-defined]
                elif len(country_list) > 1:
                    log(
                        f"Multiple responses when converting country to country"
                        f"code alpha_2 for {country_name_string}"
                    )
                    country_code = "Unknown"
                elif len(country_list) == 0:
                    log(
                        f"No responses when converting country to country"
                        f"code alpha_2 for {country_name_string}"
                    )
                    country_code = "Unknown"
            except:
                log(
                    f"Error converting country to country code alpha_2 for "
                    f"{country_name_string}"
                )
                country_code = "Unknown"
    return country_code


def language_code_from_name(language_name: str) -> str:
    """Uses PyCountry to convert a language from a string to the ISO Alpha 2
    code.

    This uses the PyCountry module to convert the name of the language to the
    alpha_2 abbreviation. Docassemble uses the abbreviation for language
    recognition, but LegalServer stores the name of the language, so this allows
    access to both.

    Args:
        language_name (str): The name of a language.

    Returns:
        A string with the ISO alpha_2 code. If either a language cannot be
        mapped to the given name or multiple languages could be mapped to the
        name then `Unknown` is returned instead.
    """

    language_code = "Unknown"
    if language_name is not None:
        try:
            language_dict = pycountry.languages.lookup(language_name).alpha_2  # type: ignore
            language_code = language_dict
        except:
            log(
                f"Error converting language from name to language alpha_2 for "
                f"{language_name}"
            )
            language_code = "Unknown"
    return language_code


def is_zip_file(file_path: str) -> bool:
    """Checks to see if this file is a zip file.

    This is a small helper function to identify whether the `file_path`
    presented is a zip file. This makes a difference when uploading the file to
    LegalServer.

    Args:
        file_path (str): The required path for a given file.

    Returns:
        A boolean of whether the file provided is a zip file.
    """

    log(f"Checking if {file_path} is a zip file.")
    try:
        with zipfile.ZipFile(file_path) as zipf:
            return True
    except zipfile.BadZipFile:
        return False
    except Exception as e:
        log(f"Error checking zip file: {file_path}. Exception raised: {str(e)}")
        return False


def post_file_to_legalserver_documents_webhook(
    *,
    legalserver_site: str,
    file_path: str,
    legalserver_matter_uuid: str,
    subfolder: str = "",
    save_to_sharepoint: bool = False,
) -> Dict:
    """This function uses LegalServer's /documents/matter_zip endpoint to
    upload a file. If it is a zip file, a case note will be created. If it
    is not a zip file, the file is just saved.

    This is a keyword defined function that takes three required parameters and
    one optional parameter. Like the other function, it requires the
    `legalserver_site` and `legalserver_matter_uuid` to link back
    to the case. It also takes the `file_path` of the file that was generated in
    Docassemble. This can be retrieved by using `.path()` with the file
    variable. If the file uploaded is a zip file, the file will be saved to the
    case, unzipped to the specified folder (or the root directory if one was not
    supplied) and a case note linked to those documents created. If the file is
    not a zip file, it will just be saved to the case. The folder can be
    specified with the `subfolder` optional parameter.

    Args:
        legalserver_site (str): required string for the LegalServer
            Site Abbreviation.
        legalserver_matter_uuid (str): required string for the LegalServer
            Matter UUID.
        file_path (str): required string for the path to the file to be sent.
        subfolder (str): optional string to identify a subfolder to store the
            file in when uploaded to LegalServer.
        save_to_sharepoint (bool): optional boolean to save the file to the
            case's SharePoint case folder.

    Returns:
        A dictionary containing the LegalServer response.
    """

    header_content = get_legalserver_token(legalserver_site=legalserver_site)

    url = f"https://{legalserver_site}.legalserver.org/api/v1/documents/matter_zip"

    payload = {"legalserver_matter_uuid": legalserver_matter_uuid}
    if subfolder:
        payload["legalserver_subfolder"] = subfolder
    if save_to_sharepoint:
        payload["save_to_sharepoint"] = True  # type: ignore

    if is_zip_file(file_path):
        files = {"files": ("files.zip", open(file_path, "rb"))}
    else:
        files = {"files": (os.path.basename(file_path), open(file_path, "rb"))}
        log(f"This file will not generate a case note since it is not a zip file.")

    log(
        f"Attempting to post file: {file_path} to case uuid: {legalserver_matter_uuid}"
        f" on: {legalserver_site}"
    )
    return_dict: Dict
    try:
        response = requests.post(
            url, data=payload, files=files, headers=header_content, timeout=(3, 30)
        )
        response.raise_for_status()

        if response.status_code != 200:
            log(
                f"LegalServer saving document failed: {str(response.status_code)}"
                f" ,{response.text} body: {str(response.request.body)} headers: "
                f"{str(response.request.headers)}"
            )
            return_dict = {"error": str(response.status_code)}
        else:
            return_dict = response.json()
            log(
                f"LegalServer Saving Document success: {str(response.status_code)},"
                f" {response.json().get('uuid')}"
            )
    except requests.exceptions.ConnectionError as e:
        log(f"LegalServer saving document failed: {e}")
        return {"error": e}
    except requests.exceptions.HTTPError as e:
        log(f"LegalServer saving document failed: {e}")
        return {"error": e}
    except requests.exceptions.Timeout as e:
        log(f"LegalServer saving document failed: {e}")
        return {"error": e}
    except Exception as e:
        log(f"LegalServer saving document failed: {e}")
        return {"error": e}
    return return_dict  # type: ignore


def get_matter_details(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    custom_fields: list | None = None,
    custom_fields_services: list | None = None,
    custom_fields_litigations: list | None = None,
    custom_fields_charges: list | None = None,
) -> Dict:
    """This function gets the Details of a LegalServer matter using the Get
    Matters endpoint.

    This is a keyword defined function that retrieves all the details available
    on a case using the LegalServer [Get Matter Details](https://apidocs.legalserver.org/docs/ls-apis/50f813dcd3a33-get-matter-details)
    API. This returns the json dictionary of the data returned by the API.

    Args:
        legalserver_site (str): required
        legalserver_matter_uuid (str): required
        custom_fields (list[str]): optional python list of string values
        custom_fields_charges (list[str]): optional python list of string values
        custom_fields_litigations (list[str]): optional python list of string values
        custom_fields_services (list[str]): optional python list of string values

    Returns:
        A dictionary of the LegalServer Matter details.

    Raises:
        Exceptions are returned as the reponse dictionary with a key of `error`.
    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)

    header_content["Content-Type"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}"

    queryparam_data = {}
    if custom_fields:
        queryparam_data["custom_fields"] = custom_fields
    if custom_fields_litigations:
        queryparam_data["custom_fields_litigations"] = custom_fields_litigations
    if custom_fields_charges:
        queryparam_data["custom_fields_charges"] = custom_fields_charges
    if custom_fields_services:
        queryparam_data["custom_fields_services"] = custom_fields_services

    return_data = get_legalserver_response(
        url=url,
        params=queryparam_data,
        legalserver_site=legalserver_site,
        source_type="matter",
        header_content=header_content,
        uuid=legalserver_matter_uuid,
    )
    return return_data


def get_organization_details(
    *,
    legalserver_site: str,
    legalserver_organization_uuid: str,
    custom_fields: list | None = None,
) -> Dict:
    """This returns information about a specific Organization in LegalServer.

    This uses LegalServer's Get Organizations API to get back details of just
    one specific of Organizations.

    Args:
        legalserver_site (str): The specific LegalServer site to
            check for the organization on.
        legalserver_organization_uuid (dict): The UUID of the specific LegalServer
            organization to retrieve
        custom_fields (list): A optional list of custom fields to include.

    Returns:
        A dictionary for the specific organization.

    Raises:
        Errors are handled in the response. Errors will be present when the
        dictionary response includes a key of 'error'


    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Content-Type"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/organizations/{legalserver_organization_uuid}"
    queryparam_data = {}

    if custom_fields:
        queryparam_data["custom_fields"] = custom_fields

    return_data = get_legalserver_response(
        url=url,
        params=queryparam_data,
        legalserver_site=legalserver_site,
        source_type="organization",
        header_content=header_content,
        uuid=legalserver_organization_uuid,
    )

    return return_data


def search_organization_data(
    *,
    legalserver_site: str,
    organization_search_params: dict | None = None,
    custom_fields: list | None = None,
) -> List[Dict]:
    """
    Search Organizations within LegalServer for a given set of parameters and custom fields.

    This uses LegalServer's Search Organizations API to get back a list of Organizations.

    Args:
        legalserver_site (str):
        organization_search_params (dict):
        custom_fields (list):

    Returns:
        List of dictionaries

    Raises:
        Errors are handled in the response. Errors will be present when the dictionary response includes a key of 'error'

    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Content-Type"] = "application/json"
    if not organization_search_params:
        organization_search_params = {}
    url = f"https://{legalserver_site}.legalserver.org/api/v2/organizations"
    if custom_fields:
        organization_search_params["custom_fields"] = custom_fields

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="organizations",
        params=organization_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
    )

    return return_data


def get_legalserver_token(*, legalserver_site: str) -> Dict[str, str]:
    """Gathers the API token of the site and checks its validity.

    This function checks that the token exists, is still valid, and then returns it in
    a dictionary for use in a requests API call.

    Args:
        legalserver_site_abbreciation (str): required string

    Returns:
        Dictionary with the token as part of the standard Authorization key for use
            in a Requests API call.

    Raises:
        Exception: if either there are no API credentials or the API Credentials have expired.
    """
    apikey = docassemble.base.functions.get_config("legalserver").get(
        legalserver_site.lower()
    )
    if apikey is None:
        raise Exception(f"No API Credentials for {legalserver_site}")
    elif apikey.get("bearer") is None:
        raise Exception(f"No bearer token for {legalserver_site}")
    if apikey.get("expiration") is None:
        raise Exception(f"No token expiration date for {legalserver_site}")
    else:
        if date_difference(starting=apikey.get("expiration"), ending=current_datetime()).days > 0:  # type: ignore
            raise Exception(f"Bearer token for {legalserver_site} has expired")
    return {"Authorization": "Bearer " + str(apikey["bearer"])}


def check_legalserver_token(*, legalserver_site: str) -> Dict:
    """Checks the API token of the site and checks its validity.

    Args:
        legalserer_site_abbreviation (str): Required string

    Responses:
        Dictionary. Key named error is included if there is an error. Otherwise a
            key named no_error is included. The key contains the details for the error.
    """
    apikey = docassemble.base.functions.get_config("legalserver").get(
        legalserver_site.lower()
    )
    if apikey is None:
        return {"error": "site not included in configuration"}
    elif apikey.get("bearer") is None:
        return {"error": "no bearer token for site available"}
    if apikey.get("expiration") is None:
        # no expiration so return false
        return {"error": "no bearer token expiration for site available"}
    else:
        if date_difference(starting=apikey.get("expiration"), ending=current_datetime()).days > 0:  # type: ignore
            log("Bearer Token for " + legalserver_site + " has expired.")
            return {"error": "bearer token expired"}
    return {"no_error": "valid token"}


def search_matter_notes_data(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    note_type: str = "",
    search_note_params: dict | None = None,
) -> List[Dict]:
    """Search Notes on a given Matter within LegalServer.

    This is a keyword defined function that gets back all of the notes on a case.
    The notes can be filtered in the API call based on the note_type. This uses the
    Search Matter Notes
    API endpoint. They are returned as a list of notes.

    Args:
        legalserver_site (str): required
        legalserver_matter_uuid (str): required
        note_type (str): Optional string to filter on Note Type
        search_note_params (dict): Optional dictionary of search parameters

    Returns:
        A list of dictionaries with the notes data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Content-Type"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/notes"

    if not search_note_params:
        search_note_params = {}
    if note_type:
        search_note_params["note_type"] = note_type

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="notes",
        params=search_note_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
    )

    return return_data


def search_matter_litigation_data(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    litigation_search_params: dict | None = None,
    custom_fields: list | None = None,
) -> List[Dict]:
    """Search Litigation records within a given matter in LegalServer.

    This is a keyword defined function that gets back all of the litigation
    records on a case. The litigations can be filtered in the API call based on
    the search parameters. This uses the
    Search Matter Litigations
    API endpoint. They are returned as a list of Litigations.

    Args:
        legalserver_site (str): required
        legalserver_matter_uuid (str): required
        custom_fields (list): Optional list of custom fields to include in the
            response.
        litigation_search_params (dict): Optional dictionary of search parameters

    Returns:
        A list of dictionaries with the litigation data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Content-Type"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/litigations"

    if not litigation_search_params:
        litigation_search_params = {}
    if custom_fields:
        litigation_search_params["custom_fields"] = custom_fields

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="litigation",
        params=litigation_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
    )

    return return_data


def search_matter_services_data(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    services_search_params: dict | None = None,
    custom_fields: list | None = None,
) -> List[Union[str, Dict]]:
    """Search Service records for a given Matter in LegalServer.

    This is a keyword defined function that gets back all of the services on a
    case. The services can be filtered in the API call based on the search
    parameters. Additional custom fields can be retrieved. This uses the Search
    Matter Services API endpoint. They are returned as a list of Services.

    Args:
        legalserver_site (str): required
        legalserver_matter_uuid (str): required
        custom_fields (list): Optional list to include any custom fields
        services_search_params (dict): Optional dictionary of search parameters

    Returns:
        A list of dictionaries with the services data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Content-Type"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/services"
    if not services_search_params:
        services_search_params = {}
    if custom_fields:
        services_search_params["custom_fields"] = custom_fields

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="services",
        params=services_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
    )

    return return_data  # type: ignore


def search_matter_charges_data(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    charges_search_params: dict | None = None,
    custom_fields: list | None = None,
) -> List[Dict]:
    """Search Charges on a given Matter in LegalServer.

    This is a keyword defined function that gets back all of the charges on a
    case. The charges can be filtered in the API call based on the search
    parameters. Additional custom fields can be retrieved. This uses the Search
    Matter Charges API endpoint. They are returned as a list of Charges.

    Args:
        legalserver_site (str): required
        legalserver_matter_uuid (str): required
        custom_fields (list): Optional list to include any custom fields
        charges_search_params (dict): Optional dictionary of search parameters

    Returns:
        A list of dictionaries with the charges data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Content-Type"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/charges"
    if not charges_search_params:
        charges_search_params = {}
    if custom_fields:
        charges_search_params["custom_fields"] = custom_fields

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="charges",
        params=charges_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
    )

    return return_data


def search_matter_contacts_data(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    matter_contact_search_params: dict | None = None,
) -> List[Dict]:
    """Search Case Contacts on a given Matter in LegalServer.

    This is a keyword defined function that gets back all of the contacts on a
    case. The contacts can be filtered in the API call based on the search
    parameters. This uses the Search Matter Contacts API endpoint. They are
    returned as a list of Contacts.

    Args:
        legalserver_site (str): required
        legalserver_matter_uuid (str): required
        matter_contact_search_params (dict): Optional dictionary of search
            parameters

    Returns:
        A list of dictionaries with the contacts data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Content-Type"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/contacts"
    if not matter_contact_search_params:
        matter_contact_search_params = {}

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="matter_contact",
        params=matter_contact_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
    )

    return return_data  # type: ignore


def search_matter_assignments_data(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    matter_assignment_search_params: dict | None = None,
) -> List[Dict]:
    """Search Assignments on a given Matter in LegalServer.

    This is a keyword defined function that gets back all of the assignments on
    a case. The assignments can be filtered in the API call based on the search
    parameters. This uses the Search Matter Assignments API endpoint. They are
    returned as a list of assignments.

    Args:
        legalserver_site (str): required
        legalserver_matter_uuid (str): required
        matter_assignment_search_params (dict): Optional dictionary of search
            parameters

    Returns:
        A list of dictionaries with the assignment data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Content-Type"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/assignments"

    if not matter_assignment_search_params:
        matter_assignment_search_params = {}

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="assignments",
        params=matter_assignment_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
    )

    return return_data


def search_matter_additional_names(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    matter_additional_names_search_params: dict | None = None,
) -> List[Dict]:
    """Search Additional Names on a given Matter in LegalServer.

    This is a keyword defined function that gets back all of the additional
    names for a client on a case. The services can be filtered in the API call
    based on the search parameters. This uses the Search Matter Additional Names
    API endpoint. They are returned as a list of Additional Names.

    Args:
        legalserver_site (str): required
        legalserver_matter_uuid (str): required
        matter_additional_names_search_params (dict): Optional dictionary of
            search parameters

    Returns:
        A list of dictionaries with the additional names data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Content-Type"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/additional_names"

    if not matter_additional_names_search_params:
        matter_additional_names_search_params = {}

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="additional_names",
        params=matter_additional_names_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
    )

    return return_data


def search_matter_non_adverse_parties(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    matter_non_adverse_parties_search_params: dict | None = None,
) -> List[Dict]:
    """Search Non-Adverse Parties on a given Matter in LegalServer.

    This is a keyword defined function that gets back all of the non-adverse parties
    on a case. The non-adverse parties can be filtered in the API call based on the
    search parameters. This uses the Search Matter Non-Adverse Parties API endpoint.
    They are returned as a list of Non-Adverse Parties.

    Args:
        legalserver_site (str): required
        legalserver_matter_uuid (str): required
        matter_non_adverse_parties_search_params (dict): Optional dictionary of search parameters

    Returns:
        A list of dictionaries with the Adverse Parties data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Content-Type"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/non_adverse_parties"

    if not matter_non_adverse_parties_search_params:
        matter_non_adverse_parties_search_params = {}

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="adverse_parties",
        params=matter_non_adverse_parties_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
    )

    return return_data


def search_matter_adverse_parties(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    matter_adverse_parties_search_params: dict | None = None,
) -> List[Dict]:
    """Search Adverse Parties on a given Matter in LegalServer.

    This is a keyword defined function that gets back all of the adverse parties
    on a case. The adverse parties can be filtered in the API call based on the
    search parameters. This uses the Search Matter Adverse Parties API endpoint.
    They are returned as a list of Adverse Parties.

    Args:
        legalserver_site (str): required
        legalserver_matter_uuid (str): required
        matter_adverse_parties_search_params (dict): Optional dictionary of search parameters

    Returns:
        A list of dictionaries with the Adverse Parties data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Content-Type"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/adverse_parties"

    if not matter_adverse_parties_search_params:
        matter_adverse_parties_search_params = {}

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="adverse_parties",
        params=matter_adverse_parties_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
    )

    return return_data


def search_user_organization_affiliation(
    *,
    legalserver_site: str,
    legalserver_user_uuid: str,
) -> List[Dict]:
    """Search Organization Affiliations on a given User in LegalServer.

    This is a keyword defined function that gets back all of the organization affiliation records
    on a user. This uses the Search User Organization Affiliation API endpoint.
    They are returned as a list of Organization Affiliations.

    Args:
        legalserver_site (str): required
        legalserver_user_uuid (str): required

    Returns:
        A list of dictionaries with the Adverse Parties data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Content-Type"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/users/{legalserver_user_uuid}/organization_affiliation"

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="organization_affiliation",
        params={},
        legalserver_site=legalserver_site,
        header_content=header_content,
    )

    return return_data


def get_user_details(
    *,
    legalserver_site: str,
    legalserver_user_uuid: str,
    custom_fields: list | None = None,
) -> Dict:
    """Get Details on a specific LegalServer user.

    This is a keyword defined function that gets back all of the details on a
    specific LegalServer user. Additional custom fields can be retrieved. This
    uses the Get User API endpoint.

    This makes a followup API call to get the organization affiliation data for
    the same user before returning all of that data in the response.

    Args:
        legalserver_site (str): required
        legalserver_user_uuid (str): required
        custom_fields (list): Optional list to include any custom fields

    Returns:
        A dictionary with the specific user data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Content-Type"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/users/{legalserver_user_uuid}"
    queryparam_data = {}

    if custom_fields:
        queryparam_data["custom_fields"] = custom_fields

    return_data = get_legalserver_response(
        url=url,
        params=queryparam_data,
        legalserver_site=legalserver_site,
        source_type="user",
        header_content=header_content,
        uuid=legalserver_user_uuid,
    )

    return_data["organization_affiliation"] = search_user_organization_affiliation(
        legalserver_site=legalserver_site,
        legalserver_user_uuid=legalserver_user_uuid,
    )

    return return_data


def search_user_data(
    *,
    legalserver_site: str,
    user_search_params: dict | None = None,
    custom_fields: list | None = None,
) -> List[Dict]:
    """Search LegalServer Users with a set of search parameters.

    This uses LegalServer's Search Users API to get back details of users that
    match certain parameters.

    Args:
        legalserver_site (str): The specific LegalServer site to
            check for the organization on.
        user_search_params (dict): The search parameters to use to find the
            users.
        custom_fields (list): A optional list of custom fields to include.

    Returns:
        A list of dictionaries for the identified users.

    Raises:
        Errors are handled in the response. Errors will be present when the
        dictionary response includes a key of 'error'
    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Content-Type"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/users"
    if not user_search_params:
        user_search_params = {}
    if custom_fields:
        user_search_params["custom_fields"] = custom_fields

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="user",
        params=user_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
    )

    return return_data


def get_contact_details(
    *,
    legalserver_site: str,
    legalserver_contact_uuid: str,
    custom_fields: list | None = None,
) -> Dict:
    """Get details about a specific Contact record in LegalServer.

    This uses LegalServer's Get Contact API to get back details of just
    one specific of contact record.

    Args:
        legalserver_site (str): The specific LegalServer site to
            check for the organization on.
        legalserver_contact_uuid (dict): The UUID of the specific LegalServer
            contact to retrieve
        custom_fields (list): A optional list of custom fields to include.

    Returns:
        A dictionary for the specific contact.

    Raises:
        Errors are handled in the response. Errors will be present when the
        dictionary response includes a key of 'error'
    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Content-Type"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/contacts/{legalserver_contact_uuid}"

    queryparam_data = {}
    if custom_fields:
        queryparam_data["custom_fields"] = custom_fields

    return_data = get_legalserver_response(
        url=url,
        params=queryparam_data,
        legalserver_site=legalserver_site,
        source_type="contacts",
        header_content=header_content,
        uuid=legalserver_contact_uuid,
    )

    return return_data


def get_legalserver_response(
    url: str,
    params: Dict,
    legalserver_site: str,
    uuid: str,
    header_content: Dict,
    source_type: str,
) -> Dict:
    """Helper function to properly get a specific piece of LegalServer data."""
    return_data = {}
    try:
        log(
            f"Get {source_type} request of {uuid} on: {legalserver_site} "
            f"included a request for custom fields: {str(params)}"
        )
        response = requests.get(
            url, params=params, headers=header_content, timeout=(3, 30)
        )
        response.raise_for_status()
        if response.status_code != 200:
            return_data = {"error": response.status_code}
            log(
                f"Error getting LegalServer {source_type} data for {uuid} "
                f"on {legalserver_site}. {str(response.status_code)}: "
                f"{str(response.json())}"
            )
        else:
            log(
                f"Got LegalServer {source_type} data for {uuid} on "
                f"{legalserver_site}. Response {str(response.status_code)}"
            )
            return_data = response.json().get("data")
    except requests.exceptions.ConnectionError as e:
        log(
            f"Error getting LegalServer {source_type} data for {uuid} "
            f"on {legalserver_site} while requesting these custom "
            f"fields: {str(params)}. Exception raised: {str(e)}."
        )
        return {"error": e}
    except requests.exceptions.HTTPError as e:
        log(
            f"Error getting LegalServer {source_type} data for {uuid} "
            f"on {legalserver_site} while requesting these custom "
            f"fields: {str(params)}. Exception raised: {str(e)}."
        )
        return {"error": e}
    except requests.exceptions.Timeout as e:
        log(
            f"Error getting LegalServer {source_type} data for {uuid} "
            f"on {legalserver_site} while requesting these custom "
            f"fields: {str(params)}. Exception raised: {str(e)}."
        )
        return {"error": e}
    except Exception as e:
        log(
            f"Error getting LegalServer {source_type} data for {uuid} "
            f"on {legalserver_site} while requesting these custom "
            f"fields: {str(params)}. Exception raised: {str(e)}."
        )
        return {"error": e}
    return return_data


def search_contact_data(
    *,
    legalserver_site: str,
    contact_search_params: dict | None = None,
    custom_fields=[],
) -> List[Dict]:
    """Search Contacts in LegalServer for a set of search parameters.

    This uses LegalServer's Search Contacts API to get back details of any
    contact records that match a set of parameters.

    Args:
        legalserver_site (str): The specific LegalServer site to
            check for the organization on.
        contact_search_params (dict): The specific parameters to search for when
            looking at contacts.
        custom_fields (list): A optional list of custom fields to include.

    Returns:
        A list of dictionaries for the matching contacts.

    Raises:
        Errors are handled in the response. Errors will be present when the
        dictionary response includes a key of 'error'
    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Content-Type"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/contacts"
    if not contact_search_params:
        contact_search_params = {}
    if custom_fields:
        contact_search_params["custom_fields"] = custom_fields

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="contact",
        params=contact_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
    )

    return return_data


def loop_through_legalserver_responses(
    url: str,
    params: Dict,
    header_content: Dict,
    source_type: str,
    legalserver_site: str,
) -> List:
    """Helper function to properly loop through LegalServer Search Responses."""
    return_data = []
    total_number_of_pages = 1
    counter = 0

    while counter < total_number_of_pages and total_number_of_pages > 0:
        try:
            log(
                f"Search {source_type} records with params: {str(params)} on: " f"{url}"
            )
            response = requests.get(
                url, params=params, headers=header_content, timeout=(3, 30)
            )
            response.raise_for_status()
            if response.status_code != 200:
                return_data = [{"error": response.status_code}]
                log(
                    f"Error searching LegalServer {source_type} data for params:"
                    f" {str(params)} on {url}. {str(response.status_code)}: "
                    f"{str(response.json())}"
                )
                break
            else:
                log(
                    f"Got LegalServer {source_type} data for params: {str(params)} "
                    f"on {url}. Response {str(response.status_code)}"
                )
                return_data.extend(response.json().get("data"))
                if response.json().get("total_number_of_pages") is not None:
                    total_number_of_pages = response.json().get("total_number_of_pages")
                    counter += 1
                    params["page_number"] = counter + 1
                else:
                    break
        except requests.exceptions.ConnectionError as e:
            log(
                f"Error getting LegalServer {source_type} data for {str(params)} "
                f"on {url}. Exception raised: {str(e)}."
            )
            return [{"error": e}]
        except requests.exceptions.HTTPError as e:
            log(
                f"Error getting LegalServer {source_type} data for {str(params)} "
                f"on {url}. Exception raised: {str(e)}."
            )
            return [{"error": e}]
        except requests.exceptions.Timeout as e:
            log(
                f"Error getting LegalServer {source_type} data for {str(params)} "
                f"on {url}. Exception raised: {str(e)}."
            )
            return [{"error": e}]
        except Exception as e:
            log(
                f"Error searching LegalServer {source_type} data for {str(params)} "
                f"on {url}. Exception raised: {str(e)}."
            )
            return [{"error": "Unknown"}]
    return return_data


def search_task_data(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str | None = None,
    task_search_params: dict | None = None,
    custom_fields=[],
) -> List[Dict]:
    """Search task data in LegalServer for a specific matter.

    This uses LegalServer's Search tasks API to get back details of any tasks
    that match a given set of parameters. Typically, this will be limited to a
    single case using the matter's UUID, but it does not have to be limited.

    Args:
        legalserver_site (str): The specific LegalServer site to
            check for the organization on.
        legalserver_matter_uuid (dict): The UUID of the specific LegalServer
            organization to retrieve
        task_search_params (dict): A dictionary of search parameters to filter
            for in the request.
        custom_fields (list): A optional list of custom fields to include.

    Returns:
        A list of dictionaries of matching tasks.

    Raises:
        Errors are handled in the response. Errors will be present when the
        dictionary response includes a key of 'error'
    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Content-Type"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/tasks"
    if not task_search_params:
        task_search_params = {}
    if legalserver_matter_uuid:
        task_search_params["matters"] = legalserver_matter_uuid
    if custom_fields:
        task_search_params["custom_fields"] = custom_fields

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="tasks",
        params=task_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
    )

    return return_data


def populate_tasks(
    *,
    task_list: DAList,
    legalserver_data: dict | None = None,
    legalserver_matter_uuid: str = "",
    legalserver_site: str = "",
) -> DAList:
    """Take the data from LegalServer and populate a list of LegalServer tasks
    into a DAList of DAObjects.

    This is a keyword defined function that takes a DAList of DAObjects and
    populates it with the task details related to a case. If the general
    legalserver_data from the `get_matter_details` response is not included, it
    makes an API call using the `search_task_data` function.

    Args:
        task_list (DAList[DAObject]): DAList of DAObjects.
        legalserver_data (dict): Optional dictionary of the matter data from a
            LegalServer request.
        legalserver_matter_uuid (str): needed if the `legalserver_data` is not
            provided.
        legalserver_site (str): needed if the `legalserver_data` is
            not provided.

    Returns:
        A DAList of DAObjects with each being a separate income record."""

    source = get_source_module_data(
        source_type="tasks",
        legalserver_data=legalserver_data,
        legalserver_matter_uuid=legalserver_matter_uuid,
        legalserver_site=legalserver_site,
    )

    if source:
        for item in source:
            if isinstance(item, dict):
                # item: DAObject = item  # type annotation
                new_task = task_list.appendObject()
                new_task.id = item.get("id")
                new_task.uuid = item.get("task_uuid")
                if item.get("title") is not None:
                    new_task.title = item.get("title")
                if item.get("list_date") is not None:
                    new_task.list_date = item.get("list_date")
                if item.get("due_date") is not None:
                    new_task.due_date = item.get("due_date")
                if item.get("active") is not None:
                    new_task.active = item.get("active")
                if item.get("task_type") is not None:
                    if item["task_type"].get("lookup_value_name") is not None:
                        new_task.task_type = item["task_type"].get("lookup_value_name")
                if item.get("deadline_type") is not None:
                    if item["deadline_type"].get("lookup_value_name") is not None:
                        new_task.deadline_type = item["deadline_type"].get(
                            "lookup_value_name"
                        )
                if item.get("deadline") is not None:
                    new_task.deadline = item.get("deadline")
                if item.get("private") is not None:
                    new_task.private = item.get("private")
                if item.get("completed") is not None:
                    new_task.completed = item.get("completed")
                if item.get("completed_by") is not None:
                    if item["completed_by"].get("user_uuid") is not None:
                        new_task.completed_by_uuid = item["completed_by"].get(
                            "user_uuid"
                        )
                    if item["completed_by"].get("user_name") is not None:
                        new_task.completed_by_name = item["completed_by"].get(
                            "user_name"
                        )
                if item.get("completed_date") is not None:
                    new_task.completed_date = item.get("completed_date")

                temp_list = []
                for user in item["users"]:
                    if user.get("user_uuid") is not None:
                        temp_list.append(
                            {
                                "user_uuid": user.get("user_uuid"),
                                "user_name": user.get("user_name"),
                            }
                        )
                if temp_list:
                    new_task.users = temp_list
                del temp_list

                if item.get("dynamic_process") is not None:
                    if item["dynamic_process"].get("dynamic_process_id") is not None:
                        new_task.dynamic_process_id = item["dynamic_process"].get(
                            "dynamic_process_id"
                        )
                    if item["dynamic_process"].get("dynamic_process_uuid") is not None:
                        new_task.dynamic_process_uuid = item["dynamic_process"].get(
                            "dynamic_process_uuid"
                        )
                    if item["dynamic_process"].get("dynamic_process_name") is not None:
                        new_task.dynamic_process_name = item["dynamic_process"].get(
                            "dynamic_process_name"
                        )
                if item.get("is_this_a_case_alert") is not None:
                    new_task.is_this_a_case_alert = item.get("is_this_a_case_alert")
                if item.get("statute_of_limitations") is not None:
                    new_task.statute_of_limitations = item.get("statute_of_limitations")
                if item.get("created_date") is not None:
                    new_task.created_date = item.get("created_date")
                if item.get("created_by") is not None:
                    if item["created_by"].get("user_uuid") is not None:
                        new_task.created_by_uuid = item["created_by"].get("user_uuid")
                    if item["created_by"].get("user_name") is not None:
                        new_task.created_by_name = item["created_by"].get("user_name")
                if item["program"].get("lookup_value_name") is not None:
                    new_task.program = item["program"].get("lookup_value_name")
                if item.get("office") is not None:
                    if item["office"].get("office_name") is not None:
                        new_task.office_name = item["office"].get("office_name")
                    if item["office"].get("office_code") is not None:
                        new_task.office_code = item["office"].get("office_code")

                standard_key_list = standard_task_keys()
                custom_fields = {
                    key: value
                    for key, value in item.items()
                    if key not in standard_key_list
                }
                if custom_fields is not None:
                    new_task.custom_fields = custom_fields
                del custom_fields
                new_task.complete = True

    task_list.gathered = True
    return task_list


def search_event_data(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str | None = None,
    event_search_params: dict | None = None,
    custom_fields=[],
) -> List[Dict]:
    """Search event data in LegalServer for a specific matter.

    This uses LegalServer's Search Events API to get back details of any events
    that match a given set of parameters. Typically, this will be limited to a
    single case using the matter's UUID, but it does not have to be limited.

    Args:
        legalserver_site (str): The specific LegalServer site to
            check for the organization on.
        legalserver_matter_uuid (dict): The UUID of the specific LegalServer
            organization to retrieve
        event_search_params (dict): A dictionary of search parameters to filter
            for in the request.
        custom_fields (list): A optional list of custom fields to include.

    Returns:
        A list of dictionaries of matching events.

    Raises:
        Errors are handled in the response. Errors will be present when the
        dictionary response includes a key of 'error'
    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Content-Type"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/events"
    if not event_search_params:
        event_search_params = {}
    if legalserver_matter_uuid:
        event_search_params["matters"] = legalserver_matter_uuid
    if custom_fields:
        event_search_params["custom_fields"] = custom_fields

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="events",
        params=event_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
    )

    return return_data


def populate_events(
    *,
    event_list: DAList,
    legalserver_data: dict | None = None,
    legalserver_matter_uuid: str = "",
    legalserver_site: str = "",
) -> DAList:
    """Take the data from LegalServer and populate a list of LegalServer events
    into a DAList of DAObjects.

    This is a keyword defined function that takes a DAList of DAObjects and
    populates it with the event details related to a case. If the general
    legalserver_data from the `get_matter_details` response is not included, it
    makes an API call using the `search_event_data` function. Note that this
    ignores the `outreaches` key in the event response since this is designed to
    connect cases to events and does not currently cover outreaches.

    Args:
        event_list (DAList[DAObject]): DAList of DAObjects.
        legalserver_data (dict): Optional dictionary of the matter data from a
            LegalServer request.
        legalserver_matter_uuid (str): needed if the `legalserver_data` is not
            provided.
        legalserver_site (str): needed if the `legalserver_data` is
            not provided.

    Returns:
        A DAList of DAObjects with each being a separate event record."""

    source = get_source_module_data(
        source_type="events",
        legalserver_data=legalserver_data,
        legalserver_matter_uuid=legalserver_matter_uuid,
        legalserver_site=legalserver_site,
    )

    if source:
        for item in source:
            if isinstance(item, dict):
                # item: DAObject = item  # type annotation
                new_event = event_list.appendObject()
                new_event.id = item.get("id")
                new_event.uuid = item.get("event_uuid")
                if item.get("title") is not None:
                    new_event.title = item.get("title")
                if item.get("location") is not None:
                    new_event.location = item.get("location")
                if item.get("front_desk") is not None:
                    new_event.front_desk = item.get("front_desk")
                if item.get("broadcast_event") is not None:
                    new_event.broadcast_event = item.get("broadcast_event")
                if item.get("court") is not None:
                    if item["court"].get("organization_name") is not None:
                        new_event.court_name = item["court"].get("organization_name")
                    if item["court"].get("organization_uuid") is not None:
                        new_event.court_uuid = item["court"].get("organization_uuid")
                if item.get("courtroom") is not None:
                    new_event.courtroom = item.get("courtroom")
                if item["event_type"].get("lookup_value_name") is not None:
                    new_event.event_type = item["event_type"].get("lookup_value_name")
                if item.get("judge") is not None:
                    new_event.judge = item.get("judge")
                if item.get("attendees") is not None:
                    new_event.attendees = item.get("attendees")
                if item.get("private_event") is not None:
                    new_event.private_event = item.get("private_event")
                temp_list = []
                for user in item["attendees"]:
                    if user.get("user_uuid") is not None:
                        temp_list.append(
                            {
                                "user_uuid": user.get("user_uuid"),
                                "user_name": user.get("user_name"),
                            }
                        )
                if temp_list:
                    new_event.attendees = temp_list
                del temp_list

                if item.get("dynamic_process_id") is not None:
                    if item["dynamic_process_id"].get("dynamic_process_id") is not None:
                        new_event.dynamic_process_id = item["dynamic_process_id"].get(
                            "dynamic_process_id"
                        )
                    if (
                        item["dynamic_process_id"].get("dynamic_process_uuid")
                        is not None
                    ):
                        new_event.dynamic_process_uuid = item["dynamic_process_id"].get(
                            "dynamic_process_uuid"
                        )
                    if (
                        item["dynamic_process_id"].get("dynamic_process_name")
                        is not None
                    ):
                        new_event.dynamic_process_name = item["dynamic_process_id"].get(
                            "dynamic_process_name"
                        )
                # start and end dates of None if not otherwise
                # if item.get("start_datetime") is not None:
                new_event.start_datetime = item.get("start_datetime")
                # if item.get("end_datetime") is not None:
                new_event.end_datetime = item.get("end_datetime")
                if item.get("all_day_event") is not None:
                    new_event.all_day_event = item.get("all_day_event")
                if item["program"].get("lookup_value_name") is not None:
                    new_event.program = item["program"].get("lookup_value_name")
                if item.get("office") is not None:
                    if item["office"].get("office_name") is not None:
                        new_event.office_name = item["office"].get("office_name")
                    if item["office"].get("office_code") is not None:
                        new_event.office_code = item["office"].get("office_code")

                standard_key_list = standard_event_keys()
                custom_fields = {
                    key: value
                    for key, value in item.items()
                    if key not in standard_key_list
                }
                if custom_fields is not None:
                    new_event.custom_fields = custom_fields
                del custom_fields
                new_event.complete = True

    event_list.gathered = True
    return event_list


def populate_income(
    *,
    income_list: DAList,
    legalserver_data: dict | None = None,
    legalserver_matter_uuid: str = "",
    legalserver_site: str = "",
) -> DAList:
    """Take the data from LegalServer and populate a list of LegalServer income
        records into a DAList of DAObjects.

        This is a keyword defined function that takes a DAList of DAObjects and
    populates it with the income details related to a case. If the general
    legalserver_data from the `get_matter_details` response is not included, it
    would make an API call using the `search_income_data` function. Unfortunately,
    the Search Income API endpoint does not currently exist.

        Args:
            income_list (DAList[DAObject]): DAList of DAObjects.
            legalserver_data (dict): Optional dictionary of the matter data from a
                LegalServer request.
            legalserver_matter_uuid (str): needed if the `legalserver_data` is not
                provided.
            legalserver_site (str): needed if the `legalserver_data` is
                not provided.

        Returns:
            A DAList of DAObjects with each being a separate income record.
    """

    source = get_source_module_data(
        source_type="incomes",
        legalserver_data=legalserver_data,
        legalserver_matter_uuid=legalserver_matter_uuid,
        legalserver_site=legalserver_site,
    )

    if source:
        for item in source:
            # item: DAObject = item # type annotation
            new_income = income_list.appendObject()
            new_income.income_uuid = item.get("income_uuid")
            new_income.id = item.get("id")
            if item.get("family_id") is not None:
                new_income.family_id = item.get("family_id")
            if item.get("other_family") is not None:
                new_income.other_family = item.get("other_family")
            if item.get("type") is not None:
                if item["type"].get("lookup_value_name") is not None:
                    new_income.type = item["type"].get("lookup_value_name")
            if item.get("amount") is not None:
                new_income.amount = item.get("amount")
            if item.get("period") is not None:
                new_income.period = item.get("period")
            if item.get("notes") is not None:
                new_income.notes = item.get("notes")
            if item.get("imported") is not None:
                new_income.imported = item.get("imported")
            if item.get("exclude") is not None:
                new_income.exclude = item.get("exclude")
            new_income.complete = True

    income_list.gathered = True
    return income_list


def populate_additional_names(
    *,
    additional_name_list: DAList,
    legalserver_data: dict | None = None,
    legalserver_matter_uuid: str = "",
    legalserver_site: str = "",
) -> DAList:
    """Take the data from LegalServer and populate a list of LegalServer
    Additional Name records into a DAList of IndividualName.

    This is a keyword defined function that takes a DAList of IndividualNames
    and populates it with the contact details related to a case. If the general
    legalserver_data from the `get_matter_details` response is not included, it
    will make an API call using the `search_matter_additional_names` function.
    Since the standard response from the `get_matter_details` does not include
    this data, it will always make that call.

    Args:
        additional_name_list (DAList[IndividualName]): required DAList of
            IndividualName for the contacts.
        legalserver_data (dict): Optional dictionary of the matter data from a
            LegalServer request.
        legalserver_matter_uuid (str):needed if the `legalserver_data` is not
            provided.
        legalserver_site (str):needed if the `legalserver_data` is
            not provided.

    Returns:
        A populated DAList of IndividualName objects.
    """

    source = get_source_module_data(
        source_type="additional_names",
        legalserver_data=legalserver_data,
        legalserver_matter_uuid=legalserver_matter_uuid,
        legalserver_site=legalserver_site,
    )

    if source:
        for item in source:
            # item: DAObject = item # type annotation
            new_name = additional_name_list.appendObject(IndividualName)
            new_name.uuid = item.get("uuid")
            new_name.id = item.get("id")
            if item.get("first") is not None:
                new_name.first = item.get("first")
            if item.get("middle") is not None:
                new_name.middle = item.get("middle")
            if item.get("type") is not None:
                if item["type"].get("lookup_value_name") is not None:
                    new_name.type = item["type"].get("lookup_value_name")
            if item.get("last") is not None:
                new_name.last = item.get("last")
            if item.get("suffix") is not None:
                new_name.suffix = item.get("suffix")

            new_name.complete = True

    additional_name_list.gathered = True
    return additional_name_list


def populate_adverse_parties(
    *,
    adverse_party_list: DAList,
    legalserver_data: dict | None = None,
    legalserver_matter_uuid: str = "",
    legalserver_site: str = "",
) -> DAList:
    """Take the data from LegalServer and populate a list of LegalServer
    Adverse Partyrecords into a DAList of Persons.

    This is a keyword defined function that takes a DAList of Persons
    and populates it with the adverse party details related to a case. If the general
    legalserver_data from the `get_matter_details` response is not included, it
    will make an API call using the `search_matter_adverse_parties` function.
    Since the standard response from the `get_matter_details` does not always
    include this data, it will always make that call.

    Args:
        adverse_party_list (DAList[Person]): required DAList of
            Persons for the Adverse Parties.
        legalserver_data (dict): Optional dictionary of the matter data from a
            LegalServer request.
        legalserver_matter_uuid (str):needed if the `legalserver_data` is not
            provided.
        legalserver_site (str):needed if the `legalserver_data` is
            not provided.

    Returns:
        A populated DAList of Person objects.
    """

    source = get_source_module_data(
        source_type="adverse_parties",
        legalserver_data=legalserver_data,
        legalserver_matter_uuid=legalserver_matter_uuid,
        legalserver_site=legalserver_site,
    )

    if source:
        for item in source:
            # item: DAObject = item # type annotation
            new_ap = adverse_party_list.appendObject(Individual)
            new_ap.uuid = item.get("uuid")
            new_ap.id = item.get("id")
            if item.get("organization_name") is None:
                new_ap.initializeAttribute("name", IndividualName)
                if item.get("first") is not None:
                    new_ap.name.first = item.get("first")
                if item.get("middle") is not None:
                    new_ap.name.middle = item.get("middle")
                if item.get("last") is not None:
                    new_ap.name.last = item.get("last")
                if item.get("suffix") is not None:
                    new_ap.name.suffix = item.get("suffix")
            else:
                new_ap.name = item.get("organization_name")
            if item.get("business_type") is not None:
                if item.get("business_type").get("lookup_value_name") is not None:
                    new_ap.business_type = item["business_type"].get(
                        "lookup_value_name"
                    )
            if item.get("date_of_birth") is not None:
                new_ap.date_of_birth = item.get("date_of_birth")
            if item.get("approximate_dob") is not None:
                new_ap.approximate_dob = item.get("approximate_dob")
            if item.get("relationship_type") is not None:
                if item["relationship_type"].get("lookup_value_name") is not None:
                    new_ap.relationship_type = item["relationship_type"].get(
                        "lookup_value_name"
                    )
            if item.get("language") is not None:
                if item["language"].get("lookup_value_name") is not None:
                    new_ap.language_name = item["language"].get("lookup_value_name")
                    if (
                        language_code_from_name(
                            item["language"].get("lookup_value_name")
                        )
                        != "Unknown"
                    ):
                        new_ap.language = language_code_from_name(
                            item["language"].get("lookup_value_name")
                        )
            if item.get("height") is not None:
                new_ap.height = item.get("height")
            if item.get("weight") is not None:
                new_ap.weight = item.get("weight")
            if item.get("eye_color") is not None:
                new_ap.eye_color = item.get("eye_color")
            if item.get("hair_color") is not None:
                new_ap.hair_color = item.get("hair_color")
            if item.get("race") is not None:
                if item["race"].get("lookup_value_name") is not None:
                    new_ap.race = item["race"].get("lookup_value_name")
            if item.get("drivers_license") is not None:
                new_ap.drivers_license = item.get("drivers_license")
            if item.get("visa_number") is not None:
                new_ap.visa_number = item.get("visa_number")
            if item.get("immigration_status") is not None:
                if item["immigration_status"].get("lookup_value_name") is not None:
                    new_ap.immigration_status = item["immigration_status"].get(
                        "lookup_value_name"
                    )
            if item.get("marital_status") is not None:
                if item["marital_status"].get("lookup_value_name") is not None:
                    new_ap.marital_status = item["marital_status"].get(
                        "lookup_value_name"
                    )
            if item.get("gender") is not None:
                if item["gender"].get("lookup_value_name") is not None:
                    new_ap.gender = item["gender"].get("lookup_value_name")
            if item.get("ssn") is not None:
                new_ap.ssn = item.get("ssn")
            if item.get("government_generated_id") is not None:
                # this is a list in the response, but it is not a list of lookups.
                if len(item.get("government_generated_id")) > 0:
                    new_ap.government_generated_id = item.get("government_generated_id")
            if item.get("street_address") is not None:
                new_ap.address.address = item.get("street_address")
            if item.get("apt_num") is not None:
                new_ap.address.unit = item.get("apt_num")
            if item.get("street_address_2") is not None:
                new_ap.address.street_2 = item.get("street_address_2")
            if item.get("addr2") is not None:
                new_ap.address.addr2 = item.get("addr2")
            if item.get("city") is not None:
                new_ap.address.city = item.get("city")
            if item.get("state") is not None:
                new_ap.address.state = item.get("state")
            if item.get("zip_code") is not None:
                new_ap.address.zip = item.get("zip_code")
            if item.get("county") is not None:
                if item["county"].get("lookup_value_name") is not None:
                    new_ap.address.county = item["county"].get("lookup_value_name")
                    new_ap.address.county_uuid = item["county"].get("lookup_value_uuid")
                    if item["county"].get("lookup_value_state") is not None:
                        new_ap.address.county_state = item["county"].get(
                            "lookup_value_state"
                        )
                    if item["county"].get("lookup_value_FIPS") is not None:
                        new_ap.address.county_FIPS = item["county"].get(
                            "lookup_value_FIPS"
                        )
            if item.get("phone_home") is not None:
                new_ap.phone_home = item.get("phone_home")
            if item.get("phone_home_note") is not None:
                new_ap.phone_home_note = item.get("phone_home_note")
            if item.get("phone_business") is not None:
                new_ap.phone_business = item.get("phone_business")
            if item.get("phone_business_note") is not None:
                new_ap.phone_business_note = item.get("phone_business_note")
            if item.get("phone_mobile") is not None:
                new_ap.phone_mobile = item.get("phone_mobile")
            if item.get("phone_mobile_note") is not None:
                new_ap.phone_mobile_note = item.get("phone_mobile_note")
            if item.get("phone_fax") is not None:
                new_ap.phone_fax = item.get("phone_fax")
            if item.get("phone_fax_note") is not None:
                new_ap.phone_fax_note = item.get("phone_fax_note")
            if item.get("adverse_party_alert") is not None:
                new_ap.adverse_party_alert = item.get("adverse_party_alert")
            if item.get("adverse_party_note") is not None:
                new_ap.adverse_party_note = item.get("adverse_party_note")
            if item.get("active") is not None:
                new_ap.active = item.get("active")
            if item.get("email") is not None:
                new_ap.email = item.get("email")

            standard_key_list = standard_adverse_party_keys()
            custom_fields = {
                key: value
                for key, value in item.items()
                if key not in standard_key_list
            }
            if custom_fields is not None:
                new_ap.custom_fields = custom_fields
            del custom_fields

            new_ap.complete = True

    adverse_party_list.gathered = True
    return adverse_party_list


def populate_non_adverse_parties(
    *,
    non_adverse_party_list: DAList,
    legalserver_data: dict | None = None,
    legalserver_matter_uuid: str = "",
    legalserver_site: str = "",
) -> DAList:
    """Take the data from LegalServer and populate a list of LegalServer
    Non-Adverse Party records into a DAList of Individuals.

    This is a keyword defined function that takes a DAList of Individuals
    and populates it with the non-adverse party details related to a case. If the
    general legalserver_data from the `get_matter_details` response is not
    included, it will make an API call using the `search_matter_non_adverse_parties`
    function. Since the standard response from the `get_matter_details` does not
    always include this data, it will always make that call.

    Args:
        non_adverse_party_list (DAList[Individual]): required DAList of
            Individuals for the Non-Adverse Parties.
        legalserver_data (dict): Optional dictionary of the matter data from a
            LegalServer request.
        legalserver_matter_uuid (str):needed if the `legalserver_data` is not
            provided.
        legalserver_site (str):needed if the `legalserver_data` is
            not provided.

    Returns:
        A populated DAList of Individual objects.
    """

    source = get_source_module_data(
        source_type="non_adverse_parties",
        legalserver_data=legalserver_data,
        legalserver_matter_uuid=legalserver_matter_uuid,
        legalserver_site=legalserver_site,
    )

    if source:
        for item in source:
            # item: DAObject = item # type annotation
            new_nap = non_adverse_party_list.appendObject(Individual)
            new_nap.uuid = item.get("uuid")
            new_nap.id = item.get("id")
            if item.get("organization_name") is None:
                new_nap.initializeAttribute("name", Individual)
                if item.get("first") is not None:
                    new_nap.name.first = item.get("first")
                if item.get("middle") is not None:
                    new_nap.name.middle = item.get("middle")
                if item.get("last") is not None:
                    new_nap.name.last = item.get("last")
                if item.get("suffix") is not None:
                    new_nap.name.suffix = item.get("suffix")
            else:
                new_nap.name = item.get("organization_name")
            if item.get("date_of_birth") is not None:
                new_nap.date_of_birth = item.get("date_of_birth")
            if item.get("approximate_dob") is not None:
                new_nap.approximate_dob = item.get("approximate_dob")
            if item["relationship_type"].get("lookup_value_name") is not None:
                new_nap.relationship_type = item["relationship_type"].get(
                    "lookup_value_name"
                )
            if item["language"].get("lookup_value_name") is not None:
                new_nap.language_name = item["language"].get("lookup_value_name")
                if (
                    language_code_from_name(item["language"].get("lookup_value_name"))
                    != "Unknown"
                ):
                    new_nap.language = language_code_from_name(
                        item["language"].get("lookup_value_name")
                    )
            if item.get("gender") is not None:
                if item["gender"].get("lookup_value_name") is not None:
                    new_nap.gender = item["gender"].get("lookup_value_name")
            if item.get("ssn") is not None:
                new_nap.ssn = item.get("ssn")
            if item.get("country_of_birth") is not None:
                ## TODO country codes
                if item["country_of_birth"].get("lookup_value_name") is not None:
                    new_nap.country_of_birth_name = item["country_of_birth"].get(
                        "lookup_value_name"
                    )
            if item["race"].get("lookup_value_name") is not None:
                new_nap.race = item["race"].get("lookup_value_name")
            if item.get("veteran") is not None:
                new_nap.veteran = item.get("veteran")
            if item.get("disabled") is not None:
                new_nap.disabled = item.get("disabled")
            if item.get("hud_race") is not None:
                if item["hud_race"].get("lookup_value_name") is not None:
                    new_nap.hud_race = item["hud_race"].get("lookup_value_name")
            if item.get("hud_9902_ethnicity") is not None:
                if item["hud_9902_ethnicity"].get("hud_9902_ethnicity") is not None:
                    new_nap.hud_9902_ethnicity = item["hud_9902_ethnicity"].get(
                        "lookup_value_name"
                    )
            if item.get("hud_disabling_condition") is not None:
                if item["hud_disabling_condition"].get("lookup_value_name") is not None:
                    new_nap.hud_disabling_condition = item[
                        "hud_disabling_condition"
                    ].get("lookup_value_name")
            if item.get("visa_number") is not None:
                new_nap.visa_number = item.get("visa_number")
            if item["immigration_status"].get("lookup_value_name") is not None:
                new_nap.immigration_status = item["immigration_status"].get(
                    "lookup_value_name"
                )
            if item["citizenship_status"].get("lookup_value_name") is not None:
                new_nap.citizenship_status = item["citizenship_status"].get(
                    "lookup_value_name"
                )
            if item["marital_status"].get("lookup_value_name") is not None:
                new_nap.marital_status = item["marital_status"].get("lookup_value_name")
            if item.get("government_generated_id") is not None:
                # this is a list in the response, but it is not a list of lookups.
                if len(item.get("government_generated_id")) > 0:
                    new_nap.government_generated_id = item.get(
                        "government_generated_id"
                    )
            if item.get("street_address") is not None:
                new_nap.address.address = item.get("street_address")
            if item.get("apt_num") is not None:
                new_nap.address.unit = item.get("apt_num")
            if item.get("addr2") is not None:
                new_nap.address.addr2 = item.get("addr2")
            if item.get("city") is not None:
                new_nap.address.city = item.get("city")
            if item.get("state") is not None:
                new_nap.address.state = item.get("state")
            if item.get("zip_code") is not None:
                new_nap.address.zip = item.get("zip_code")
            if item["county"].get("lookup_value_name") is not None:
                new_nap.address.county = item["county"].get("lookup_value_name")
                new_nap.address.county_uuid = item["county"].get("lookup_value_uuid")
                if item["county"].get("lookup_value_state") is not None:
                    new_nap.address.county_state = item["county"].get(
                        "lookup_value_state"
                    )
                if item["county"].get("lookup_value_FIPS") is not None:
                    new_nap.address.county_FIPS = item["county"].get(
                        "lookup_value_FIPS"
                    )
            if item.get("phone_home") is not None:
                new_nap.phone_home = item.get("phone_home")
            if item.get("phone_home_note") is not None:
                new_nap.phone_home_note = item.get("phone_home_note")
            if item.get("phone_business") is not None:
                new_nap.phone_business = item.get("phone_business")
            if item.get("phone_business_note") is not None:
                new_nap.phone_business_note = item.get("phone_business_note")
            if item.get("phone_mobile") is not None:
                new_nap.phone_mobile = item.get("phone_mobile")
            if item.get("phone_mobile_note") is not None:
                new_nap.phone_mobile_note = item.get("phone_mobile_note")
            if item.get("phone_fax") is not None:
                new_nap.phone_fax = item.get("phone_fax")
            if item.get("phone_fax_note") is not None:
                new_nap.phone_fax_note = item.get("phone_fax_note")
            if item.get("family_member") is not None:
                new_nap.family_member = item.get("family_member")
            if item.get("household_member") is not None:
                new_nap.household_member = item.get("household_member")
            if item.get("potential_conflict") is not None:
                new_nap.potential_conflict = item.get("potential_conflict")
            if item.get("non_adverse_party") is not None:
                new_nap.non_adverse_party = item.get("non_adverse_party")
            if item.get("active") is not None:
                new_nap.active = item.get("active")
            if item.get("email") is not None:
                new_nap.email = item.get("email")

            standard_key_list = standard_non_adverse_party_keys()
            custom_fields = {
                key: value
                for key, value in item.items()
                if key not in standard_key_list
            }
            if custom_fields is not None:
                new_nap.custom_fields = custom_fields
            del custom_fields

            new_nap.complete = True

    non_adverse_party_list.gathered = True
    return non_adverse_party_list


def populate_notes(
    *,
    note_list: DAList,
    legalserver_data: dict | None = None,
    legalserver_matter_uuid: str = "",
    legalserver_site="",
) -> DAList:
    """Take the data from LegalServer and populate a list of LegalServer note
    records into a DAList of DAObjects.

    This is a keyword defined function that takes a DAList of DAObjects and
    populates it with the note details related to a case. If the general
    legalserver_data from the `get_matter_details` response is not included, it
    will make an API call using the `search_matter_notes_data` function.

    Args:
        note_list (DAList[DAObject]): DAList of DAObjects.
        legalserver_data (dict): Optional dictionary of the matter data from a
            LegalServer request.
        legalserver_matter_uuid (str): needed if the `legalserver_data` is not
            provided.
        legalserver_site (str): needed if the `legalserver_data` is not
            provided.

    Returns:
        A DAList of DAObjects with a separate DAObject for each note.
    """

    source = get_source_module_data(
        source_type="notes",
        legalserver_data=legalserver_data,
        legalserver_matter_uuid=legalserver_matter_uuid,
        legalserver_site=legalserver_site,
    )
    if source:
        for item in source:
            if isinstance(item, dict):
                # item: DAObject = item  # type annotation
                new_note = note_list.appendObject()
                new_note.casenote_uuid = item.get("casenote_uuid")
                new_note.id = item.get("id")
                if item.get("subject") is not None:
                    new_note.subject = item.get("subject")
                if item.get("body") is not None:
                    new_note.body = item.get("body")
                if item["note_type"].get("lookup_value_name") is not None:
                    new_note.note_type = item["note_type"].get("lookup_value_name")
                if item.get("date_posted") is not None:
                    new_note.date_posted = item.get("date_posted")
                if item.get("date_time_created") is not None:
                    new_note.date_time_created = item.get("date_time_created")
                if item.get("last_update") is not None:
                    new_note.last_update = item.get("last_update")
                if item.get("allow_etransfer") is not None:
                    new_note.allow_etransfer = item.get("allow_etransfer")
                if item.get("active") is not None:
                    new_note.active = item.get("active")
                if item.get("note_was_emailed") is not None:
                    new_note.note_was_emailed = item.get("note_was_emailed")
                if item.get("note_was_messaged") is not None:
                    new_note.note_was_messaged = item.get("note_was_messaged")
                if item.get("note_has_document_attached") is not None:
                    new_note.note_has_document_attached = item.get(
                        "note_has_document_attached"
                    )
                if item.get("created_by") is not None:
                    if item["created_by"].get("user_uuid") is not None:
                        new_note.created_by_uuid = item["created_by"].get("user_uuid")
                    if item["created_by"].get("user_name") is not None:
                        new_note.created_by_name = item["created_by"].get("user_name")
                if item.get("last_updated_by") is not None:
                    if item["last_updated_by"].get("user_uuid") is not None:
                        new_note.last_updated_by_uuid = item["last_updated_by"].get(
                            "user_uuid"
                        )
                    if item["last_updated_by"].get("user_name") is not None:
                        new_note.last_updated_by_name = item["last_updated_by"].get(
                            "user_name"
                        )
                new_note.complete = True
    note_list.gathered = True
    return note_list


def populate_assignments(
    *,
    assignment_list: DAList,
    legalserver_data: dict | None = None,
    legalserver_matter_uuid: str = "",
    legalserver_site: str = "",
) -> DAList:
    """Take the data from LegalServer and populate a list of LegalServer
    Assignment records into a DAList of DAObjects.

    This is a keyword defined function that takes a DAList of DAObjects and
    populates it with the assignment details related to a case. If the general
    legalserver_data from the `get_matter_details` response is not included, it
    will make an API call using the `search_assignment_data` function.

    Args:
        assignment_list (DAList[DAObject]): DAList of DAObjects for the
            Assignments.
        legalserver_data (dict): Optional dictionary of the matter data from a
            LegalServer request.
        legalserver_matter_uuid (str): needed if the `legalserver_data` is not
            provided.
        legalserver_site (str): needed if the `legalserver_data` is
            not provided.

    Returns:
        A DAList of DAObjects.
    """

    source = get_source_module_data(
        source_type="assignments",
        legalserver_data=legalserver_data,
        legalserver_matter_uuid=legalserver_matter_uuid,
        legalserver_site=legalserver_site,
    )

    if source:
        for item in source:
            if isinstance(item, dict):
                # item: DAObject = item  # type annotation
                new_assignment = assignment_list.appendObject()
                new_assignment.uuid = item.get("uuid")
                new_assignment.id = item.get("id")
                new_assignment.type = item["type"].get("lookup_value_name")
                new_assignment.start_date = item.get("start_date")
                new_assignment.end_date = item.get("end_date")
                if item.get("date_requested") is not None:
                    new_assignment.date_requested = item.get("date_requested")
                if item.get("confirmed") is not None:
                    new_assignment.confirmed = item.get("confirmed")
                new_assignment.program = item["program"].get("lookup_value_name")
                if item.get("notes") is not None:
                    new_assignment.notes = item.get("notes")
                if item.get("created_at") is not None:
                    new_assignment.created_at = item.get("created_at")
                if item.get("satisfies_outreach_training_credit") is not None:
                    new_assignment.satisfies_outreach_training_credit = item.get(
                        "satisfies_outreach_training_credit"
                    )
                if item.get("office") is not None:
                    if item["office"].get("office_name") is not None:
                        new_assignment.office_name = item["office"].get("office_name")
                    if item["office"].get("office_code") is not None:
                        new_assignment.office_code = item["office"].get("office_code")
                new_assignment.user_uuid = item["user"].get("user_uuid")
                new_assignment.user_name = item["user"].get("user_name")
                if item.get("assigned_by") is not None:
                    if item["assigned_by"].get("user_uuid") is not None:
                        new_assignment.assigned_by_uuid = item["assigned_by"].get(
                            "user_uuid"
                        )
                    if item["assigned_by"].get("user_name") is not None:
                        new_assignment.assigned_by_name = item["assigned_by"].get(
                            "user_name"
                        )
                new_assignment.complete = True

    assignment_list.gathered = True
    return assignment_list


def populate_litigations(
    *,
    litigation_list: DAList,
    legalserver_data: dict | None = None,
    legalserver_matter_uuid: str = "",
    legalserver_site: str = "",
) -> DAList:
    """Take the data from LegalServer and populate a list of LegalServer
    Litigation records into a DAList of DAObjects.

    This is a keyword defined function that takes a DAList of DAObjects and
    populates it with the litigation details related to a case. If the general
    legalserver_data from the `get_matter_details` response is not included, it will
    make an API call using the `search_matter_litigation_data` function.

    Args:
        litigation_list (DAList[DAObject]): DAList of DAObjects.
        legalserver_data (dict): Optional dictionary of the matter data from a
            LegalServer request.
        legalserver_matter_uuid (str): needed if the `legalserver_data` is not
            provided.
        legalserver_site (str): needed if the `legalserver_data` is
            not provided.
        custom_fields (list): Optional list of field names for custom fields to
            include.

    Returns:
        DAList of DAObjects
    """

    source = get_source_module_data(
        source_type="litigations",
        legalserver_data=legalserver_data,
        legalserver_matter_uuid=legalserver_matter_uuid,
        legalserver_site=legalserver_site,
    )
    if source:
        for item in source:
            if isinstance(item, dict):
                # item: DAObject = item  # type annotation
                new_litigation = litigation_list.appendObject()
                if item.get("litigation_uuid") is not None:
                    new_litigation.litigation_uuid = item.get("litigation_uuid")
                else:
                    new_litigation.litigation_uuid = item.get("uuid")
                if item.get("litigation_id") is not None:
                    new_litigation.litigation_id = item.get("litigation_id")
                else:
                    new_litigation.litigation_id = item.get("id")
                if item.get("court_text") is not None:
                    new_litigation.court_text = item.get("court_text")
                if item.get("court_id") is not None:
                    if item["court_id"].get("organization_name") is not None:
                        new_litigation.court_name = item["court_id"].get(
                            "organization_name"
                        )
                    if item["court_id"].get("organization_uuid") is not None:
                        new_litigation.court_uuid = item["court_id"].get(
                            "organization_uuid"
                        )
                if item.get("court_number") is not None:
                    new_litigation.court_number = item.get("court_number")
                if item.get("caption") is not None:
                    new_litigation.caption = item.get("caption")
                if item.get("docket") is not None:
                    new_litigation.docket = item.get("docket")
                if item.get("cause_of_action") is not None:
                    new_litigation.cause_of_action = item.get("cause_of_action")
                if item.get("judge") is not None:
                    new_litigation.judge = item.get("judge")
                if item.get("adverse_party") is not None:
                    new_litigation.adverse_party = item.get("adverse_party")
                if item.get("notes") is not None:
                    new_litigation.notes = item.get("notes")
                if item.get("outcome") is not None:
                    new_litigation.outcome = item.get("outcome")
                if item.get("outcome_date") is not None:
                    new_litigation.outcome_date = item.get("outcome_date")
                if item.get("default_date") is not None:
                    new_litigation.default_date = item.get("default_date")
                if item.get("date_served") is not None:
                    new_litigation.date_served = item.get("date_served")
                if item.get("date_proceeding_initiated") is not None:
                    new_litigation.date_proceeding_initiated = item.get(
                        "date_proceeding_initiated"
                    )
                if item.get("date_proceeding_concluded") is not None:
                    new_litigation.date_proceeding_concluded = item.get(
                        "date_proceeding_concluded"
                    )
                if item.get("dynamic_process") is not None:
                    if item["dynamic_process"].get("dynamic_process_id") is not None:
                        new_litigation.dynamic_process_id = item["dynamic_process"].get(
                            "dynamic_process_id"
                        )
                    if item["dynamic_process"].get("dynamic_process_uuid") is not None:
                        new_litigation.dynamic_process_uuid = item[
                            "dynamic_process"
                        ].get("dynamic_process_uuid")
                    if item["dynamic_process"].get("dynamic_process_name") is not None:
                        new_litigation.dynamic_process_name = item[
                            "dynamic_process"
                        ].get("dynamic_process_name")
                if item.get("application_filing_date") is not None:
                    new_litigation.application_filing_date = item.get(
                        "application_filing_date"
                    )
                if item.get("court_calendar") is not None:
                    new_litigation.court_calendar = item.get("court_calendar")
                if item.get("lsc_disclosure_required") is not None:
                    new_litigation.lsc_disclosure_required = item.get(
                        "lsc_disclosure_required"
                    )
                if item["litigation_relationship"].get("lookup_value_name") is not None:
                    new_litigation.litigation_relationship = item[
                        "litigation_relationship"
                    ].get("lookup_value_name")
                if item["filing_type"].get("lookup_value_name") is not None:
                    new_litigation.filing_type = item["filing_type"].get(
                        "lookup_value_name"
                    )
                if item.get("number_of_people_served") is not None:
                    new_litigation.number_of_people_served = item.get(
                        "number_of_people_served"
                    )
                standard_key_list = standard_litigation_keys()
                custom_fields = {
                    key: value
                    for key, value in item.items()
                    if key not in standard_key_list
                }
                if custom_fields is not None:
                    new_litigation.custom_fields = custom_fields
                del custom_fields
                new_litigation.complete = True
        log(f"Litigations Populated for a case.")
    litigation_list.gathered = True
    return litigation_list


def standard_litigation_keys() -> List[str]:
    """Return the list of keys present in a Matter Litigation response from
    LegalServer to better identify the custom fields.

    Args:
        None

    Returns:
        A list of strings that match the keys present in the Litigation
        responses.
    """
    standard_litigation_keys = [
        "id",
        "court_text",
        "court_id",
        "court_number",
        "matter_id",
        "matter_identification_number",
        "caption",
        "docket",
        "cause_of_action",
        "judge",
        "adverse_party",
        "notes",
        "outcome",
        "outcome_date",
        "default_date",
        "date_served",
        "date_proceeding_initiated",
        "date_proceeding_concluded",
        "dynamic_process",
        "application_filing_date",
        "court_calendar",
        "lsc_disclosure_required",
        "litigation_relationship",
        "filing_type",
        "number_of_people_served",
        "litigation_uuid",
    ]
    return standard_litigation_keys


def standard_charges_keys() -> List[str]:
    """Return the list of keys present in a Matter Charge response from
    LegalServer to better identify the custom fields.

    Args:
        None.

    Returns:
        A list of strings.
    """
    standard_charges_keys = [
        "id",
        "charge_date",
        "arraignment_date",
        "matter_id",
        "matter_identification_number",
        "warrant_number",
        "charge_category",
        "statute_number",
        "penalty_class",
        "lookup_charge",
        "charge_outcome_id",
        "disposition_date",
        "top_charge",
        "note",
        "previous_charge_id",
        "charge_reduction_date",
        "charge_tag_id",
        "issue_note",
        "dynamic_process",
        "charge_uuid",
    ]
    return standard_charges_keys


def standard_services_keys() -> List[str]:
    """Return the list of keys present in a Matter Services response from
    LegalServer to better identify the custom fields.

    Args:
        None.

    Returns:
        A list of strings.
    """
    standard_services_keys = [
        "id",
        "matter",
        "matter_identification_number",
        "title",
        "type",
        "start_date",
        "end_date",
        "closed_by",
        "note",
        "closed",
        "active",
        "dynamic_process",
        "decision",
        "funding_code",
        "service_uuid",
        "charges",
        "matter_id",
    ]
    return standard_services_keys


def standard_user_keys() -> List[str]:
    """Return the list of keys present in an User response from LegalServer to
    better identify the custom fields.

    Args:
        None.

    Returns:
        A list of strings.
    """
    standard_user_keys = [
        "id",
        "user_uuid",
        "first",
        "middle",
        "last",
        "email",
        "email_allow",
        "login",
        "active",
        "current",
        "contact_active",
        "types",
        "role",
        "gender",
        "race",
        "dob",
        "office",
        "program",
        "date_start",
        "date_end",
        "dynamic_process",
        "date_graduated",
        "date_bar_join",
        "bar_number",
        "date_joined_panel",
        "external_unique_id",
        "additional_programs",
        "additional_offices",
        "external_guid",
        "highest_court_admitted",
        "languages",
        "phone_business",
        "phone_fax",
        "phone_home",
        "phone_mobile",
        "phone_other",
        "practice_state",
        "member_good_standing",
        "recruitment",
        "salutation",
        "school_attended",
        "bind_work_address_to_organization",
        "hourly_rate",
        "counties",
        "contact_types",
        "address_home",
        "address_work",
        "organization_affiliation",
    ]
    return standard_user_keys


def standard_organization_affiliation_keys() -> List[str]:
    """Return the list of keys present in an User's Organization Affiliation response from LegalServer to
    better identify the fields.

    Args:
        None.

    Returns:
        A list of strings.
    """
    standard_organization_affiliation_keys = [
        "id",
        "organization",
        "organization_date_start",
        "organization_date_end",
        "organization_position",
        "organization_contact",
        "organization_contact_type",
        "assistant",
        "assistant_phone",
        "judicial_assistant",
        "judicial_assistant_phone",
        "organization_affiliation_uuid",
    ]

    return standard_organization_affiliation_keys


def standard_organization_keys() -> List[str]:
    """Return the list of keys present in an Organization response from
    LegalServer to better identify the custom fields.

    Args:
        None.

    Returns:
        A list of strings.
    """
    standard_organization_keys = [
        "id",
        "name",
        "abbreviation",
        "description",
        "types",
        "street",
        "street_2",
        "city",
        "state",
        "phone",
        "fax",
        "referral_contact_phone",
        "referral_contact_email",
        "website",
        "is_master",
        "active",
        "date_org_entered",
        "external_site_uuids",
        "uuid",
        "external_unique_id",
        "parent_organization",
        "dynamic_process",
    ]
    return standard_organization_keys


def standard_client_home_address_keys() -> List[str]:
    """Return the list of keys present in a Client Home Address response from
    LegalServer to better identify the GIS fields.

    Args:
        None.

    Returns:
        A list of strings.
    """
    standard_client_home_address_keys = [
        "street",
        "street_2",
        "apt_num",
        "city",
        "state",
        "zip",
        "county",
        "lon",
        "lat",
        "census_tract",
        "geocoding_failed",
        "state_legislature_district_upper",
        "state_legislature_district_lower",
        "congressional_district",
    ]
    return standard_client_home_address_keys


def standard_contact_keys() -> List[str]:
    """Return the list of keys present in a Contact response from LegalServer to
    better identify the custom fields.

    Args:
        None.

    Returns:
        A list of strings.
    """
    standard_contact_keys = [
        "id",
        "uuid",
        "first",
        "middle",
        "last",
        "suffix",
        "type",
        "active",
        "donation_name",
        "salutation",
        "email",
        "phone_home",
        "phone_home_note",
        "phone_business",
        "phone_business_note",
        "phone_fax",
        "phone_fax_note",
        "phone_other",
        "phone_other_note",
        "phone_mobile",
        "phone_mobile_note",
        "bind_work_address_to_organization",
        "work_address",
        "address_work",
        "bar_number",
        "member_good_standing",
        "date_created",
        "language",
        "email_allow",
        "mail_allow",
        "gender",
        "office",
        "user_profile_exists",
        "user_uuid",
        "dynamic_process",
    ]
    return standard_contact_keys


def standard_event_keys() -> List[str]:
    """Return the list of keys present in an Event response from LegalServer to
    better identify the custom fields.

    Args:
        None.

    Returns:
        A list of strings.
    """
    standard_event_keys = [
        "id",
        "title",
        "location",
        "front_desk",
        "broadcast_event",
        "court",
        "courtroom",
        "event_type",
        "attendees",
        "judge",
        "dynamic_process",
        "start_datetime",
        "end_datetime",
        "all_day_event",
        "program",
        "office",
        "event_uuid",
        "dynamic_process_id",
        "outreaches",
        "private_event",
    ]
    return standard_event_keys


def standard_non_adverse_party_keys() -> List[str]:
    """Return the list of keys present in a Non-Adverse Party List response from
    LegalServer to better identify the custom fields.

    Args:
        None.

    Returns:
        A list of strings.
    """

    standard_non_adverse_party_keys = [
        "first",
        "last",
        "middle",
        "suffix",
        "date_of_birth",
        "approximate_dob",
        "relationship_type",
        "uuid",
        "language",
        "gender",
        "ssn",
        "country_of_birth",
        "race",
        "veteran",
        "disabled",
        "hud_race",
        "hud_9902_ethnicity",
        "hud_disabling_condition",
        "visa_number",
        "immigration_status",
        "citizenship_status",
        "marital_status",
        "government_generated_id",
        "address_party",
        "phone_home",
        "phone_home_note",
        "phone_business",
        "phone_business_note",
        "phone_mobile",
        "phone_mobile_note",
        "phone_fax",
        "phone_fax_note",
        "family_member",
        "household_member",
        "non_adverse_party",
        "potential_conflict",
        "id",
        "active",
        "email",
        "addr2",
        "apt_num",
        "city",
        "county",
        "state",
        "street_address",
        "zip_code",
    ]
    return standard_non_adverse_party_keys


def standard_adverse_party_keys() -> List[str]:
    """Return the list of keys present in an Adverse Party List response from
    LegalServer to better identify the custom fields.

    Args:
        None.

    Returns:
        A list of strings.
    """
    standard_adverse_party_keys = [
        "first",
        "last",
        "middle",
        "suffix",
        "organization_name",
        "business_type",
        "date_of_birth",
        "approximate_dob",
        "relationship_type",
        "uuid",
        "language",
        "height",
        "weight",
        "eye_color",
        "hair_color",
        "race",
        "drivers_license",
        "visa_number",
        "immigration_status",
        "marital_status",
        "government_generated_id",
        "address_party",
        "phone_home",
        "phone_home_note",
        "phone_business",
        "phone_business_note",
        "phone_mobile",
        "phone_mobile_note",
        "phone_fax",
        "phone_fax_note",
        "adverse_party_alert",
        "adverse_party_note",
        "id",
        "active",
        "email",
        "employer",
        "addr2",
        "apt_num",
        "county",
        "gender",
        "ssn",
        "state",
        "street_address",
        "street_address_2",
        "zip_code",
    ]

    return standard_adverse_party_keys


def standard_task_keys() -> List[str]:
    """Return the list of keys present in a Task response from LegalServer to
    better identify the custom fields.

    Args:
        None.

    Returns:
        A list of strings.
    """
    standard_task_keys = [
        "id",
        "active",
        "module",
        "title",
        "list_date",
        "due_date",
        "task_type",
        "deadline",
        "deadline_type",
        "private",
        "completed",
        "completed_by",
        "completed_date",
        "users",
        "dynamic_process_id",
        "is_this_a_case_alert",
        "office",
        "program",
        "statute_of_limitations",
        "created_by",
        "created_date",
        "task_uuid",
    ]
    return standard_task_keys


def standard_matter_keys() -> List[str]:
    """Return the list of keys present in a Matter response from LegalServer to
    better identify the custom fields.

    Args:
        None.

    Returns:
        A list of strings.
    """
    standard_matter_keys = [
        "case_number",
        "case_id",
        "matter_uuid",
        "cause_number",
        "case_email_address",
        "case_title",
        "client_full_name",
        "first",
        "last",
        "middle",
        "suffix",
        "is_group",
        "organization_name",
        "client_email_address",
        "case_disposition",
        "is_this_a_prescreen",
        "prescreen_date",
        "prescreen_user",
        "prescreen_program",
        "prescreen_office",
        "intake_office",
        "intake_program",
        "intake_user",
        "prescreen_screening_status",
        "client_address_home",
        "client_address_mailing",
        "date_opened",
        "date_closed",
        "intake_date",
        "date_rejected",
        "rejected",
        "client_gender",
        "veteran",
        "disabled",
        "preferred_phone_number",
        "home_phone",
        "mobile_phone",
        "other_phone",
        "work_phone",
        "fax_phone",
        "language",
        "second_language",
        "interpreter",
        "county_of_residence",
        "county_of_dispute",
        "legal_problem_code",
        "legal_problem_category",
        "special_legal_problem_code",
        "intake_type",
        "impact",
        "special_characteristics",
        "marital_status",
        "citizenship",
        "citizenship_country",
        "immigration_status",
        "a_number",
        "visa_number",
        "date_of_birth",
        "case_status",
        "close_reason",
        "case_profile_url",
        "pro_bono_opportunity_summary",
        "pro_bono_opportunity_county",
        "pro_bono_opportunity_note",
        "pro_bono_opportunity_available_date",
        "pro_bono_opportunity_placement_date",
        "pro_bono_engagement_type",
        "pro_bono_time_commitment",
        "pro_bono_urgent",
        "pro_bono_interest_cc",
        "pro_bono_skills_developed",
        "pro_bono_appropriate_volunteer",
        "pro_bono_expiration_date",
        "pro_bono_opportunity_status",
        "pro_bono_opportunity_cc",
        "simplejustice_opportunity_legal_topic",
        "simplejustice_opportunity_helped_community",
        "simplejustice_opportunity_skill_type",
        "simplejustice_opportunity_community",
        "level_of_expertise",
        "days_open",
        "percentage_of_poverty",
        "asset_eligible",
        "lsc_eligible",
        "income_eligible",
        "dynamic_process",
        "race",
        "ethnicity",
        "current_living_situation",
        "victim_of_domestic_violence",
        "how_referred",
        "number_of_adults",
        "number_of_children",
        "birth_city",
        "birth_country",
        "drivers_license",
        "highest_education",
        "home_phone_note",
        "work_phone_note",
        "mobile_phone_note",
        "other_phone_note",
        "fax_phone_note",
        "case_restrictions",
        "case_exclusions",
        "exclude_from_search_results",
        "conflict_status_note",
        "conflict_status_note_ap",
        "client_conflict_status",
        "adverse_party_conflict_status",
        "conflict_waived",
        "ap_conflict_waived",
        "ssi_welfare_status",
        "ssi_months_client_has_received_welfare_payments",
        "ssi_welfare_case_num",
        "ssi_section8_housing_type",
        "ssi_eatra",
        "referring_organizations",
        "additional_assistance",
        "pai_case",
        "institutionalized",
        "institutionalized_at",
        "client_approved_transfer",
        "transfer_reject_reason",
        "transfer_reject_notes",
        "prior_client",
        "priorities",
        "asset_assistance",
        "fee_generating",
        "rural",
        "pro_bono_opportunity_guardian_ad_litem_certification_needed",
        "pro_bono_opportunity_summary_of_upcoming_dates",
        "pro_bono_opportunity_summary_of_work_needed",
        "pro_bono_opportunity_special_issues",
        "pro_bono_opportunity_court_and_filing_fee_information",
        "pro_bono_opportunity_paupers_eligible",
        "is_lead_case",
        "lead_case",
        "income_change_significantly",
        "income_change_type",
        "ssn",
        "school_status",
        "employment_status",
        "military_service",
        "sharepoint_site_library",
        "sending_site_identification_number",
        "hud_ami_category",
        "hud_area_median_income_percentage",
        "hud_entity_poverty_band",
        "hud_statewide_median_income_percentage",
        "hud_statewide_poverty_band",
        "assignments",
        "charges",
        "services",
        "litigations",
        "incomes",
        "events",
        "notes",
        "additional_names",
        "adverse_parties",
        "contacts",
        "non_adverse_parties",
        "tasks",
    ]
    return standard_matter_keys


def populate_charges(
    *,
    charge_list: DAList,
    legalserver_data: dict | None = None,
    legalserver_matter_uuid: str = "",
    legalserver_site: str = "",
) -> DAList:
    """Take the data from LegalServer and populate a list of LegalServer Matter
    Charge records into a DAList of DAObjects.

    This is a keyword defined function that takes a DAList of DAObjects and
    populates it with the charge details related to a case. If the general
    legalserver_data from the `get_matter_details` response is not included, it
    will make an API call using the `search_matter_charges_data` function.

    Args:
        charge_list (DAList[DAObjects]): DAList of DAObjects
        legalserver_data (dict): Optional dictionary of the matter data from a
            LegalServer request.
        legalserver_matter_uuid (str): needed if the `legalserver_data` is not
            provided.
        legalserver_site (str): needed if the `legalserver_data` is
            not provided.
        custom_fields (list[str]): Optional list of field names for custom
            fields to include.

    Returns:
        DAList of DAObjects
    """

    source = get_source_module_data(
        source_type="charges",
        legalserver_data=legalserver_data,
        legalserver_matter_uuid=legalserver_matter_uuid,
        legalserver_site=legalserver_site,
    )

    if source:
        for item in source:
            if isinstance(item, dict):
                # item: dict = item  # type annoation
                new_charge = charge_list.appendObject()
                new_charge.id = item.get("id")
                new_charge.uuid = item.get("charge_uuid")
                if item.get("charge_date") is not None:
                    new_charge.charge_date = item.get("charge_date")
                if item.get("arraignment_date") is not None:
                    new_charge.arraignment_date = item.get("arraignment_date")
                if item.get("warrant_number") is not None:
                    new_charge.warrant_number = item.get("warrant_number")
                if item.get("charge_category") is not None:
                    new_charge.charge_category = item.get("charge_category")
                if item.get("statute_number") is not None:
                    new_charge.statute_number = item.get("statute_number")
                if item.get("penalty_class") is not None:
                    new_charge.penalty_class = item.get("penalty_class")
                if item.get("lookup_charge") is not None:
                    if item["lookup_charge"].get("charge_uuid") is not None:
                        new_charge.lookup_charge_uuid = item["lookup_charge"].get(
                            "charge_uuid"
                        )
                    if item["lookup_charge"].get("lookup_charge") is not None:
                        new_charge.lookup_charge = item["lookup_charge"].get(
                            "lookup_charge"
                        )
                if item["charge_outcome_id"].get("lookup_value_name") is not None:
                    new_charge.charge_outcome_id = item["charge_outcome_id"].get(
                        "lookup_value_name"
                    )
                if item.get("disposition_date") is not None:
                    new_charge.disposition_date = item.get("disposition_date")
                if item.get("top_charge") is not None:
                    new_charge.top_charge = item.get("top_charge")
                if item.get("note") is not None:
                    new_charge.note = item.get("note")
                if item["previous_charge_id"].get("lookup_value_name") is not None:
                    new_charge.previous_charge_id = item["previous_charge_id"].get(
                        "lookup_value_name"
                    )
                if item.get("charge_reduction_date") is not None:
                    new_charge.charge_reduction_date = item.get("charge_reduction_date")
                temp_list = []
                for tag in item["charge_tag_id"]:
                    if tag.get("lookup_value_name") is not None:
                        temp_list.append(tag.get("lookup_value_name"))
                if temp_list:
                    new_charge.charge_tag_id = temp_list
                del temp_list
                if item.get("issue_note") is not None:
                    new_charge.issue_note = item.get("issue_note")
                if item.get("dynamic_process") is not None:
                    if item["dynamic_process"].get("dynamic_process_id") is not None:
                        new_charge.dynamic_process_id = item["dynamic_process"].get(
                            "dynamic_process_id"
                        )
                    if item["dynamic_process"].get("dynamic_process_uuid") is not None:
                        new_charge.dynamic_process_uuid = item["dynamic_process"].get(
                            "dynamic_process_uuid"
                        )
                    if item["dynamic_process"].get("dynamic_process_name") is not None:
                        new_charge.dynamic_process_name = item["dynamic_process"].get(
                            "dynamic_process_name"
                        )

                standard_key_list = standard_charges_keys()
                custom_fields = {
                    key: value
                    for key, value in item.items()
                    if key not in standard_key_list
                }
                if custom_fields is not None:
                    new_charge.custom_fields = custom_fields
                del custom_fields
                new_charge.complete = True

    log(f"Charges Populated for a case.")

    charge_list.gathered = True
    return charge_list


def populate_services(
    *,
    services_list: DAList,
    legalserver_data: dict | None = None,
    legalserver_matter_uuid: str = "",
    legalserver_site: str = "",
) -> DAList:
    """Take the data from LegalServer and populate a list of LegalServer Matter
    Service records into a DAList of DAObjects.

    This is a keyword defined function that takes a DAList of DAObjects and
    populates it with the service details related to a case. If the general
    legalserver_data from the `get_matter_details` response is not included, it will
    make an API call using the `search_matter_services_data` function.

    Args:
        service_list (DAList[DAObject]): DAList of DAObjects.
        legalserver_data (dict): Optional dictionary of the matter data from a
            LegalServer request.
        legalserver_matter_uuid (str): needed if the `legalserver_data` is not
            provided.
        legalserver_site (str): needed if the `legalserver_data` is
            not provided.
        custom_fields (list[str]): Optional list of field names for custom
            fields to include.

    Returns:
        A DAList of DAObjects.
    """
    source = get_source_module_data(
        source_type="services",
        legalserver_site=legalserver_site,
        legalserver_data=legalserver_data,
        legalserver_matter_uuid=legalserver_matter_uuid,
    )

    if source:
        for item in source:
            if isinstance(item, dict):
                # item: DAObject = item  # type annotation
                new_service = services_list.appendObject()
                new_service.id = item.get("id")
                new_service.uuid = item.get("uuid")

                if item.get("title") is not None:
                    new_service.title = item.get("title")
                if item.get("start_date") is not None:
                    new_service.start_date = item.get("start_date")
                if item["type"].get("lookup_value_name") is not None:
                    new_service.type = item["type"].get("lookup_value_name")
                if item.get("end_date") is not None:
                    new_service.end_date = item.get("end_date")
                if item.get("closed_by") is not None:
                    if item["closed_by"].get("user_uuid") is not None:
                        new_service.closed_by_uuid = item["closed_by"].get("user_uuid")
                    if item["closed_by"].get("user_name") is not None:
                        new_service.closed_by_name = item["closed_by"].get("user_name")
                if item.get("note") is not None:
                    new_service.note = item.get("note")
                if item.get("closed") is not None:
                    new_service.closed = item.get("closed")
                if item.get("active") is not None:
                    new_service.active = item.get("active")
                if item.get("dynamic_process") is not None:
                    if item["dynamic_process"].get("dynamic_process_id") is not None:
                        new_service.dynamic_process_id = item["dynamic_process"].get(
                            "dynamic_process_id"
                        )
                    if item["dynamic_process"].get("dynamic_process_uuid") is not None:
                        new_service.dynamic_process_uuid = item["dynamic_process"].get(
                            "dynamic_process_uuid"
                        )
                    if item["dynamic_process"].get("dynamic_process_name") is not None:
                        new_service.dynamic_process_name = item["dynamic_process"].get(
                            "dynamic_process_name"
                        )
                if item["decision"].get("lookup_value_name") is not None:
                    new_service.decision = item["decision"].get("lookup_value_name")
                if item.get("funding_code") is not None:
                    new_service.funding_code = item.get("funding_code")
                standard_key_list = standard_services_keys()
                custom_fields = {
                    key: value
                    for key, value in item.items()
                    if key not in standard_key_list
                }
                if custom_fields is not None:
                    new_service.custom_fields = custom_fields
                del custom_fields
                new_service.complete = True
        log(f"Services Populated for a case.")

    services_list.gathered = True
    return services_list


def populate_contacts(
    *,
    contact_list: DAList,
    legalserver_data: dict | None = None,
    legalserver_matter_uuid: str = "",
    legalserver_site: str = "",
) -> DAList:
    """Take the data from LegalServer and populate a list of LegalServer Matter
    Contact records into a DAList of DAObjects.

    This is a keyword defined function that takes a DAList of Individuals and
    populates it with the contact details related to a case. If the general
    legalserver_data from the `get_matter_details` response is not included, it
    will make an API call using the `search_contact_data` function.

    Args:
        contact_list (DAList[Individual]): required DAList of Individuals for
            the contacts.
        legalserver_data (dict): Optional dictionary of the matter data from a
            LegalServer request.
        legalserver_matter_uuid (str): needed if the `legalserver_data` is not
            provided.
        legalserver_site (str): needed if the `legalserver_data` is
            not provided.
        custom_fields (list[str]): Optional list of field names for custom
            fields to include.

    Returns:
        A DAList of Individual objects.
    """
    source = get_source_module_data(
        source_type="contacts",
        legalserver_data=legalserver_data,
        legalserver_matter_uuid=legalserver_matter_uuid,
        legalserver_site=legalserver_site,
    )

    if source:
        for item in source:
            if isinstance(item, dict):
                # item: Individual = item  # type annotation
                new_contact = contact_list.appendObject(Individual)
                # new_contact.id = item.get('id')
                new_contact.uuid = item.get("case_contact_uuid")
                if item.get("contact_uuid") is not None:
                    new_contact.contact_uuid = item.get("contact_uuid")
                if item.get("first") is not None:
                    new_contact.name.first = item.get("first")
                if item.get("middle") is not None:
                    new_contact.name.middle = item.get("middle")
                if item.get("last") is not None:
                    new_contact.name.last = item.get("last")
                if item["case_contact_type"].get("lookup_value_name") is not None:
                    new_contact.type = item["case_contact_type"].get(
                        "lookup_value_name"
                    )
                if item.get("suffix") is not None:
                    new_contact.name.suffix = item.get("suffix")
                if item.get("business_phone") is not None:
                    new_contact.phone = item.get("business_phone")
                if item.get("email") is not None:
                    new_contact.email = item.get("email")
                new_contact.contact_types = []
                for type in item["contact_types"]:
                    if type.get("lookup_value_name") is not None:
                        new_contact.contact_types.append(type.get("lookup_value_name"))

                new_contact.complete = True
                log(f"Contacts Populated for a case.")

    contact_list.gathered = True
    return contact_list


def populate_client(
    *, client: Individual | Person, legalserver_data: dict
) -> Individual | Person:
    """Take the data from LegalServer and populate an Individual or Person.

    This is a keyword defined function that takes a the general legalserver_data
    from the `get_matter_details` and saves the client related data to either an
    Individual or a Person depending on whether the client is an individual or a
    group.

    Args:
        client (Individual | Person): Either an Individual or a Person object
        legalserver_data (dict): the full case data returned from the Get Matter
        API call to LegalServer

    Returns:
        A populated client object.
    """

    if legalserver_data.get("is_group"):
        client.name.text = legalserver_data.get("organization_name")
    else:
        client.initializeAttribute("name", IndividualName)
    if legalserver_data.get("first") is not None:
        client.name.first = legalserver_data.get("first")
    if legalserver_data.get("last") is not None:
        client.name.last = legalserver_data.get("last")
    if legalserver_data.get("middle") is not None:
        client.name.middle = legalserver_data.get("middle")
    if legalserver_data.get("suffix") is not None:
        client.name.suffix = legalserver_data.get("suffix")

    # Client Details

    if legalserver_data.get("ssn") is not None:
        client.ssn = legalserver_data.get("ssn")
    if legalserver_data.get("veteran") is not None:
        client.is_veteran = legalserver_data.get("veteran")
    if legalserver_data.get("client_gender") is not None:
        if legalserver_data["client_gender"].get("lookup_value_name") is not None:
            client.gender = legalserver_data["client_gender"].get("lookup_value_name")
        elif isinstance(legalserver_data.get("client_gender"), str):
            client.gender = legalserver_data.get("client_gender")
    if legalserver_data.get("client_email_address") is not None:
        client.email = legalserver_data.get("client_email_address")
    if legalserver_data.get("date_of_birth") is not None:
        client.birthdate = legalserver_data.get("date_of_birth")
    if legalserver_data.get("salutation") is not None:
        client.salutation_to_use = legalserver_data.get("salutation")
    if legalserver_data.get("disabled") is not None:
        client.is_disabled = legalserver_data.get("disabled")
    if legalserver_data.get("employment_status") is not None:
        if legalserver_data["employment_status"].get("lookup_value_name") is not None:
            client.employment_status = legalserver_data["employment_status"].get(
                "lookup_value_name"
            )
        elif isinstance(legalserver_data.get("employment_status"), str):
            client.employment_status = legalserver_data.get("employment_status")

    if legalserver_data.get("preferred_phone_number") is not None:
        if (
            legalserver_data["preferred_phone_number"].get("lookup_value_name")
            is not None
        ):
            client.preferred_phone_number = legalserver_data[
                "preferred_phone_number"
            ].get("lookup_value_name")
    if legalserver_data.get("home_phone") is not None:
        client.phone_number = legalserver_data.get("home_phone")
    if legalserver_data.get("mobile_phone") is not None:
        client.mobile_number = legalserver_data.get("mobile_phone")
    if legalserver_data.get("other_phone") is not None:
        client.other_phone = legalserver_data.get("other_phone")
    if legalserver_data.get("work_phone") is not None:
        client.mobile_number = legalserver_data.get("work_phone")
    if legalserver_data.get("fax_phone") is not None:
        client.other_phone = legalserver_data.get("fax_phone")
    if legalserver_data.get("home_phone_note") is not None:
        client.phone_number_note = legalserver_data.get("home_phone_note")
    if legalserver_data.get("mobile_phone_note") is not None:
        client.mobile_number_note = legalserver_data.get("mobile_phone_note")
    if legalserver_data.get("other_phone_note") is not None:
        client.other_phone_note = legalserver_data.get("other_phone_note")
    if legalserver_data.get("work_phone_note") is not None:
        client.mobile_number_note = legalserver_data.get("work_phone_note")
    if legalserver_data.get("fax_phone_note") is not None:
        client.other_phone_note = legalserver_data.get("fax_phone_note")

    if legalserver_data.get("language") is not None:
        if legalserver_data["language"].get("lookup_value_name") is not None:
            client.language_name = legalserver_data["language"].get("lookup_value_name")
            if (
                language_code_from_name(
                    legalserver_data["language"].get("lookup_value_name")
                )
                != "Unknown"
            ):
                client.language = language_code_from_name(
                    legalserver_data["language"].get("lookup_value_name")
                )
    if legalserver_data.get("second_language") is not None:
        if legalserver_data["second_language"].get("lookup_value_name") is not None:
            client.second_language_name = legalserver_data["second_language"].get(
                "lookup_value_name"
            )
            if (
                language_code_from_name(
                    legalserver_data["second_language"].get("lookup_value_name")
                )
                != "Unknown"
            ):
                client.second_language = language_code_from_name(
                    legalserver_data["second_language"].get("lookup_value_name")
                )

    if legalserver_data.get("interpreter") is not None:
        client.interpreter = legalserver_data.get("interpreter")
    if legalserver_data.get("marital_status") is not None:
        if legalserver_data["marital_status"].get("lookup_value_name") is not None:
            client.marital_status = legalserver_data["marital_status"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("citizenship") is not None:
        if legalserver_data["citizenship"].get("lookup_value_name") is not None:
            client.citizenship = legalserver_data["citizenship"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("citizenship_country") is not None:
        if legalserver_data["citizenship_country"].get("lookup_value_name") is not None:
            client.citizenship_country = legalserver_data["citizenship_country"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("immigration_status") is not None:
        if legalserver_data["immigration_status"].get("lookup_value_name") is not None:
            client.immigration_status = legalserver_data["immigration_status"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("a_number") is not None:
        client.a_number = legalserver_data.get("a_number")
    if legalserver_data.get("visa_number") is not None:
        client.visa_number = legalserver_data.get("visa_number")

    if legalserver_data.get("race") is not None:
        if legalserver_data["race"].get("lookup_value_name") is not None:
            client.race = legalserver_data["race"].get("lookup_value_name")
    if legalserver_data.get("ethnicity") is not None:
        if legalserver_data["ethnicity"].get("lookup_value_name") is not None:
            client.ethnicity = legalserver_data["ethnicity"].get("lookup_value_name")
    if legalserver_data.get("current_living_situation") is not None:
        if (
            legalserver_data["current_living_situation"].get("lookup_value_name")
            is not None
        ):
            client.current_living_situation = legalserver_data[
                "current_living_situation"
            ].get("lookup_value_name")
    if legalserver_data.get("victim_of_domestic_violence") is not None:
        client.victim_of_domestic_violence = legalserver_data.get(
            "victim_of_domestic_violence"
        )
    if legalserver_data.get("birth_city") is not None:
        client.birth_city = legalserver_data.get("birth_city")
    if legalserver_data.get("birth_country") is not None:
        if legalserver_data["birth_country"].get("lookup_value_name") is not None:
            client.birth_country = legalserver_data["birth_country"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("drivers_license") is not None:
        client.drivers_license = legalserver_data.get("drivers_license")
    if legalserver_data.get("highest_education") is not None:
        if legalserver_data["highest_education"].get("lookup_value_name") is not None:
            client.highest_education = legalserver_data["highest_education"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("institutionalized") is not None:
        client.institutionalized = legalserver_data.get("institutionalized")
    if legalserver_data.get("institutionalized_at") is not None:
        if (
            legalserver_data["institutionalized_at"].get("organization_uuid")
            is not None
        ):
            client.institutionalized_organization_uuid = legalserver_data[
                "institutionalized_at"
            ].get("organization_uuid")
        if (
            legalserver_data["institutionalized_at"].get("organization_name")
            is not None
        ):
            client.institutionalized_organization_name = legalserver_data[
                "institutionalized_at"
            ].get("organization_name")
    if legalserver_data.get("school_status") is not None:
        if legalserver_data["school_status"].get("lookup_value_name") is not None:
            client.school_status = legalserver_data["school_status"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("military_status") is not None:
        if legalserver_data["military_service"].get("lookup_value_name") is not None:
            client.military_service = legalserver_data["military_service"].get(
                "lookup_value_name"
            )

    # Client Home Address
    if legalserver_data.get("client_address_home") is not None:
        if legalserver_data["client_address_home"].get("street") is not None:
            client.address.address = legalserver_data["client_address_home"].get(
                "street"
            )
        ## LS Supports both Apt Num and Street2
        if (
            legalserver_data["client_address_home"].get("street_2") is not None
            and legalserver_data["client_address_home"].get("apt_num") is None
        ):
            client.address.unit = legalserver_data["client_address_home"].get(
                "street_2"
            )
        if (
            legalserver_data["client_address_home"].get("apt_num") is not None
            and legalserver_data["client_address_home"].get("street_2") is None
        ):
            client.address.unit = legalserver_data["client_address_home"].get("apt_num")
        if (
            legalserver_data["client_address_home"].get("apt_num") is not None
            and legalserver_data["client_address_home"].get("street_2") is not None
        ):
            client.address.unit = legalserver_data["client_address_home"].get("apt_num")
            if client.address.address is None:
                client.address.address = legalserver_data["client_address_home"].get(
                    "street_2"
                )
            else:
                client.address.address = f'{client.address.address}, {legalserver_data["client_address_home"].get("street_2")}'
        if legalserver_data["client_address_home"].get("city") is not None:
            client.address.city = legalserver_data["client_address_home"].get("city")
        if legalserver_data["client_address_home"].get("state") is not None:
            client.address.state = legalserver_data["client_address_home"].get("state")
        if legalserver_data["client_address_home"].get("zip") is not None:
            client.address.zip = legalserver_data["client_address_home"].get("zip")
        if (
            legalserver_data["client_address_home"]["county"].get("lookup_value_name")
            is not None
        ):
            client.address.county = legalserver_data["client_address_home"][
                "county"
            ].get("lookup_value_name")

        # GIS Fields
        if legalserver_data["client_address_home"].get("lon") is not None:
            client.address.ls_longitude = legalserver_data["client_address_home"].get(
                "lon"
            )
        if legalserver_data["client_address_home"].get("lat") is not None:
            client.address.ls_latitude = legalserver_data["client_address_home"].get(
                "lat"
            )
        if legalserver_data["client_address_home"].get("census_tract") is not None:
            if (
                legalserver_data["client_address_home"]["census_tract"].get(
                    "lookup_value_name"
                )
                is not None
            ):
                client.address.census_tract = legalserver_data[
                    "client_address_home"
                ].get("")
        if legalserver_data["client_address_home"].get("geocoding_failed") is not None:
            client.address.ls_geocoding_failed = legalserver_data[
                "client_address_home"
            ].get("geocoding_failed")
        if (
            legalserver_data["client_address_home"].get(
                "state_legislature_district_upper"
            )
            is not None
        ):
            if (
                legalserver_data["client_address_home"][
                    "state_legislature_district_upper"
                ].get("lookup_value_name")
                is not None
            ):
                client.address.state_legislature_district_upper = legalserver_data[
                    "client_address_home"
                ]["state_legislature_district_upper"].get("lookup_value_name")
        if (
            legalserver_data["client_address_home"].get(
                "state_legislature_district_lower"
            )
            is not None
        ):
            if (
                legalserver_data["client_address_home"][
                    "state_legislature_district_lower"
                ].get("lookup_value_name")
                is not None
            ):
                client.address.state_legislature_district_lower = legalserver_data[
                    "client_address_home"
                ]["state_legislature_district_lower"].get("lookup_value_name")
        if (
            legalserver_data["client_address_home"].get("congressional_district")
            is not None
        ):
            if (
                legalserver_data["client_address_home"]["congressional_district"].get(
                    "lookup_value_name"
                )
                is not None
            ):
                client.address.congressional_district = legalserver_data[
                    "client_address_home"
                ]["congressional_district"].get("lookup_value_name")

        standard_client_home_address_key_list = standard_client_home_address_keys()
        for key, value in legalserver_data["client_address_home"].items():
            if key not in standard_client_home_address_key_list:
                if isinstance(value, dict):
                    if value.get("lookup_value_name") is not None:
                        setattr(client.address, key, value.get("lookup_value_name"))

                #                        client.address[key] = value.get("lookup_value_name")
                else:
                    #                    client.address[key] = value
                    setattr(client.address, key, value)

    # Client Mailing Address
    if legalserver_data.get("client_address_mailing") is not None:
        if (
            legalserver_data["client_address_mailing"].get("street") is not None
            or legalserver_data["client_address_mailing"].get("apt_num") is not None
            or legalserver_data["client_address_mailing"].get("street_2") is not None
            or legalserver_data["client_address_mailing"].get("city") is not None
            or legalserver_data["client_address_mailing"].get("state") is not None
            or legalserver_data["client_address_mailing"].get("zip") is not None
        ):
            client.initializeAttribute("mailing_address", Address)

        if legalserver_data["client_address_mailing"].get("street") is not None:
            client.mailing_address.address = legalserver_data[
                "client_address_mailing"
            ].get("street")
        ## LS Supports both Apt Num and Street2
        if (
            legalserver_data["client_address_mailing"].get("street_2") is not None
            and legalserver_data["client_address_mailing"].get("apt_num") is None
        ):
            client.mailing_address.unit = legalserver_data[
                "client_address_mailing"
            ].get("street_2")
        if (
            legalserver_data["client_address_mailing"].get("apt_num") is not None
            and legalserver_data["client_address_mailing"].get("street_2") is None
        ):
            client.mailing_address.unit = legalserver_data[
                "client_address_mailing"
            ].get("apt_num")
        if (
            legalserver_data["client_address_mailing"].get("apt_num") is not None
            and legalserver_data["client_address_mailing"].get("street_2") is not None
        ):
            client.mailing_address.unit = legalserver_data[
                "client_address_mailing"
            ].get("apt_num")
            if client.mailing_address.address is None:
                client.mailing_address.address = legalserver_data[
                    "client_address_mailing"
                ].get("street_2")
            else:
                client.mailing_address.address = f'{client.mailing_address.address}, {legalserver_data["client_address_mailing"].get("street_2")}'
        if legalserver_data["client_address_mailing"].get("city") is not None:
            client.mailing_address.city = legalserver_data[
                "client_address_mailing"
            ].get("city")
        if legalserver_data["client_address_mailing"].get("state") is not None:
            client.mailing_address.state = legalserver_data[
                "client_address_mailing"
            ].get("state")
        if legalserver_data["client_address_mailing"].get("zip") is not None:
            client.mailing_address.zip = legalserver_data["client_address_mailing"].get(
                "zip"
            )

    return client


def populate_case(*, case: DAObject, legalserver_data: dict) -> DAObject:
    """Take the data from LegalServer and populate a DAObject for the matter.

    This is a keyword defined function that takes a DAObject and populates it
    with the case related details related to a case. It requires the general
    legalserver_data from the `get_matter_details` response.

    Args:
        case (DAObject): DAObject holding all the case data
        legalserver_data (dict): the full case data returned from the Get Matter
            API call to LegalServer

    Returns:
        The populated case object.
    """

    case.case_number = legalserver_data.get("case_number")
    case.case_id = legalserver_data.get("case_id")
    case.profile_url = legalserver_data.get("case_profile_url")
    case.case_disposition = legalserver_data["case_disposition"].get(
        "lookup_value_name"
    )
    case.is_this_a_prescreen = legalserver_data.get("is_this_a_prescreen")
    case.is_group = legalserver_data.get("is_group")
    case.email = legalserver_data.get("case_email_address")
    case.rejected = legalserver_data.get("rejected")
    if legalserver_data.get("dynamic_process") is not None:
        if legalserver_data["dynamic_process"].get("dynamic_process_id") is not None:
            case.dynamic_process_id = legalserver_data["dynamic_process"].get(
                "dynamic_process_id"
            )
        if legalserver_data["dynamic_process"].get("dynamic_process_uuid") is not None:
            case.dynamic_process_uuid = legalserver_data["dynamic_process"].get(
                "dynamic_process_uuid"
            )
        if legalserver_data["dynamic_process"].get("dynamic_process_name") is not None:
            case.dynamic_process_name = legalserver_data["dynamic_process"].get(
                "dynamic_process_name"
            )

    if legalserver_data.get("prescreen_date") is not None:
        case.prescreen_date = legalserver_data.get("prescreen_date")
    if legalserver_data.get("cause_number") is not None:
        case.cause_number = legalserver_data.get("cause_number")
    if legalserver_data.get("case_title") is not None:
        case.case_title = legalserver_data.get("case_title")
    if legalserver_data.get("prescreen_user") is not None:
        if legalserver_data["prescreen_user"].get("user_uuid") is not None:
            case.prescreen_user_uuid = legalserver_data["prescreen_user"].get(
                "user_uuid"
            )
        if legalserver_data["prescreen_user"].get("user_name") is not None:
            case.prescreen_user_name = legalserver_data["prescreen_user"].get(
                "user_name"
            )
    if legalserver_data.get("prescreen_program") is not None:
        if legalserver_data["prescreen_program"].get("lookup_value_name") is not None:
            case.prescreen_program = legalserver_data["prescreen_program"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("prescreen_office") is not None:
        if legalserver_data.get("prescreen_office") is not None:
            if legalserver_data["prescreen_office"].get("office_code") is not None:
                case.prescreen_office_code = legalserver_data["prescreen_office"].get(
                    "office_code"
                )
        if legalserver_data["prescreen_office"].get("office_name") is not None:
            case.prescreen_office_name = legalserver_data["prescreen_office"].get(
                "office_name"
            )
    if legalserver_data.get("intake_user") is not None:
        if legalserver_data["intake_user"].get("user_uuid") is not None:
            case.intake_user_uuid = legalserver_data["intake_user"].get("user_uuid")
        if legalserver_data["intake_user"].get("user_name") is not None:
            case.intake_user_name = legalserver_data["intake_user"].get("user_name")
    if legalserver_data["intake_program"].get("lookup_value_name") is not None:
        case.intake_program = legalserver_data["intake_program"].get(
            "lookup_value_name"
        )
    if legalserver_data.get("intake_office") is not None:
        if legalserver_data["intake_office"].get("office_code") is not None:
            case.intake_office_code = legalserver_data["intake_office"].get(
                "office_code"
            )
        if legalserver_data["intake_office"].get("office_name") is not None:
            case.intake_office_name = legalserver_data["intake_office"].get(
                "office_name"
            )
    if (
        legalserver_data["prescreen_screening_status"].get("lookup_value_name")
        is not None
    ):
        case.prescreen_screening_status = legalserver_data[
            "prescreen_screening_status"
        ].get("lookup_value_name")
    if legalserver_data.get("date_opened") is not None:
        case.date_opened = legalserver_data.get("date_opened")
    if legalserver_data.get("date_closed") is not None:
        case.date_closed = legalserver_data.get("date_closed")
    if legalserver_data.get("intake_date") is not None:
        case.intake_date = legalserver_data.get("intake_date")
    if legalserver_data.get("date_rejected") is not None:
        case.date_rejected = legalserver_data.get("date_rejected")
    if legalserver_data.get("county_of_dispute") is not None:
        if legalserver_data["county_of_dispute"].get("lookup_value_name") is not None:
            case.county_of_dispute_name = legalserver_data["county_of_dispute"].get(
                "lookup_value_name"
            )
        if legalserver_data["county_of_dispute"].get("lookup_value_state") is not None:
            case.county_of_dispute_state = legalserver_data["county_of_dispute"].get(
                "lookup_value_state"
            )
        if legalserver_data["county_of_dispute"].get("lookup_value_FIPS") is not None:
            case.county_of_dispute_FIPS = legalserver_data["county_of_dispute"].get(
                "lookup_value_FIPS"
            )
    if legalserver_data["legal_problem_code"].get("lookup_value_name") is not None:
        case.legal_problem_code = legalserver_data["legal_problem_code"].get(
            "lookup_value_name"
        )
    if legalserver_data["legal_problem_category"].get("lookup_value_name") is not None:
        case.legal_problem_category = legalserver_data["legal_problem_category"].get(
            "lookup_value_name"
        )
    temp_list = []
    for slpc in legalserver_data["special_legal_problem_code"]:
        if slpc.get("lookup_value_name") is not None:
            temp_list.append(slpc.get("lookup_value_name"))
    if temp_list:
        case.special_legal_problem_code = temp_list
    del temp_list
    if legalserver_data["intake_type"].get("lookup_value_name") is not None:
        case.intake_type = legalserver_data["intake_type"].get("lookup_value_name")
    if legalserver_data.get("impact") is not None:
        case.impact = legalserver_data.get("impact")
    temp_list = []
    for sc in legalserver_data["special_characteristics"]:
        if sc.get("lookup_value_name") is not None:
            temp_list.append(sc.get("lookup_value_name"))
    if temp_list:
        case.special_characteristics = temp_list
    del temp_list
    if legalserver_data["case_status"].get("lookup_value_name") is not None:
        case.case_status = legalserver_data["case_status"].get("lookup_value_name")
    if legalserver_data["close_reason"].get("lookup_value_name") is not None:
        case.close_reason = legalserver_data["close_reason"].get("lookup_value_name")
    if legalserver_data.get("pro_bono_opportunity_summary") is not None:
        case.pro_bono_opportunity_summary = legalserver_data.get(
            "pro_bono_opportunity_summary"
        )
    if legalserver_data.get("pro_bono_opportunity_county") is not None:
        if (
            legalserver_data["pro_bono_opportunity_county"].get("lookup_value_name")
            is not None
        ):
            case.pro_bono_opportunity_county_name = legalserver_data[
                "pro_bono_opportunity_county"
            ].get("lookup_value_name")
        if (
            legalserver_data["pro_bono_opportunity_county"].get("lookup_Value_state")
            is not None
        ):
            case.pro_bono_opportunity_county_state = legalserver_data[
                "pro_bono_opportunity_county"
            ].get("lookup_value_state")
        if (
            legalserver_data["pro_bono_opportunity_county"].get("lookup_value_FIPS")
            is not None
        ):
            case.pro_bono_opportunity_county_FIPS = legalserver_data[
                "pro_bono_opportunity_county"
            ].get("lookup_value_FIPS")
    if legalserver_data.get("pro_bono_opportunity_note") is not None:
        case.pro_bono_opportunity_note = legalserver_data.get(
            "pro_bono_opportunity_note"
        )
    if legalserver_data.get("pro_bono_opportunity_available_date") is not None:
        case.pro_bono_opportunity_available_date = legalserver_data.get(
            "pro_bono_opportunity_available_date"
        )
    if legalserver_data.get("pro_bono_opportunity_placement_date") is not None:
        case.pro_bono_opportunity_placement_date = legalserver_data.get(
            "pro_bono_opportunity_placement_date"
        )
    if (
        legalserver_data["pro_bono_engagement_type"].get("lookup_value_name")
        is not None
    ):
        case.pro_bono_engagement_type = legalserver_data[
            "pro_bono_engagement_type"
        ].get("lookup_value_name")
    if (
        legalserver_data["pro_bono_time_commitment"].get("lookup_value_name")
        is not None
    ):
        case.pro_bono_time_commitment = legalserver_data[
            "pro_bono_time_commitment"
        ].get("lookup_value_name")
    if legalserver_data.get("pro_bono_urgent") is not None:
        case.pro_bono_urgent = legalserver_data.get("pro_bono_urgent")
    if legalserver_data.get("pro_bono_interest_cc") is not None:
        case.pro_bono_interest_cc = legalserver_data.get("pro_bono_interest_cc")
    temp_list = []
    for skill in legalserver_data["pro_bono_skills_developed"]:
        if skill.get("lookup_value_name") is not None:
            temp_list.append(skill.get("lookup_value_name"))
    if temp_list:
        case.pro_bono_skills_developed = temp_list
    del temp_list
    temp_list = []
    for vol in legalserver_data["pro_bono_appropriate_volunteer"]:
        if vol.get("lookup_value_name") is not None:
            temp_list.append(vol.get("lookup_value_name"))
    if temp_list != []:
        case.pro_bono_appropriate_volunteer = temp_list
    del temp_list
    if legalserver_data.get("pro_bono_expiration_date") is not None:
        case.pro_bono_expiration_date = legalserver_data.get("pro_bono_expiration_date")
    if (
        legalserver_data["pro_bono_opportunity_status"].get("lookup_value_name")
        is not None
    ):
        case.pro_bono_opportunity_status = legalserver_data[
            "pro_bono_opportunity_status"
        ].get("lookup_value_name")
    if legalserver_data.get("pro_bono_opportunity_cc") is not None:
        case.pro_bono_opportunity_cc = legalserver_data.get("pro_bono_opportunity_cc")
    temp_list = []
    for topic in legalserver_data["simplejustice_opportunity_legal_topic"]:
        if topic.get("lookup_value_name") is not None:
            temp_list.append(topic.get("lookup_value_name"))
    if temp_list != []:
        case.simplejustice_opportunity_legal_topic = temp_list
    del temp_list
    temp_list = []
    for community in legalserver_data["simplejustice_opportunity_helped_community"]:
        if community.get("lookup_value_name") is not None:
            temp_list.append(community.get("lookup_value_name"))
    if temp_list != []:
        case.simplejustice_opportunity_helped_community = temp_list
    del temp_list
    temp_list = []
    for skill in legalserver_data["simplejustice_opportunity_skill_type"]:
        if skill.get("lookup_value_name") is not None:
            temp_list.append(skill.get("lookup_value_name"))
    if temp_list != []:
        case.simplejustice_opportunity_skill_type = temp_list
    del temp_list
    temp_list = []
    for community in legalserver_data["simplejustice_opportunity_community"]:
        if community.get("lookup_value_name") is not None:
            temp_list.append(community.get("lookup_value_name"))
    if temp_list != []:
        case.simplejustice_opportunity_community = temp_list
    del temp_list
    if legalserver_data["level_of_expertise"].get("lookup_value_name") is not None:
        case.level_of_expertise = legalserver_data["level_of_expertise"].get(
            "lookup_value_name"
        )
    if legalserver_data.get("days_open") is not None:
        case.days_open = legalserver_data.get("days_open")

    if legalserver_data.get("percentage_of_poverty") is not None:
        case.percentage_of_poverty = legalserver_data.get("percentage_of_poverty")
    if legalserver_data.get("asset_eligible") is not None:
        case.asset_eligible = legalserver_data.get("asset_eligible")
    if legalserver_data.get("lsc_eligible") is not None:
        case.lsc_eligible = legalserver_data.get("lsc_eligible")
    if legalserver_data.get("income_eligible") is not None:
        case.income_eligible = legalserver_data.get("income_eligible")
    if legalserver_data["how_referred"].get("lookup_value_name") is not None:
        case.how_referred = legalserver_data["how_referred"].get("lookup_value_name")
    if legalserver_data.get("number_of_adults") is not None:
        case.number_of_adults = legalserver_data.get("number_of_adults")
    temp_list = []
    for rest in legalserver_data["case_restrictions"]:
        if rest.get("lookup_value_name") is not None:
            temp_list.append(rest.get("lookup_value_name"))
    if temp_list:
        case.case_restrictions = temp_list
    del temp_list
    ## these are users, perhaps do something else
    if legalserver_data.get("case_exclusions") is not None:
        case.case_exclusions = legalserver_data.get("case_exclusions")
    if legalserver_data.get("exclude_from_search_results") is not None:
        case.exclude_from_search_results = legalserver_data.get(
            "exclude_from_search_results"
        )
    if legalserver_data.get("conflict_status_note") is not None:
        case.conflict_status_note = legalserver_data.get("conflict_status_note")
    if legalserver_data.get("conflict_status_note_ap") is not None:
        case.conflict_status_note_ap = legalserver_data.get("conflict_status_note_ap")
    if legalserver_data.get("client_conflict_status") is not None:
        case.client_conflict_status = legalserver_data.get("client_conflict_status")
    if legalserver_data.get("adverse_party_conflict_status") is not None:
        case.adverse_party_conflict_status = legalserver_data.get(
            "adverse_party_conflict_status"
        )
    if legalserver_data.get("conflict_waived") is not None:
        case.conflict_waived = legalserver_data.get("conflict_waived")
    if legalserver_data.get("ap_conflict_waived") is not None:
        case.ap_conflict_waived = legalserver_data.get("ap_conflict_waived")
    if legalserver_data["ssi_welfare_status"].get("lookup_value_name") is not None:
        case.ssi_welfare_status = legalserver_data["ssi_welfare_status"].get(
            "lookup_value_name"
        )
    if (
        legalserver_data.get("ssi_months_client_has_received_welfare_payments")
        is not None
    ):
        case.ssi_months_client_has_received_welfare_payments = legalserver_data.get(
            "ssi_months_client_has_received_welfare_payments"
        )
    if legalserver_data.get("ssi_welfare_case_num") is not None:
        case.ssi_welfare_case_num = legalserver_data.get("ssi_welfare_case_num")
    if (
        legalserver_data["ssi_section8_housing_type"].get("lookup_value_name")
        is not None
    ):
        case.ssi_section8_housing_type = legalserver_data[
            "ssi_section8_housing_type"
        ].get("lookup_value_name")
    if legalserver_data.get("ssi_eatra") is not None:
        case.ssi_eatra = legalserver_data.get("ssi_eatra")
    ## these are organizations, perhaps do something else.
    if legalserver_data.get("referring_organizations") is not None:
        case.referring_organizations = legalserver_data.get("referring_organizations")
    temp_list = []
    for add in legalserver_data["additional_assistance"]:
        if add.get("lookup_value_name") is not None:
            temp_list.append(add.get("lookup_value_name"))
    if temp_list:
        case.additional_assistance = temp_list
    del temp_list
    if legalserver_data.get("pai_case") is not None:
        case.pai_case = legalserver_data.get("pai_case")
    if legalserver_data.get("client_approved_transfer") is not None:
        case.client_approved_transfer = legalserver_data.get("client_approved_transfer")
    if legalserver_data.get("transfer_reject_reason") is not None:
        case.transfer_reject_reason = legalserver_data.get("transfer_reject_reason")
    if legalserver_data.get("transfer_reject_notes") is not None:
        case.transfer_reject_notes = legalserver_data.get("transfer_reject_notes")
    if legalserver_data.get("prior_client") is not None:
        case.prior_client = legalserver_data.get("prior_client")
    temp_list = []
    for pro in legalserver_data["priorities"]:
        if pro.get("lookup_value_name") is not None:
            temp_list.append(pro.get("lookup_value_name"))
    if temp_list:
        case.priorities = temp_list
    del temp_list

    if legalserver_data.get("asset_assistance") is not None:
        case.asset_assistance = legalserver_data.get("asset_assistance")
    if legalserver_data.get("fee_generating") is not None:
        case.fee_generating = legalserver_data.get("fee_generating")
    if legalserver_data.get("rural") is not None:
        case.rural = legalserver_data.get("rural")
    if (
        legalserver_data.get(
            "pro_bono_opportunity_guardian_ad_litem_certification_needed"
        )
        is not None
    ):
        case.pro_bono_opportunity_guardian_ad_litem_certification_needed = (
            legalserver_data.get(
                "pro_bono_opportunity_guardian_ad_litem_certification_needed"
            )
        )
    if (
        legalserver_data.get("pro_bono_opportunity_summary_of_upcoming_dates")
        is not None
    ):
        case.pro_bono_opportunity_summary_of_upcoming_dates = legalserver_data.get(
            "pro_bono_opportunity_summary_of_upcoming_dates"
        )
    if legalserver_data.get("pro_bono_opportunity_summary_of_work_needed") is not None:
        case.pro_bono_opportunity_summary_of_work_needed = legalserver_data.get(
            "pro_bono_opportunity_summary_of_work_needed"
        )
    if legalserver_data.get("pro_bono_opportunity_special_issues") is not None:
        case.pro_bono_opportunity_special_issues = legalserver_data.get(
            "pro_bono_opportunity_special_issues"
        )
    if (
        legalserver_data.get("pro_bono_opportunity_court_and_filing_fee_information")
        is not None
    ):
        case.pro_bono_opportunity_court_and_filing_fee_information = (
            legalserver_data.get(
                "pro_bono_opportunity_court_and_filing_fee_information"
            )
        )
    if legalserver_data.get("pro_bono_opportunity_paupers_eligible") is not None:
        case.pro_bono_opportunity_paupers_eligible = legalserver_data.get(
            "pro_bono_opportunity_paupers_eligible"
        )

    if legalserver_data.get("is_lead_case") is not None:
        case.is_lead_case = legalserver_data.get("is_lead_case")
    if legalserver_data.get("lead_case") is not None:
        case.lead_case = legalserver_data.get("lead_case")
    if legalserver_data.get("income_change_significantly") is not None:
        case.income_change_significantly = legalserver_data.get(
            "income_change_significantly"
        )
    if legalserver_data["income_change_type"].get("lookup_value_name") is not None:
        case.income_change_type = legalserver_data["income_change_type"].get(
            "lookup_value_name"
        )

    if legalserver_data["hud_entity_poverty_band"].get("lookup_value_name") is not None:
        case.hud_entity_poverty_band = legalserver_data["hud_entity_poverty_band"].get(
            "lookup_value_name"
        )
    if (
        legalserver_data["hud_statewide_poverty_band"].get("lookup_value_name")
        is not None
    ):
        case.hud_statewide_poverty_band = legalserver_data[
            "hud_statewide_poverty_band"
        ].get("lookup_value_name")
    if legalserver_data.get("hud_statewide_median_income_percentage") is not None:
        case.hud_statewide_median_income_percentage = legalserver_data.get(
            "hud_statewide_median_income_percentage"
        )
    if legalserver_data.get("hud_area_median_income_percentage") is not None:
        case.hud_area_median_income_percentage = legalserver_data.get(
            "hud_area_median_income_percentage"
        )
    if legalserver_data["hud_ami_category"].get("lookup_value_name") is not None:
        case.hud_ami_category = legalserver_data["hud_ami_category"].get(
            "lookup_value_name"
        )

    if legalserver_data.get("sharepoint_site_library") is not None:
        if (
            legalserver_data["sharepoint_site_library"].get("lookup_value_name")
            is not None
        ):
            case.sharepoint_site_library = legalserver_data[
                "sharepoint_site_library"
            ].get("lookup_value_name")
    if legalserver_data.get("sending_site_identification_number") is not None:
        case.sending_site_identification_number = legalserver_data.get(
            "sending_site_identification_number"
        )
    if legalserver_data.get("branch") is not None:
        if legalserver_data["branch"].get("lookup_value_name") is not None:
            case.branch = legalserver_data["branch"].get("lookup_value_name")
    if legalserver_data.get("military_status") is not None:
        if legalserver_data["military_status"].get("lookup_value_name") is not None:
            case.military_status = legalserver_data["military_status"].get(
                "lookup_value_name"
            )

    # Custom Fields are funny
    standard_key_list = standard_matter_keys()
    custom_fields = {
        key: value
        for key, value in legalserver_data.items()
        if key not in standard_key_list
    }
    if custom_fields is not None:
        case.custom_fields = custom_fields

    log(f"LegalServer Case Object populated for a case.")

    return case


def get_source_module_data(
    *,
    source_type: str,
    legalserver_data: Dict | None = None,
    legalserver_matter_uuid: str | None = None,
    legalserver_site: str | None = None,
    custom_field_list: List | None = None,
) -> List:
    """Helper function to check and then collect source data for populating
    DALists.

    This will check if the source data is present in the general legalserver_data
    response. If it is not present there, then it will make the appropriate API
    call to retrieve the information for that module. It can take any custom field
    parameters as part of the request.

    Args:
        source_type (str): This is the string name of the module. It should match
            the key in the Get Matter Details response for the module.
        legalserver_data (dict): This is an optional set of data from the initial
            Get LegalServer Matter Details API call.
        legalserver_matter_uuid (str): This is the specific LegalServer case.
        legalserver_site (str): This is the LegalServer site to check.
        custom_field_list (list): This is an optional list of custom fields.

    Returns:
        A list of dictionaries for the API response.
    """

    source = []
    if legalserver_data:
        if legalserver_data.get(source_type) is not None:
            source = legalserver_data[source_type]
    if not source:
        if legalserver_matter_uuid and legalserver_site:
            log(
                f"{source_type} should be retrieved via API since they were not provided otherwise."
            )
            if source_type == "events":
                source = search_event_data(
                    legalserver_site=legalserver_site,
                    legalserver_matter_uuid=legalserver_matter_uuid,
                    custom_fields=custom_field_list,
                )
            elif source_type == "tasks":
                source = search_task_data(
                    legalserver_site=legalserver_site,
                    legalserver_matter_uuid=legalserver_matter_uuid,
                    custom_fields=custom_field_list,
                )
            elif source_type == "contacts":
                source = search_matter_contacts_data(
                    legalserver_site=legalserver_site,
                    legalserver_matter_uuid=legalserver_matter_uuid,
                )
            elif source_type == "services":
                source = search_matter_services_data(
                    legalserver_site=legalserver_site,
                    legalserver_matter_uuid=legalserver_matter_uuid,
                    custom_fields=custom_field_list,
                )
            elif source_type == "charges":
                source = search_matter_charges_data(
                    legalserver_site=legalserver_site,
                    legalserver_matter_uuid=legalserver_matter_uuid,
                    custom_fields=custom_field_list,
                )
            elif source_type == "litigations":
                source = search_matter_litigation_data(
                    legalserver_site=legalserver_site,
                    legalserver_matter_uuid=legalserver_matter_uuid,
                    custom_fields=custom_field_list,
                )
            elif source_type == "assignments":
                source = search_matter_assignments_data(
                    legalserver_site=legalserver_site,
                    legalserver_matter_uuid=legalserver_matter_uuid,
                )
            elif source_type == "notes":
                source = search_matter_notes_data(
                    legalserver_site=legalserver_site,
                    legalserver_matter_uuid=legalserver_matter_uuid,
                )
            elif source_type == "additional_names":
                source = search_matter_additional_names(
                    legalserver_site=legalserver_site,
                    legalserver_matter_uuid=legalserver_matter_uuid,
                )
            elif source_type == "adverse_parties":
                source = search_matter_adverse_parties(
                    legalserver_site=legalserver_site,
                    legalserver_matter_uuid=legalserver_matter_uuid,
                )
            elif source_type == "non_adverse_parties":
                source = search_matter_non_adverse_parties(
                    legalserver_site=legalserver_site,
                    legalserver_matter_uuid=legalserver_matter_uuid,
                )
            elif source_type == "incomes":
                source = []
                # no search incomes endpoint in LegalServer
                # source = search_matter_notes_data(
                # legalserver_site=legalserver_site,
                # legalserver_matter_uuid=legalserver_matter_uuid
                # )
            else:
                source = []
        else:
            log(
                f"{source_type} cannot be populated because no case data or "
                f"LegalServer case and site were supplied."
            )

    if len(source) == 1:
        if "error" in source[0]:
            error_string = str(source[0].get("error"))  # type: ignore
            log(f"Error is the collection of the {source_type} data: {error_string}")
            source = []

    return source


def populate_primary_assignment(
    *,
    primary_assignment: Individual,
    assignment_list: DAList,
    legalserver_data: dict | None = None,
    legalserver_matter_uuid: str = "",
    legalserver_site: str = "",
    user_custom_fields: List | None = None,
) -> Individual:
    """
    This is a keyword defined function that takes an Individual object and populates
    it with the user data of the current primary assignment on a case. This needs
    `populate_assignment()` run first so that it can parse the list of assignments
    on the case for the current primary assignment.

    Args:
        primary_assignment (Individual): Individual object that will be returned
        assignment_list (DAList[DAObject]): DAList of DAObjects
        legalserver_data (Dict | None): Optional dictionary of the matter data
            from a LegalServerrequest
        legalserver_matter_uuid (str): needed if the `legalserver_data` is not provided
        legalserver_site (str): needed if the `legalserver_data` is not provided
        user_custom_fields (list): Optional list of custom fields to gather on the User record.

    Returns:
        The supplied Individual object.
    """
    if len(assignment_list) == 0:
        assignment_list = populate_assignments(
            assignment_list=assignment_list,
            legalserver_data=legalserver_data,
            legalserver_matter_uuid=legalserver_matter_uuid,
            legalserver_site=legalserver_site,
        )
    for assignment in assignment_list:
        if isinstance(assignment, DAObject):
            if assignment.end_date is None and assignment.type == "Primary":
                primary_assignment.user_uuid = assignment.user_uuid
                user_data = get_user_details(
                    legalserver_site=legalserver_site,
                    legalserver_user_uuid=primary_assignment.user_uuid,
                    custom_fields=user_custom_fields,
                )
                primary_assignment = populate_user_data(
                    user=primary_assignment, user_data=user_data
                )
    return primary_assignment


def populate_first_pro_bono_assignment(
    *,
    legalserver_first_pro_bono_assignment: Individual,
    assignment_list: DAList,
    legalserver_data: dict | None = None,
    legalserver_matter_uuid: str = "",
    legalserver_site: str = "",
    user_custom_fields: List | None = None,
) -> Individual:
    """
    This is a keyword defined function that takes an Individual object and populates
    it with the user data of the earliest assigned Pro Bono assignment on a case
    whose assignment has not yet been ended. This needs
    `populate_assignment()` run first so that it can parse the list of assignments
    on the case for the current primary assignment.

    Args:
        legalserver_first_pro_bono_assignment (Individual): Individual object that will be returned
        assignment_list (DAList[DAObject]): DAList of DAObjects
        legalserver_data (Dict | None): Optional dictionary of the matter data
            from a LegalServerrequest
        legalserver_matter_uuid (str): needed if the `legalserver_data` is not provided
        legalserver_site (str): needed if the `legalserver_data` is not provided
        user_custom_fields (list): Optional list of custom fields to gather on the User record.

    Returns:
        The supplied Individual object.
    """
    if len(assignment_list) == 0:
        assignment_list = populate_assignments(
            assignment_list=assignment_list,
            legalserver_data=legalserver_data,
            legalserver_matter_uuid=legalserver_matter_uuid,
            legalserver_site=legalserver_site,
        )
    legalserver_first_pro_bono_assignment.assignment_start_date = current_datetime()
    for assignment in assignment_list:
        if isinstance(assignment, DAObject):
            if assignment.end_date is None and assignment.type == "Pro Bono":
                if (
                    date_difference(
                        assignment.start_date,
                        legalserver_first_pro_bono_assignment.assignment_start_date,
                    ).days  # type: ignore
                    > 0
                ):
                    legalserver_first_pro_bono_assignment.user_uuid = (
                        assignment.user_uuid
                    )
                    legalserver_first_pro_bono_assignment.assignment_start_date = (
                        assignment.start_date
                    )
                    user_data = get_user_details(
                        legalserver_site=legalserver_site,
                        legalserver_user_uuid=legalserver_first_pro_bono_assignment.user_uuid,
                        custom_fields=user_custom_fields,
                    )
                    legalserver_first_pro_bono_assignment = populate_user_data(
                        user=legalserver_first_pro_bono_assignment, user_data=user_data
                    )
    return legalserver_first_pro_bono_assignment


def populate_latest_pro_bono_assignment(
    *,
    legalserver_latest_pro_bono_assignment: Individual,
    assignment_list: DAList,
    legalserver_data: dict | None = None,
    legalserver_matter_uuid: str = "",
    legalserver_site: str = "",
    user_custom_fields: List | None = None,
) -> Individual:
    """
    This is a keyword defined function that takes an Individual object and populates
    it with the user data of the latest assigned Pro Bono assignment on a case
    whose assignment has not yet been ended. This needs
    `populate_assignment()` run first so that it can parse the list of assignments
    on the case for the current primary assignment.

    Args:
        legalserver_latest_pro_bono_assignment (Individual): Individual object that will be returned
        assignment_list (DAList[DAObject]): DAList of DAObjects
        legalserver_data (Dict | None): Optional dictionary of the matter data
            from a LegalServer request
        legalserver_matter_uuid (str): needed if the `legalserver_data` is not provided
        legalserver_site (str): needed if the `legalserver_data` is not provided
        user_custom_fields (list): Optional list of custom fields to gather on the User record

    Returns:
        The supplied Individual object.
    """
    if len(assignment_list) == 0:
        assignment_list = populate_assignments(
            assignment_list=assignment_list,
            legalserver_data=legalserver_data,
            legalserver_matter_uuid=legalserver_matter_uuid,
            legalserver_site=legalserver_site,
        )
    legalserver_latest_pro_bono_assignment.assignment_start_date = (
        date.today() - date_interval(years=100)
    )
    for assignment in assignment_list:
        if isinstance(assignment, DAObject):
            if assignment.end_date is None and assignment.type == "Pro Bono":
                if (
                    date_difference(
                        assignment.start_date,
                        legalserver_latest_pro_bono_assignment.assignment_start_date,
                    ).days  # type: ignore
                    < 0
                ):
                    legalserver_latest_pro_bono_assignment.user_uuid = (
                        assignment.user_uuid
                    )
                    legalserver_latest_pro_bono_assignment.assignment_start_date = (
                        assignment.start_date
                    )
                    user_data = get_user_details(
                        legalserver_site=legalserver_site,
                        legalserver_user_uuid=legalserver_latest_pro_bono_assignment.user_uuid,
                        custom_fields=user_custom_fields,
                    )
                    legalserver_latest_pro_bono_assignment = populate_user_data(
                        user=legalserver_latest_pro_bono_assignment, user_data=user_data
                    )
    return legalserver_latest_pro_bono_assignment


def populate_current_user(
    *,
    legalserver_current_user: Individual,
    legalserver_current_user_uuid: str,
    legalserver_site: str = "",
    user_custom_fields: List | None = None,
) -> Individual:
    """
    This is a keyword defined function that takes an Individual object and populates
    it with the user data of the current LegalServer user that initiated the
    Docassemble workflow.

    Args:
        legalserver_current_user (Individual): Individual object that will be returned
        legalserver_current_user_uuid (str):
        legalserver_site (str):
        user_custom_fields (list): Optional list of custom fields to gather on the User record

    Returns:
        The supplied Individual object.
    """

    user_data = get_user_details(
        legalserver_site=legalserver_site,
        legalserver_user_uuid=legalserver_current_user_uuid,
        custom_fields=user_custom_fields,
    )
    legalserver_current_user = populate_user_data(
        user=legalserver_current_user, user_data=user_data
    )
    return legalserver_current_user


def populate_user_data(*, user: Individual, user_data: Dict) -> Individual:
    """
    This is a keyword defined function that helps populate an Individual record
    with details from the Get User API response.

    Args:
        user (Individual): The Individual object to be populated and returned.
        user_data (Dict): The get_user_details() response dictionary that has
            the information to populate the record with.

    Returns:
        The user Individual object that was initially supplied.
    """
    user.id = user_data.get("id")
    user.user_uuid = user_data.get("user_uuid")
    if user_data.get("first") is not None:
        user.name.first = user_data.get("first")
    if user_data.get("middle") is not None:
        user.name.middle = user_data.get("middle")
    if user_data.get("last") is not None:
        user.name.last = user_data.get("last")
    if user_data.get("email") is not None:
        user.email = user_data.get("email")
    if user_data.get("email_allow") is not None:
        user.email_allow = user_data.get("email_allow")
    if user_data.get("login") is not None:
        user.login = user_data.get("login")
    if user_data.get("active") is not None:
        user.active = user_data.get("active")
    if user_data.get("current") is not None:
        user.current = user_data.get("current")
    if user_data.get("contact_active") is not None:
        user.contact_active = user_data.get("contact_active")

    temp_list = []
    for type in user_data["types"]:
        if type.get("lookup_value_name") is not None:
            temp_list.append(type.get("lookup_value_name"))
    if temp_list:
        user.types = temp_list
    del temp_list

    if user_data["role"].get("lookup_value_name") is not None:
        user.role = user_data["role"].get("lookup_value_name")

    if user_data["gender"].get("lookup_value_name") is not None:
        user.role = user_data["gender"].get("lookup_value_name")

    if user_data["race"].get("lookup_value_name") is not None:
        user.role = user_data["race"].get("lookup_value_name")
    if user_data.get("dob") is not None:
        user.birthdate = user_data.get("dob")
    if user_data.get("office") is not None:
        if user_data["office"].get("office_name") is not None:
            user.office = user_data.get("office")
    if user_data["program"].get("lookup_value_name") is not None:
        user.program = user_data["program"].get("lookup_value_name")
    if user_data.get("date_start") is not None:
        user.date_start = user_data.get("date_start")
    if user_data.get("date_end") is not None:
        user.date_end = user_data.get("date_end")

    if user_data.get("date_graduated") is not None:
        user.date_graduated = user_data.get("date_graduated")
    if user_data.get("date_bar_join") is not None:
        user.date_bar_join = user_data.get("date_bar_join")
    if user_data.get("bar_number") is not None:
        user.bar_number = user_data.get("bar_number")
    if user_data.get("date_joined_panel") is not None:
        user.date_joined_panel = user_data.get("date_joined_panel")
    if user_data.get("external_unique_id") is not None:
        user.external_unique_id = user_data.get("external_unique_id")

    temp_list = []
    for program in user_data["additional_programs"]:
        if program.get("lookup_value_name") is not None:
            temp_list.append(program.get("lookup_value_name"))
    if temp_list:
        user.additional_programs = temp_list
    del temp_list

    if user_data.get("additional_offices") is not None:
        user.additional_offices = user_data.get("additional_offices")

    temp_list = []
    for office in user_data["additional_offices"]:
        if office.get("office_name") is not None:
            temp_list.append(office.get("office_name"))
    if temp_list:
        user.additional_offices = temp_list
    del temp_list

    if user_data.get("external_guid") is not None:
        user.external_guid = user_data.get("external_guid")

    if user_data.get("highest_court_admitted") is not None:
        user.highest_court_admitted = user_data.get("highest_court_admitted")

    temp_list = []
    for language in user_data["languages"]:
        if language.get("lookup_value_name") is not None:
            temp_list.append(language.get("lookup_value_name"))
    if temp_list:
        user.languages = temp_list
    del temp_list

    if user_data.get("phone_business") is not None:
        user.phone_business = user_data.get("phone_business")
    if user_data.get("phone_fax") is not None:
        user.phone_fax = user_data.get("phone_fax")
    if user_data.get("phone_home") is not None:
        user.phone_home = user_data.get("phone_home")
    if user_data.get("phone_mobile") is not None:
        user.phone_mobile = user_data.get("phone_mobile")
    if user_data.get("phone_other") is not None:
        user.phone_other = user_data.get("phone_other")
    if user_data.get("practice_state") is not None:
        user.practice_state = user_data.get("practice_state")
    if user_data["member_good_standing"].get("lookup_value_name") is not None:
        user.member_good_standing = user_data["member_good_standing"].get(
            "lookup_value_name"
        )
    if user_data["recruitment"].get("lookup_value_name") is not None:
        user.recruitment = user_data["recruitment"].get("lookup_value_name")
    if user_data.get("salutation") is not None:
        user.salutation_to_use = user_data.get("salutation")
    if user_data.get("school_attended") is not None:
        user.school_attended = user_data.get("school_attended")
    if user_data.get("bind_work_address_to_organization") is not None:
        user.bind_work_address_to_organization = user_data.get(
            "bind_work_address_to_organization"
        )
    if user_data.get("hourly_rate") is not None:
        user.hourly_rate = user_data.get("hourly_rate")

    temp_list = []
    temp_list2 = []
    for county in user_data["counties"]:
        if county.get("lookup_value_name") is not None:
            temp_list.append(county.get("lookup_value_name"))
            temp_list2.append(county.get("lookup_value_FIPS"))
    if temp_list:
        user.counties = temp_list
        user.counties_FIPS = temp_list2
    del temp_list
    del temp_list2

    if user_data.get("contact_types") is not None:
        user.contact_types = user_data.get("contact_types")

    if user_data.get("address_home") is not None:
        user.address_home = user_data.get("address_home")

    if user_data.get("address_work") is not None:
        user.address_work = user_data.get("address_work")

    temp_list = []
    for type in user_data["types"]:
        if type.get("lookup_value_name") is not None:
            temp_list.append(type.get("lookup_value_name"))
    if temp_list:
        user.types = temp_list
    del temp_list

    # Work Address
    if user_data.get("address_work") is not None:
        if user_data["address_work"].get("street") is not None:
            user.address.address = user_data["address_work"].get("street")
        ## LS Supports both Apt Num and Street2
        if (
            user_data["address_work"].get("street_2") is not None
            and user_data["address_work"].get("apt_num") is None
        ):
            user.address.unit = user_data["address_work"].get("street_2")
        if (
            user_data["address_work"].get("apt_num") is not None
            and user_data["address_work"].get("street_2") is None
        ):
            user.address.unit = user_data["address_work"].get("apt_num")
        if (
            user_data["address_work"].get("apt_num") is not None
            and user_data["address_work"].get("street_2") is not None
        ):
            user.address.unit = user_data["address_work"].get("apt_num")
            if user.address.address is None:
                user.address.address = user_data["address_work"].get("street_2")
            else:
                user.address.address = f'{user.address.address}, {user_data["address_work"].get("street_2")}'
        if user_data["address_work"].get("city") is not None:
            user.address.city = user_data["address_work"].get("city")
        if user_data["address_work"].get("state") is not None:
            user.address.state = user_data["address_work"].get("state")
        if user_data["address_work"].get("zip") is not None:
            user.address.zip = user_data["address_work"].get("zip")

    # Home Address
    if user_data.get("address_home") is not None:
        if (
            user_data["address_home"].get("street") is not None
            or user_data["address_home"].get("apt_num") is not None
            or user_data["address_home"].get("street_2") is not None
            or user_data["address_home"].get("city") is not None
            or user_data["address_home"].get("state") is not None
            or user_data["address_home"].get("zip") is not None
        ):
            user.initializeAttribute("home_address", Address)

        if user_data["address_home"].get("street") is not None:
            user.home_address.address = user_data["address_home"].get("street")
        ## LS Supports both Apt Num and Street2
        if (
            user_data["address_home"].get("street_2") is not None
            and user_data["address_home"].get("apt_num") is None
        ):
            user.home_address.unit = user_data["address_home"].get("street_2")
        if (
            user_data["address_home"].get("apt_num") is not None
            and user_data["address_home"].get("street_2") is None
        ):
            user.home_address.unit = user_data["address_home"].get("apt_num")
        if (
            user_data["address_home"].get("apt_num") is not None
            and user_data["address_home"].get("street_2") is not None
        ):
            user.home_address.unit = user_data["address_home"].get("apt_num")
            if user.home_address.address is None:
                user.home_address.address = user_data["address_home"].get("street_2")
            else:
                user.home_address.address = f'{user.home_address.address}, {user_data["address_home"].get("street_2")}'
        if user_data["address_home"].get("city") is not None:
            user.home_address.city = user_data["address_home"].get("city")
        if user_data["address_home"].get("state") is not None:
            user.home_address.state = user_data["address_home"].get("state")
        if user_data["address_home"].get("zip") is not None:
            user.home_address.zip = user_data["address_home"].get("zip")

    if user_data.get("dynamic_process") is not None:
        user.dynamic_process_id = user_data["dynamic_process"].get("dynamic_process_id")
        user.dynamic_process_uuid = user_data["dynamic_process"].get(
            "dynamic_process_uuid"
        )
        user.dynamic_process_name = user_data["dynamic_process"].get(
            "dynamic_process_name"
        )

    if user_data.get("organization_affiliation") is not None:
        user.organization = 1

    standard_key_list = standard_user_keys()
    custom_fields = {
        key: value for key, value in user_data.items() if key not in standard_key_list
    }
    if custom_fields is not None:
        user.custom_fields = custom_fields
    del custom_fields

    return user


def count_of_pro_bono_assignments(*, pro_bono_assignment_list: DAList) -> int:
    """Simple function that checks how many pro bono assignments there are.

    Args:
        pro_bono_assignment_list (DAList): List of the Pro Bono Assignments.

    Returns:
        An integer value of the number of assignments thus gathered."""
    count = 0
    count = pro_bono_assignment_list.number_gathered()
    return count


def populate_pro_bono_assignments(
    *,
    pro_bono_assignment_list: DAList,
    assignment_list: DAList,
    legalserver_data: dict | None = None,
    legalserver_matter_uuid: str = "",
    legalserver_site: str = "",
    user_custom_fields: List | None = None,
) -> DAList:
    """
    This is a keyword defined function that takes a DAList of Individuals and populates
    it with the user data of all the assigned Pro Bono assignments on a case
    whose assignments have not yet been ended. This needs
    `populate_assignment()` run first so that it can parse the list of assignments
    on the case for the current primary assignment.

    Args:
        pro_bono_assignment_list (DAList[Individual]): DAList object of
            Individual objects that will be returned
        assignment_list (DAList[DAObject]): DAList of DAObjects
        legalserver_data (Dict | None): Optional dictionary of the matter data
            from a LegalServer request
        legalserver_matter_uuid (str): needed if the `legalserver_data` is not provided
        legalserver_site (str): needed if the `legalserver_data` is not provided
        user_custom_fields (list): Optional list of custom fields to gather on the User record.

    Returns:
        The supplied DAList of Individuals.
    """
    pro_bono_list = []
    if len(assignment_list) == 0:
        assignment_list = populate_assignments(
            assignment_list=assignment_list,
            legalserver_data=legalserver_data,
            legalserver_matter_uuid=legalserver_matter_uuid,
            legalserver_site=legalserver_site,
        )
    for item in assignment_list:
        if isinstance(item, DAObject):
            if item.type == "Pro Bono" and item.end_date is None:
                pro_bono_list.append({"uuid": item.user_uuid})
    for item in pro_bono_list:
        if isinstance(item, dict):
            new_user = Individual()
            user_data = get_user_details(
                legalserver_site=legalserver_site,
                legalserver_user_uuid=item["uuid"],
                custom_fields=user_custom_fields,
            )
            new_user = populate_user_data(user=new_user, user_data=user_data)
            pro_bono_assignment_list.append(new_user)

    pro_bono_assignment_list.gathered = True

    return pro_bono_assignment_list


def get_legalserver_report_data(
    *,
    legalserver_site: str,
    display_hidden_columns: bool = False,
    report_number: int,
    report_params: Dict | None = None,
) -> Dict:
    """This is a function that will get a LegalServer report and return the data
    in a python dictionary.

    This uses the LegalServer Reports API to get any report type data back from
    LegalServer and return it as a python dictionary. LegalServer Report APIs can
    return data in either JSON or XML format and this will parse either into a
    python dictionary. Note that LegalServer's JSON content is not perfect. True/False
    are rendered as 't' and 'f' instead of JSON booleans. Also numbers are
    returned as strings. It is also worth noting that the Reports API typically
    defaults to include hidden columns. This function defaults to exclude them
    unless otherwise specified.

    Args:
        legalserver_site (str): The LegalServer Site being queried
        display_hidden_columns (bool): This will allow for hidden columns (in the
            LegalServer Report) to be excluded or included from the results
        report number (int): This indicates which report should be retrieved
        report_params (dict): This is available for any additional filters

    Returns:
        This returns a dictionary of the reports API results.

    Raises:
        This can raise exceptions for any standard errors from the Requests API handler.
    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)

    url = f"https://{legalserver_site}.legalserver.org/modules/report/api_export.php"

    if not report_params:
        report_params = {}

    report_params["display_hidden_columns"] = display_hidden_columns

    report_api_key = (
        docassemble.base.functions.get_config("legalserver")
        .get(legalserver_site)
        .get("report " + str(report_number))
    )
    report_params["api_key"] = report_api_key
    report_params["load"] = str(report_number)  # type: ignore
    dict_response = {}  # type: ignore
    try:
        log(
            f"Attempting to retrive the following report {str(report_params)} from {legalserver_site}"
        )
        response = requests.get(
            headers=header_content, url=url, params=report_params, timeout=(3, 30)
        )
        response.raise_for_status()
        log(f"data received. headers: {str(response.headers)}, data: {response.text}")
        content_type = response.headers.get("Content-Type", "")

        if "application/xml" in content_type or "text/xml" in content_type:
            # Parse the XML response using lxml and convert it to JSON

            xml_data = etree.fromstring(response.text)  # type: ignore

            # Create a function to recursively convert an ElementTree into a dictionary
            def element_to_dict(element):
                if len(element) == 0:
                    return element.text
                result = {}
                for child in element:
                    child_data = element_to_dict(child)
                    if child.tag in result:
                        if isinstance(result[child.tag], list):
                            result[child.tag].append(child_data)
                        else:
                            result[child.tag] = [result[child.tag], child_data]
                    else:
                        result[child.tag] = child_data
                return result

            if xml_data is not None:
                # Use the xml_to_dict function to recursively convert XML to a dictionary
                dict_response = element_to_dict(xml_data)

        elif "application/json" in content_type:
            # The response is already JSON
            dict_response = response.json()

    except etree.ParseError as e:
        log(f"LegalServer report with {str(report_params)} failed: {e}")
        return {"error": e}
    except requests.exceptions.ConnectionError as e:
        log(f"LegalServer retrieving report with {str(report_params)} failed: {e}")
        return {"error": e}
    except requests.exceptions.HTTPError as e:
        log(f"LegalServer retrieving report with {str(report_params)} failed: {e}")
        return {"error": e}
    except requests.exceptions.Timeout as e:
        log(f"LegalServer retrieving report with {str(report_params)} failed: {e}")
        return {"error": e}
    except Exception as e:
        log(f"LegalServer retrieving report with {str(report_params)} failed: {e}")
        return {"error": e}

    return dict_response


def list_templates(package_name: str = "") -> List:
    """This is a helper function that will list all of the files in the data/templates
    directory of a given Docassemble Package.

    Args:
        package_name (str): The package being queried for templates.
            If not included, it defaults to the current package.

    Returns:
        This returns a list of the files available in the Templates directory.
    """

    if package_name:
        if "docassemble-" in package_name:
            package = package_name.replace("docassemble-", "docassemble.")
        else:
            package = package_name
        template_path = f"{package}:data/templates/README.md"
    else:
        template_path = "data/templates/README.md"

    files = [
        str(path)
        for path in os.listdir(os.path.dirname(path_and_mimetype(template_path)[0]))
        if not path.startswith(".")
    ]
    if "README.md" in files:
        files.remove("README.md")
    return files
