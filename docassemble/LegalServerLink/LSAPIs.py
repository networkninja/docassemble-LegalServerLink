import requests
import pycountry
import json
import defusedxml.ElementTree as etree
from datetime import date
from docassemble.base.functions import get_config, defined
from docassemble.base.util import (
    log,
    Address,
    Individual,
    DAList,
    DAObject,
    Person,
    IndividualName,
    Name,
    current_datetime,
    date_interval,
    date_difference,
    path_and_mimetype,
    DAFile,
)
import zipfile
from typing import List, Dict, Union, Optional, Any
import os.path
from os import listdir
import re
from typing import Dict, List, Union, Optional, Any

__all__ = [
    "check_custom_fields",
    "check_for_valid_fields",
    "check_legalserver_token",
    "count_of_pro_bono_assignments",
    "country_code_from_name",
    "get_contact_details",
    "get_document",
    "get_matter_details",
    "get_organization_details",
    "get_user_details",
    "get_legalserver_report_data",
    "human_readable_size",
    "is_zip_file",
    "language_code_from_name",
    "list_templates",
    "populate_additional_names",
    "populate_adverse_parties",
    "populate_assignments",
    "populate_associated_cases",
    "populate_case",
    "populate_charges",
    "populate_client",
    "populate_contacts",
    "populate_contact_data",
    "populate_current_user",
    "populate_documents",
    "populate_event_data",
    "populate_events",
    "populate_first_pro_bono_assignment",
    "populate_given_contact",
    "populate_given_event",
    "populate_given_organization",
    "populate_given_task",
    "populate_given_user",
    "populate_income",
    "populate_latest_pro_bono_assignment",
    "populate_litigations",
    "populate_organization_data",
    "populate_non_adverse_parties",
    "populate_notes",
    "populate_primary_assignment",
    "populate_pro_bono_assignments",
    "populate_services",
    "populate_tasks",
    "populate_user_data",
    "post_file_to_legalserver_documents_webhook",
    "search_contact_data",
    "search_document_data",
    "search_event_data",
    "search_matter_additional_names",
    "search_matter_adverse_parties",
    "search_matter_assignments_data",
    "search_matter_charges_data",
    "search_matter_contacts_data",
    "search_matter_income_data",
    "search_matter_litigation_data",
    "search_matter_notes_data",
    "search_matter_non_adverse_parties",
    "search_matter_services_data",
    "search_task_data",
    "search_user_data",
    "search_organization_data",
    "search_user_organization_affiliation",
    "standard_adverse_party_keys",
    "standard_charges_keys",
    "standard_client_home_address_keys",
    "standard_contact_keys",
    "standard_document_keys",
    "standard_event_keys",
    "standard_litigation_keys",
    "standard_matter_keys",
    "standard_non_adverse_party_keys",
    "standard_organization_affiliation_keys",
    "standard_organization_keys",
    "standard_services_keys",
    "standard_task_keys",
    "standard_user_keys",
    "check_for_valid_fields",
]


def check_custom_fields(response_obj):
    """
    Check if the response contains any custom fields at the top level.
    Custom fields are identified by ending with an underscore followed by an integer.

    Args:
        response_obj: The parsed JSON response object (dict)

    Returns:
        tuple: (bool, list) where:
            - bool: True if custom fields are present, False otherwise
            - list: List of custom field keys found
    """
    if not isinstance(response_obj, dict):
        return False, []

    # Pattern for custom fields: ending with underscore followed by digits
    pattern = re.compile(r"_\d+$")

    # Find all custom field keys
    custom_keys = [
        key
        for key in response_obj.keys()
        if isinstance(key, str) and pattern.search(key)
    ]

    # Return whether custom fields exist and the list of custom field keys
    return bool(custom_keys), custom_keys


def check_for_valid_fields(*, source_list: list, module: str) -> bool:
    """Checks whether the list provided meets the following criteria:
    1. Is a valid list (use the has_valid_items function) of strings
    2. All the strings either match the standard keys present for a module (like standard_matter_keys() for matters) or
    are valid custom fields with the format of `custom_field_name_1`, `custom_field_name_2`, etc.

    Args:
        source_list (list): The list of field names to check
        module (str): The module type to check against (e.g., 'matter', 'contact', 'task', etc.)

    Returns:
        bool: True if all fields are valid, False otherwise
    """
    # First check if the list is valid
    if not has_valid_items(source_list):
        return False

    # Get the appropriate standard keys based on the module
    standard_keys = []
    if module.lower() == "matters":
        standard_keys = standard_matter_keys()
    elif module.lower() == "contacts":
        standard_keys = standard_contact_keys()
    elif module.lower() == "events":
        standard_keys = standard_event_keys()
    elif module.lower() == "tasks":
        standard_keys = standard_task_keys()
    elif module.lower() == "documents":
        standard_keys = standard_document_keys()
    elif module.lower() == "organizations":
        standard_keys = standard_organization_keys()
    elif module.lower() == "organization_affiliations":
        standard_keys = standard_organization_affiliation_keys()
    elif module.lower() == "services":
        standard_keys = standard_services_keys()
    elif module.lower() == "litigations":
        standard_keys = standard_litigation_keys()
    elif module.lower() == "charges":
        standard_keys = standard_charges_keys()
    elif module.lower() == "adverse_parties":
        standard_keys = standard_adverse_party_keys()
    elif module.lower() == "non_adverse_parties":
        standard_keys = standard_non_adverse_party_keys()
    else:
        log(f"Unknown module type: {module}. Cannot check for valid fields.")
        raise ValueError(
            f"Unknown module type: {module}. Cannot check for valid fields."
        )
    # Check each field in the source list
    for field in source_list:
        # Skip empty strings - already checked by has_valid_items
        if not field.strip():
            continue

        # Check if it's a standard field
        if field in standard_keys:
            continue
        else:
            # If not a standard field, check if it's a valid custom field format
            # Custom fields should follow pattern like custom_field_name_1
            pattern = re.compile(r"^[a-zA-Z0-9_]+_\d+$")
            if not pattern.search(field):
                # Not a standard field or properly formatted custom field
                return False

    return True


def check_legalserver_token(*, legalserver_site: str) -> Dict:
    """Checks the API token of the site and checks its validity.

    Args:
        legalserer_site_abbreviation (str): Required string

    Responses:
        Dictionary. Key named error is included if there is an error. Otherwise a
            key named no_error is included. The key contains the details for the error.
    """
    config = get_config("legalserver")
    if not config:
        return {"error": "No LegalServer API credentials found in configuration."}
    apikey = config.get(legalserver_site.lower())
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


def count_of_pro_bono_assignments(*, pro_bono_assignment_list: DAList) -> int:
    """Simple function that checks how many pro bono assignments there are.

    Args:
        pro_bono_assignment_list (DAList): List of the Pro Bono Assignments.

    Returns:
        An integer value of the number of assignments thus gathered."""
    count = 0
    count = pro_bono_assignment_list.number_gathered()
    return count


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


def human_readable_size(size_bytes: Union[int, float]) -> str:
    """
    Convert size in bytes to a human-readable format (KB, MB, GB, etc.)

    Args:
        size_bytes (int or float): The size in bytes.

    Returns:
        str: Human-readable size string.

    Raises:
        ValueError: If size_bytes is negative or not a number.
    """
    if not isinstance(size_bytes, (int, float)):
        raise ValueError("size_bytes must be an integer or float")
    if size_bytes < 0:
        raise ValueError("size_bytes must be non-negative")
    if size_bytes == 0:
        return "0B"

    size_names = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1

    return f"{size_bytes:.2f} {size_names[i]}"


def get_contact_details(
    *,
    legalserver_site: str,
    legalserver_contact_uuid: str,
    custom_fields: list | None = None,
    custom_results: list = [],
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
        custom_results (list): An optional list of fields to return.

    Returns:
        A dictionary for the specific contact.

    Raises:
        Errors are handled in the response. Errors will be present when the
        dictionary response includes a key of 'error'
    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/contacts/{legalserver_contact_uuid}"

    queryparam_data = {}
    if custom_fields:
        if has_valid_items(custom_fields):
            queryparam_data["custom_fields"] = format_field_list(custom_fields)

    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="contacts"):
            queryparam_data["custom_results"] = format_field_list(custom_results)

    return_data = get_legalserver_response(
        url=url,
        params=queryparam_data,
        legalserver_site=legalserver_site,
        source_type="contacts",
        header_content=header_content,
        uuid=legalserver_contact_uuid,
    )

    return return_data


def get_document(
    *, legalserver_site: str, document_uuid: str, document_name: str = "document.pdf"
) -> tuple[DAFile | None, bool]:
    """
    Retrieves a document from the LegalServer API.
    Args:
        legalserver_site (str): The LegalServer site URL.
        document_uuid (str): The unique identifier of the document.
        document_name (str): The name to save the document as. Defaults to "document.pdf".
    Returns:
        tuple: (DAFile, bool) - The downloaded document file and a success boolean.
    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)

    the_file = DAFile()
    the_file.set_random_instance_name()
    the_file.initialize(filename=document_name)
    url = (
        "https://" + legalserver_site + ".legalserver.org/modules/document/download.php"
    )
    queryparams = {"unique_id": document_uuid}

    try:
        log(
            f"Attempting to retrieve the following file {str(document_uuid)} from {legalserver_site}"
        )
        response = requests.get(
            headers=header_content, url=url, params=queryparams, timeout=(3, 30)
        )
        response.raise_for_status()

        open(the_file.path(), "wb").write(response.content)
        the_file.commit()
        return the_file, True

    except Exception as e:
        log(f"LegalServer retrieving document with {str(queryparams)} failed: {e}")
        return None, False


def get_event_details(
    *,
    legalserver_site: str,
    legalserver_event_uuid: str,
    custom_fields: list | None = None,
    sort: str | None = None,
    custom_results: list = [],
) -> Dict:
    """Get details about a specific Event record in LegalServer.

    This uses LegalServer's Get Event API to get back details of just
    one specific event record.

    Args:
        legalserver_site (str): The specific LegalServer site to
            check for the organization on.
        legalserver_event_uuid (dict): The UUID of the specific LegalServer
            event to retrieve
        custom_fields (list): A optional list of custom fields to include.
        sort (str): Optional string to sort the results by. Defaults to ASC.
        custom_results (list): An optional list of fields to return.

    Returns:
        A dictionary for the event record.

    Raises:
        Errors are handled in the response. Errors will be present when the
        dictionary response includes a key of 'error'
    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/events/{legalserver_event_uuid}"

    queryparam_data: Dict[str, Union[str, List[str]]] = {}
    if custom_fields:
        if has_valid_items(custom_fields):
            queryparam_data["custom_fields"] = format_field_list(custom_fields)

    if sort in {"asc", "desc"}:
        queryparam_data["sort"] = sort

    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="events"):
            queryparam_data["custom_results"] = format_field_list(custom_results)

    return_data = get_legalserver_response(
        url=url,
        params=queryparam_data,
        legalserver_site=legalserver_site,
        source_type="events",
        header_content=header_content,
        uuid=legalserver_event_uuid,
    )

    return return_data


def get_matter_details(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    custom_fields: list[str] | None = None,
    custom_fields_services: list[str] | None = None,
    custom_fields_litigations: list[str] | None = None,
    custom_fields_charges: list[str] | None = None,
    sort: str | None = None,
    custom_results: list = [],
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
        sort (str): optional string to sort the results by. Defaults to ASC.
        custom_results (list): An optional list of fields to return.

    Returns:
        A dictionary of the LegalServer Matter details.

    Raises:
        Exceptions are returned as the reponse dictionary with a key of `error`.
    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)

    header_content["Accept"] = "application/json"

    base_url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/"

    queryparam_data: Dict[str, Union[str, List[str]]] = {}

    if custom_fields:
        if has_valid_items(custom_fields):
            queryparam_data["custom_fields"] = format_field_list(custom_fields)

    if custom_fields_litigations:
        if has_valid_items(custom_fields_litigations):
            queryparam_data["custom_fields_litigations"] = format_field_list(
                custom_fields_litigations
            )

    if custom_fields_charges:
        if has_valid_items(custom_fields_charges):
            queryparam_data["custom_fields_charges"] = format_field_list(
                custom_fields_charges
            )

    if custom_fields_services:
        if has_valid_items(custom_fields_services):
            queryparam_data["custom_fields_services"] = format_field_list(
                custom_fields_services
            )

    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="matters"):
            queryparam_data["custom_results"] = format_field_list(custom_results)

    if sort == "asc":
        queryparam_data["sort"] = "asc"
    elif sort == "desc":
        queryparam_data["sort"] = "desc"

    # Construct the full URL with custom fields in the query string
    url = base_url

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
    sort: str | None = None,
    custom_results: list = [],
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
        sort (str): Optional string to sort the results by. Defaults to ASC.
        custom_results (list): An optional list of fields to return.

    Returns:
        A dictionary for the specific organization.

    Raises:
        Errors are handled in the response. Errors will be present when the
        dictionary response includes a key of 'error'


    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/organizations/{legalserver_organization_uuid}"
    queryparam_data: Dict[str, Union[str, List[str]]] = {}

    if custom_fields:
        if has_valid_items(custom_fields):
            queryparam_data["custom_fields"] = format_field_list(custom_fields)

    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="organizations"):
            queryparam_data["custom_results"] = format_field_list(custom_results)

    if sort == "asc":
        queryparam_data["sort"] = "asc"
    elif sort == "desc":
        queryparam_data["sort"] = "desc"

    return_data = get_legalserver_response(
        url=url,
        params=queryparam_data,
        legalserver_site=legalserver_site,
        source_type="organization",
        header_content=header_content,
        uuid=legalserver_organization_uuid,
    )

    return return_data


def get_task_details(
    *,
    legalserver_site: str,
    legalserver_task_uuid: str,
    custom_fields: list | None = None,
    sort: str | None = None,
    custom_results: list = [],
) -> Dict:
    """This returns information about a specific Task in LegalServer.

    This uses LegalServer's Get Task API to get back details of just
    one specific of Task.

    Args:
        legalserver_site (str): The specific LegalServer site to
            check for the task on.
        legalserver_task_uuid (dict): The UUID of the specific LegalServer
            task to retrieve
        custom_fields (list): A optional list of custom fields to include.
        sort (str): Optional string to sort the results by. Defaults to ASC.
        custom_results (list): An optional list of fields to return.

    Returns:
        A dictionary for the specific task.

    Raises:
        Errors are handled in the response. Errors will be present when the
        dictionary response includes a key of 'error'


    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/tasks/{legalserver_task_uuid}"
    queryparam_data: Dict[str, Union[str, List[str]]] = {}

    if custom_fields:
        if has_valid_items(custom_fields):
            queryparam_data["custom_fields"] = format_field_list(custom_fields)

    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="tasks"):
            queryparam_data["custom_results"] = format_field_list(custom_results)

    if sort == "asc":
        queryparam_data["sort"] = "asc"
    elif sort == "desc":
        queryparam_data["sort"] = "desc"

    return_data = get_legalserver_response(
        url=url,
        params=queryparam_data,
        legalserver_site=legalserver_site,
        source_type="tasks",
        header_content=header_content,
        uuid=legalserver_task_uuid,
    )

    return return_data


def get_user_details(
    *,
    legalserver_site: str,
    legalserver_user_uuid: str,
    custom_fields: list | None = None,
    custom_results: list = [],
    sort: str | None = None,
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
        custom_results (list): An optional list of fields to return.

    Returns:
        A dictionary with the specific user data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/users/{legalserver_user_uuid}"
    queryparam_data = {}

    if custom_fields:
        if has_valid_items(custom_fields):
            queryparam_data["custom_fields"] = format_field_list(custom_fields)
    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="matters"):
            queryparam_data["custom_results"] = format_field_list(custom_results)

    if sort == "asc":
        queryparam_data["sort"] = "asc"
    elif sort == "desc":
        queryparam_data["sort"] = "desc"

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


def element_to_dict(element) -> Union[Dict[str, Any], Optional[str]]:
    """
    Recursively converts an XML element to a Python dictionary.

    This function translates an XML element structure into a nested dictionary
    representation,preserving the hierarchical structure of the XML. It handles
    elements with text content, child elements, and repeated elements by
    converting them to lists.

    Args:
        element: An XML element object (typically from ElementTree)

    Returns:
        dict or str: If the element has children, returns a dictionary where
            keys are child tag names and values are either dictionaries (for
            single child elements), lists of dictionaries (for repeated child
            elements), or strings (for text content). If the element has no
            children, returns the element's text content.

    Example:
        For XML like:
        <parent>
            <child>text1</child>
            <child>text2</child>
            <other>value</other>
        </parent>

        Returns:
        {
            'child': ['text1', 'text2'],
            'other': 'value'
        }
    """
    if len(element) == 0:
        return element.text
    result: Dict[str, Any] = {}
    for child in element:
        child_data: Union[Dict[str, Any], Optional[str]] = element_to_dict(child)
        if child.tag in result:
            if isinstance(result[child.tag], list):
                result[child.tag].append(child_data)
            else:
                result[child.tag] = [result[child.tag], child_data]
        else:
            result[child.tag] = child_data
    return result


def get_legalserver_report_data(
    *,
    legalserver_site: str,
    display_hidden_columns: bool = False,
    report_number: int,
    report_params: Dict | None = None,
) -> Dict[str, str | List[Dict[str, str | int | bool]]]:
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
        get_config("legalserver")
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

            if xml_data is not None:
                # Use the xml_to_dict function to recursively convert XML to a dictionary
                xml_dict_result = element_to_dict(xml_data)
                if isinstance(xml_dict_result, dict):
                    dict_response = xml_dict_result
                else:
                    dict_response = {
                        "error": "XML conversion did not result in a dictionary"
                    }

        elif "application/json" in content_type:
            # The response is already JSON
            dict_response = response.json()

    except etree.ParseError as e:
        log(f"LegalServer report with {str(report_params)} failed: {e}")
        return {"error": str(e)}
    except requests.exceptions.ConnectionError as e:
        log(f"LegalServer retrieving report with {str(report_params)} failed: {e}")
        return {"error": str(e)}
    except requests.exceptions.HTTPError as e:
        log(f"LegalServer retrieving report with {str(report_params)} failed: {e}")
        return {"error": str(e)}
    except requests.exceptions.Timeout as e:
        log(f"LegalServer retrieving report with {str(report_params)} failed: {e}")
        return {"error": str(e)}
    except Exception as e:
        log(f"LegalServer retrieving report with {str(report_params)} failed: {e}")
        return {"error": str(e)}

    return dict_response  # type: ignore


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
    config = get_config("legalserver")
    if not config:
        raise Exception("No LegalServer API credentials found in configuration.")
    apikey = config.get(legalserver_site.lower())
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
                source = search_matter_income_data(
                    legalserver_site=legalserver_site,
                    legalserver_matter_uuid=legalserver_matter_uuid,
                )
            elif source_type == "associated_cases":
                source = []
                # no search associated cases endpoint in LegalServer, this is
                # returned in the general search results
            elif source_type == "documents":
                source = search_document_data(
                    legalserver_site=legalserver_site,
                    legalserver_matter_uuid=legalserver_matter_uuid,
                )
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


def has_valid_items(field_list: Optional[List[str]]) -> bool:
    """Check if a list contains at least one non-empty string.

    Args:
        field_list: A list of strings to check, or None

    Returns:
        True if the list exists and contains at least one non-empty string,
        False otherwise
    """
    return field_list is not None and any(item.strip() for item in field_list)


def format_field_list(field_list: List[str]) -> str:
    """Format a list of fields with proper quoting for the LegalServer API.

    Args:
        field_list: A list of field names to format

    Returns:
        A string in the format ["field1","field2"] with empty fields removed
    """
    valid_fields = [f'"{field}"' for field in field_list if field.strip()]
    return f"[{','.join(valid_fields)}]"


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

    template_dir_path = path_and_mimetype(template_path)[0]
    if template_dir_path is None:
        files = []
    else:
        files = [
            str(path)
            for path in os.listdir(os.path.dirname(template_dir_path))
            if not path.startswith(".")
        ]
    if "README.md" in files:
        files.remove("README.md")
    return files


def loop_through_legalserver_responses(
    url: str,
    params: Dict,
    header_content: Dict,
    source_type: str,
    legalserver_site: str,
    page_limit: int | None = None,
) -> List:
    """Helper function to properly loop through LegalServer Search Responses."""
    return_data = []
    total_number_of_pages = 1
    counter = 0

    while (
        counter < total_number_of_pages
        and total_number_of_pages > 0
        and (page_limit is None or counter < page_limit)
    ):
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
            return [{"error": str(e)}]
        except requests.exceptions.HTTPError as e:
            log(
                f"Error getting LegalServer {source_type} data for {str(params)} "
                f"on {url}. Exception raised: {str(e)}."
            )
            return [{"error": str(e)}]
        except requests.exceptions.Timeout as e:
            log(
                f"Error getting LegalServer {source_type} data for {str(params)} "
                f"on {url}. Exception raised: {str(e)}."
            )
            return [{"error": str(e)}]
        except Exception as e:
            log(
                f"Error searching LegalServer {source_type} data for {str(params)} "
                f"on {url}. Exception raised: {str(e)}."
            )
            return [{"error": "Unknown"}]
    return return_data


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
            if item.get("id") is not None:
                new_name.id = item.get("id")
            if item.get("first") is not None:
                new_name.first = item.get("first")
            if item.get("middle") is not None:
                new_name.middle = item.get("middle")
            if item.get("type") is not None and isinstance(item["type"], dict):
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
            if item.get("id") is not None:
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
                new_ap.initializeAttribute("name", Name)
                new_ap.name.text = item.get("organization_name")
            if item.get("business_type") is not None and isinstance(
                item.get("business_type"), dict
            ):
                if item.get("business_type").get("lookup_value_name") is not None:
                    new_ap.business_type = item["business_type"].get(
                        "lookup_value_name"
                    )
            if item.get("date_of_birth") is not None:
                new_ap.date_of_birth = item.get("date_of_birth")
            if item.get("approximate_dob") is not None:
                new_ap.approximate_dob = item.get("approximate_dob")
            if item.get("relationship_type") is not None and isinstance(
                item.get("relationship_type"), dict
            ):
                if item["relationship_type"].get("lookup_value_name") is not None:
                    new_ap.relationship_type = item["relationship_type"].get(
                        "lookup_value_name"
                    )
            if item.get("language") is not None and isinstance(
                item.get("language"), dict
            ):
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
            if item.get("race") is not None and isinstance(item.get("race"), dict):
                if item["race"].get("lookup_value_name") is not None:
                    new_ap.race = item["race"].get("lookup_value_name")
            if item.get("drivers_license") is not None:
                new_ap.drivers_license = item.get("drivers_license")
            if item.get("visa_number") is not None:
                new_ap.visa_number = item.get("visa_number")
            if item.get("immigration_status") is not None and isinstance(
                item.get("immigration_status"), dict
            ):
                if item["immigration_status"].get("lookup_value_name") is not None:
                    new_ap.immigration_status = item["immigration_status"].get(
                        "lookup_value_name"
                    )
            if item.get("marital_status") is not None and isinstance(
                item.get("marital_status"), dict
            ):
                if item["marital_status"].get("lookup_value_name") is not None:
                    new_ap.marital_status = item["marital_status"].get(
                        "lookup_value_name"
                    )
            if item.get("gender") is not None and isinstance(item.get("gender"), dict):
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
            if item.get("county") is not None and isinstance(item.get("county"), dict):
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
            else:
                new_ap.custom_fields = {}
            del custom_fields

            new_ap.complete = True

    adverse_party_list.gathered = True
    return adverse_party_list


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
                # these fields are all required by the application so will never
                # be null or not present.
                new_assignment.uuid = item.get("uuid")
                # these fields could be null or not present, so we check

                if item.get("id") is not None:
                    new_assignment.id = item.get("id")
                if item.get("type") is not None and isinstance(item.get("type"), dict):
                    if item["type"].get("lookup_value_name") is not None:
                        new_assignment.type = item["type"].get("lookup_value_name")

                new_assignment.start_date = item.get("start_date")
                new_assignment.end_date = item.get("end_date")
                if item.get("program") is not None and isinstance(
                    item.get("program"), dict
                ):
                    if item["program"].get("lookup_value_name") is not None:
                        new_assignment.program = item["program"].get(
                            "lookup_value_name"
                        )
                if item.get("user") is not None and isinstance(item.get("user"), dict):
                    if item["user"].get("user_uuid") is not None:
                        new_assignment.user_uuid = item["user"].get("user_uuid")
                    if item["user"].get("user_name") is not None:
                        new_assignment.user_name = item["user"].get("user_name")
                if item.get("date_requested") is not None:
                    new_assignment.date_requested = item.get("date_requested")
                if item.get("confirmed") is not None:
                    new_assignment.confirmed = item.get("confirmed")
                if item.get("notes") is not None:
                    new_assignment.notes = item.get("notes")
                if item.get("created_at") is not None:
                    new_assignment.created_at = item.get("created_at")
                if item.get("satisfies_outreach_training_credit") is not None:
                    new_assignment.satisfies_outreach_training_credit = item.get(
                        "satisfies_outreach_training_credit"
                    )
                if item.get("office") is not None and isinstance(item["office"], dict):
                    if item["office"].get("office_name") is not None:
                        new_assignment.office_name = item["office"].get("office_name")
                    if item["office"].get("office_code") is not None:
                        new_assignment.office_code = item["office"].get("office_code")
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


def populate_associated_cases(
    *,
    associated_case_list: DAList,
    legalserver_data: dict | None = None,
    legalserver_matter_uuid: str = "",
    legalserver_site: str = "",
) -> DAList:
    """Take the data from LegalServer and populate a list of LegalServer associated cases
    into a DAList of DAObjects.

    This is a keyword defined function that takes a DAList of DAObjects and
    populates it with the associated case details related to a case. If the general
    legalserver_data from the `get_matter_details` response is not included, it
    does not make a separate API call since there is no dedicated endpoint.

    Args:
        associated_case_list (DAList[DAObject]): DAList of DAObjects.
        legalserver_data (dict): Optional dictionary of the matter data from a
            LegalServer request.
        legalserver_matter_uuid (str): needed if the `legalserver_data` is not
            provided.
        legalserver_site (str): needed if the `legalserver_data` is
            not provided.

    Returns:
        A DAList of DAObjects with each being a separate income record."""

    source = get_source_module_data(
        source_type="associated_cases",
        legalserver_data=legalserver_data,
        legalserver_matter_uuid=legalserver_matter_uuid,
        legalserver_site=legalserver_site,
    )

    if source:
        for item in source:
            if isinstance(item, dict):
                # item: DAObject = item  # type annotation
                new_case = associated_case_list.appendObject()
                new_case.matter = item.get("matter")
                new_case.matter_uuid = item.get("matter_uuid")

                new_case.matter_identification_number = item.get(
                    "matter_identification_number"
                )

                new_case.complete = True

    associated_case_list.gathered = True
    return associated_case_list


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
    case.uuid = legalserver_data.get("uuid")
    if legalserver_data.get("case_number") is not None:
        case.case_number = legalserver_data.get("case_number")
    if legalserver_data.get("case_id") is not None:
        case.case_id = legalserver_data.get("case_id")
    if legalserver_data.get("case_profile_url") is not None:
        case.profile_url = legalserver_data.get("case_profile_url")
    if legalserver_data.get("case_disposition") is not None and isinstance(
        legalserver_data.get("case_disposition"), dict
    ):
        if legalserver_data["case_disposition"].get("lookup_value_name") is not None:
            case.case_disposition = legalserver_data["case_disposition"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("is_this_a_prescreen") is not None:
        case.is_this_a_prescreen = legalserver_data.get("is_this_a_prescreen")
    if legalserver_data.get("is_group") is not None:
        case.is_group = legalserver_data.get("is_group")
    if legalserver_data.get("case_email_address") is not None:
        case.email = legalserver_data.get("case_email_address")
    if legalserver_data.get("rejected") is not None:
        case.rejected = legalserver_data.get("rejected")
    rejection_reason = legalserver_data.get("rejection_reason")
    if isinstance(rejection_reason, dict):
        lookup_value_name = rejection_reason.get("lookup_value_name")
        if lookup_value_name is not None:
            case.rejection_reason = lookup_value_name
    if legalserver_data.get("dynamic_process") is not None and isinstance(
        legalserver_data["dynamic_process"], dict
    ):
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
    if legalserver_data.get("prescreen_user") is not None and isinstance(
        legalserver_data.get("prescreen_user"), dict
    ):
        if legalserver_data["prescreen_user"].get("user_uuid") is not None:
            case.prescreen_user_uuid = legalserver_data["prescreen_user"].get(
                "user_uuid"
            )
        if legalserver_data["prescreen_user"].get("user_name") is not None:
            case.prescreen_user_name = legalserver_data["prescreen_user"].get(
                "user_name"
            )
    if legalserver_data.get("prescreen_program") is not None and isinstance(
        legalserver_data.get("prescreen_program"), dict
    ):
        if legalserver_data["prescreen_program"].get("lookup_value_name") is not None:
            case.prescreen_program = legalserver_data["prescreen_program"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("prescreen_office") is not None and isinstance(
        legalserver_data["prescreen_office"], dict
    ):
        if legalserver_data.get("prescreen_office") is not None:
            if legalserver_data["prescreen_office"].get("office_code") is not None:
                case.prescreen_office_code = legalserver_data["prescreen_office"].get(
                    "office_code"
                )
        if legalserver_data["prescreen_office"].get("office_name") is not None:
            case.prescreen_office_name = legalserver_data["prescreen_office"].get(
                "office_name"
            )
    if legalserver_data.get("intake_user") is not None and isinstance(
        legalserver_data.get("intake_user"), dict
    ):
        if legalserver_data["intake_user"].get("user_uuid") is not None:
            case.intake_user_uuid = legalserver_data["intake_user"].get("user_uuid")
        if legalserver_data["intake_user"].get("user_name") is not None:
            case.intake_user_name = legalserver_data["intake_user"].get("user_name")
    if legalserver_data["intake_program"].get(
        "lookup_value_name"
    ) is not None and isinstance(legalserver_data.get("intake_program"), dict):
        case.intake_program = legalserver_data["intake_program"].get(
            "lookup_value_name"
        )
    if legalserver_data.get("intake_office") is not None and isinstance(
        legalserver_data["intake_office"], dict
    ):
        if legalserver_data["intake_office"].get("office_code") is not None:
            case.intake_office_code = legalserver_data["intake_office"].get(
                "office_code"
            )
        if legalserver_data["intake_office"].get(
            "office_name"
        ) is not None and isinstance(legalserver_data["intake_office"], dict):
            case.intake_office_name = legalserver_data["intake_office"].get(
                "office_name"
            )
    if legalserver_data["prescreen_screening_status"].get(
        "lookup_value_name"
    ) is not None and isinstance(
        legalserver_data.get("prescreen_screening_status"), dict
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
    if legalserver_data.get("county_of_dispute") is not None and isinstance(
        legalserver_data["county_of_dispute"], dict
    ):
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
    if legalserver_data["legal_problem_code"].get(
        "lookup_value_name"
    ) is not None and isinstance(legalserver_data["legal_problem_code"], dict):
        case.legal_problem_code = legalserver_data["legal_problem_code"].get(
            "lookup_value_name"
        )
    if legalserver_data["legal_problem_category"].get(
        "lookup_value_name"
    ) is not None and isinstance(legalserver_data["legal_problem_category"], dict):
        case.legal_problem_category = legalserver_data["legal_problem_category"].get(
            "lookup_value_name"
        )
    if legalserver_data.get("special_legal_problem_code") is not None and isinstance(
        legalserver_data["special_legal_problem_code"], list
    ):
        temp_list = []
        for slpc in legalserver_data["special_legal_problem_code"]:
            if slpc.get("lookup_value_name") is not None:
                temp_list.append(slpc.get("lookup_value_name"))
        if temp_list:
            case.special_legal_problem_code = temp_list
        del temp_list
    if legalserver_data.get("intake_type") is not None and isinstance(
        legalserver_data["intake_type"], dict
    ):
        if legalserver_data["intake_type"].get("lookup_value_name") is not None:
            case.intake_type = legalserver_data["intake_type"].get("lookup_value_name")
    if legalserver_data.get("case_type") is not None and isinstance(
        legalserver_data["case_type"], dict
    ):
        if legalserver_data["case_type"].get("lookup_value_name") is not None:
            case.case_type = legalserver_data["case_type"].get("lookup_value_name")
    if legalserver_data.get("impact") is not None:
        case.impact = legalserver_data.get("impact")
    if legalserver_data.get("special_characteristics") is not None and isinstance(
        legalserver_data["special_characteristics"], list
    ):
        temp_list = []
        for sc in legalserver_data["special_characteristics"]:
            if sc.get("lookup_value_name") is not None:
                temp_list.append(sc.get("lookup_value_name"))
        if temp_list:
            case.special_characteristics = temp_list
        del temp_list
    if legalserver_data.get("case_status") is not None and isinstance(
        legalserver_data["case_status"], dict
    ):
        if legalserver_data["case_status"].get("lookup_value_name") is not None:
            case.case_status = legalserver_data["case_status"].get("lookup_value_name")
    if legalserver_data.get("close_reason") is not None and isinstance(
        legalserver_data["close_reason"], dict
    ):
        if legalserver_data["close_reason"].get("lookup_value_name") is not None:
            case.close_reason = legalserver_data["close_reason"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("pro_bono_opportunity_summary") is not None:
        case.pro_bono_opportunity_summary = legalserver_data.get(
            "pro_bono_opportunity_summary"
        )
    if legalserver_data.get("pro_bono_opportunity_county") is not None and isinstance(
        legalserver_data["pro_bono_opportunity_county"], dict
    ):
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
    if legalserver_data.get("pro_bono_engagement_type") is not None and isinstance(
        legalserver_data["pro_bono_engagement_type"], dict
    ):
        if (
            legalserver_data["pro_bono_engagement_type"].get("lookup_value_name")
            is not None
        ):
            case.pro_bono_engagement_type = legalserver_data[
                "pro_bono_engagement_type"
            ].get("lookup_value_name")
    if legalserver_data.get("pro_bono_time_commitment") is not None and isinstance(
        legalserver_data["pro_bono_time_commitment"], dict
    ):
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
    if legalserver_data.get("pro_bono_skills_developed") is not None and isinstance(
        legalserver_data["pro_bono_skills_developed"], list
    ):
        temp_list = []
        for skill in legalserver_data["pro_bono_skills_developed"]:
            if skill.get("lookup_value_name") is not None:
                temp_list.append(skill.get("lookup_value_name"))
        if temp_list:
            case.pro_bono_skills_developed = temp_list
        del temp_list
    if legalserver_data.get(
        "pro_bono_appropriate_volunteer"
    ) is not None and isinstance(
        legalserver_data["pro_bono_appropriate_volunteer"], list
    ):
        temp_list = []
        for vol in legalserver_data["pro_bono_appropriate_volunteer"]:
            if vol.get("lookup_value_name") is not None:
                temp_list.append(vol.get("lookup_value_name"))
        if temp_list != []:
            case.pro_bono_appropriate_volunteer = temp_list
        del temp_list
    if legalserver_data.get("pro_bono_expiration_date") is not None:
        case.pro_bono_expiration_date = legalserver_data.get("pro_bono_expiration_date")
    if legalserver_data.get("pro_bono_opportunity_status") is not None and isinstance(
        legalserver_data["pro_bono_opportunity_status"], dict
    ):
        if (
            legalserver_data["pro_bono_opportunity_status"].get("lookup_value_name")
            is not None
        ):
            case.pro_bono_opportunity_status = legalserver_data[
                "pro_bono_opportunity_status"
            ].get("lookup_value_name")
    if legalserver_data.get("pro_bono_opportunity_cc") is not None:
        case.pro_bono_opportunity_cc = legalserver_data.get("pro_bono_opportunity_cc")
    if legalserver_data.get(
        "simplejustice_opportunity_legal_topic"
    ) is not None and isinstance(
        legalserver_data["simplejustice_opportunity_legal_topic"], list
    ):
        temp_list = []
        for topic in legalserver_data["simplejustice_opportunity_legal_topic"]:
            if topic.get("lookup_value_name") is not None:
                temp_list.append(topic.get("lookup_value_name"))
        if temp_list != []:
            case.simplejustice_opportunity_legal_topic = temp_list
        del temp_list
    if legalserver_data.get(
        "simplejustice_opportunity_helped_community"
    ) is not None and isinstance(
        legalserver_data["simplejustice_opportunity_helped_community"], list
    ):
        temp_list = []
        for community in legalserver_data["simplejustice_opportunity_helped_community"]:
            if community.get("lookup_value_name") is not None:
                temp_list.append(community.get("lookup_value_name"))
        if temp_list != []:
            case.simplejustice_opportunity_helped_community = temp_list
        del temp_list
    if legalserver_data.get(
        "simplejustice_opportunity_skill_type"
    ) is not None and isinstance(
        legalserver_data["simplejustice_opportunity_skill_type"], list
    ):
        temp_list = []
        for skill in legalserver_data["simplejustice_opportunity_skill_type"]:
            if skill.get("lookup_value_name") is not None:
                temp_list.append(skill.get("lookup_value_name"))
        if temp_list != []:
            case.simplejustice_opportunity_skill_type = temp_list
        del temp_list
    if legalserver_data.get(
        "simplejustice_opportunity_community"
    ) is not None and isinstance(
        legalserver_data["simplejustice_opportunity_community"], list
    ):
        temp_list = []
        for community in legalserver_data["simplejustice_opportunity_community"]:
            if community.get("lookup_value_name") is not None:
                temp_list.append(community.get("lookup_value_name"))
        if temp_list != []:
            case.simplejustice_opportunity_community = temp_list
        del temp_list
    if legalserver_data.get("level_of_expertise") is not None and isinstance(
        legalserver_data["level_of_expertise"], dict
    ):
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
    if legalserver_data.get("how_referred") is not None and isinstance(
        legalserver_data["how_referred"], dict
    ):
        if legalserver_data["how_referred"].get("lookup_value_name") is not None:
            case.how_referred = legalserver_data["how_referred"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("number_of_adults") is not None:
        case.number_of_adults = legalserver_data.get("number_of_adults")
    if legalserver_data.get("number_of_children") is not None:
        case.number_of_children = legalserver_data.get("number_of_children")
    if legalserver_data.get("online_intake_payload") is not None:
        case.online_intake_payload = legalserver_data.get("online_intake_payload")
    if legalserver_data.get("case_restrictions") is not None and isinstance(
        legalserver_data.get("case_restrictions"), list
    ):
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
    if legalserver_data.get("ssi_welfare_status") is not None and isinstance(
        legalserver_data["ssi_welfare_status"], dict
    ):
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
    if legalserver_data.get("ssi_section8_housing_type") is not None and isinstance(
        legalserver_data["ssi_section8_housing_type"], dict
    ):
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
    if legalserver_data.get("additional_assistance") is not None and isinstance(
        legalserver_data.get("additional_assistance"), list
    ):
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
    if legalserver_data.get("priorities") is not None and isinstance(
        legalserver_data.get("priorities"), list
    ):
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
    if legalserver_data.get("income_change_type") is not None and isinstance(
        legalserver_data["income_change_type"], dict
    ):
        if legalserver_data["income_change_type"].get("lookup_value_name") is not None:
            case.income_change_type = legalserver_data["income_change_type"].get(
                "lookup_value_name"
            )

    if legalserver_data.get("hud_entity_poverty_band") is not None and isinstance(
        legalserver_data["hud_entity_poverty_band"], dict
    ):
        if (
            legalserver_data["hud_entity_poverty_band"].get("lookup_value_name")
            is not None
        ):
            case.hud_entity_poverty_band = legalserver_data[
                "hud_entity_poverty_band"
            ].get("lookup_value_name")
    if legalserver_data.get("hud_statewide_poverty_band") is not None and isinstance(
        legalserver_data["hud_statewide_poverty_band"], dict
    ):
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
    if legalserver_data.get("hud_ami_category") is not None and isinstance(
        legalserver_data["hud_ami_category"], dict
    ):
        if legalserver_data["hud_ami_category"].get("lookup_value_name") is not None:
            case.hud_ami_category = legalserver_data["hud_ami_category"].get(
                "lookup_value_name"
            )

    if legalserver_data.get("sharepoint_site_library") is not None and isinstance(
        legalserver_data["sharepoint_site_library"], dict
    ):
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
    if legalserver_data.get("branch") is not None and isinstance(
        legalserver_data["branch"], dict
    ):
        if legalserver_data["branch"].get("lookup_value_name") is not None:
            case.branch = legalserver_data["branch"].get("lookup_value_name")
    if legalserver_data.get("military_status") is not None and isinstance(
        legalserver_data["military_status"], dict
    ):
        if legalserver_data["military_status"].get("lookup_value_name") is not None:
            case.military_status = legalserver_data["military_status"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("external_id") is not None:
        case.external_id = legalserver_data.get("external_id")
    if legalserver_data.get("created_by_integration_or_api") is not None:
        case.created_by_integration_or_api = legalserver_data.get(
            "created_by_integration_or_api"
        )
    if legalserver_data.get("modified_by_integration_or_api") is not None:
        case.modified_by_integration_or_api = legalserver_data.get(
            "modified_by_integration_or_api"
        )
    if legalserver_data.get("trial_date") is not None:
        case.trial_date = legalserver_data.get("trial_date")
    if legalserver_data.get("date_of_appointment_retention") is not None:
        case.date_of_appointment_retention = legalserver_data.get(
            "date_of_appointment_retention"
        )
    if legalserver_data.get("api_integration_preference") is not None and isinstance(
        legalserver_data["api_integration_preference"], dict
    ):
        if (
            legalserver_data["api_integration_preference"].get("lookup_value_name")
            is not None
        ):
            case.api_integration_preference = legalserver_data[
                "api_integration_preference"
            ].get("lookup_value_name")
    if legalserver_data.get("court_tracking_numbers") is not None and isinstance(
        legalserver_data.get("court_tracking_numbers"), list
    ):
        temp_list = []
        for num in legalserver_data["court_tracking_numbers"]:
            if num.get("court_tracking_number") is not None:
                temp_list.append(num.get("court_tracking_number"))
        if temp_list:
            case.court_tracking_numbers = temp_list
        del temp_list
    if legalserver_data.get("sharepoint_tracer_document_id") is not None:
        case.sharepoint_tracer_document_id = legalserver_data.get(
            "sharepoint_tracer_document_id"
        )
    if legalserver_data.get("dropbox_folder_id") is not None:
        case.dropbox_folder_id = legalserver_data.get("dropbox_folder_id")
    if legalserver_data.get("google_drive_folder_id") is not None:
        case.google_drive_folder_id = legalserver_data.get("google_drive_folder_id")

    # Custom Fields are funny
    standard_key_list = standard_matter_keys()
    custom_fields = {
        key: value
        for key, value in legalserver_data.items()
        if key not in standard_key_list
    }
    if custom_fields is not None:
        case.custom_fields = custom_fields
    else:
        case.custom_fields = {}

    log(f"LegalServer Case Object populated for a case.")

    return case


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

                new_charge.uuid = item.get("charge_uuid")
                if item.get("id") is not None:
                    new_charge.id = item.get("id")
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
                if item.get("lookup_charge") is not None and isinstance(
                    item["lookup_charge"], dict
                ):
                    if item["lookup_charge"].get("charge_uuid") is not None:
                        new_charge.lookup_charge_uuid = item["lookup_charge"].get(
                            "charge_uuid"
                        )
                    if item["lookup_charge"].get("lookup_charge") is not None:
                        new_charge.lookup_charge = item["lookup_charge"].get(
                            "lookup_charge"
                        )
                if item.get("charge_outcome_id") is not None and isinstance(
                    item["charge_outcome_id"], dict
                ):
                    if item["charge_outcome_id"].get("lookup_value_name") is not None:
                        new_charge.charge_outcome_id = item["charge_outcome_id"].get(
                            "lookup_value_name"
                        )
                if item.get("charge_name") is not None:
                    new_charge.charge_name = item.get("charge_name")
                if item.get("disposition_date") is not None:
                    new_charge.disposition_date = item.get("disposition_date")
                if item.get("top_charge") is not None:
                    new_charge.top_charge = item.get("top_charge")
                if item.get("note") is not None:
                    new_charge.note = item.get("note")
                if item.get("previous_charge_id") is not None:
                    if item["previous_charge_id"].get("lookup_value_name") is not None:
                        new_charge.previous_charge_id = item["previous_charge_id"].get(
                            "lookup_value_name"
                        )
                if item.get("charge_reduction_date") is not None:
                    new_charge.charge_reduction_date = item.get("charge_reduction_date")
                if item.get("charge_tag_id") is not None and isinstance(
                    item.get("charge_tag_id"), list
                ):
                    # charge_tag_id is a list of dicts, so we need to extract the names
                    # from the lookup_value_name key in each dict
                    temp_list = []
                    for tag in item["charge_tag_id"]:
                        if tag.get("lookup_value_name") is not None:
                            temp_list.append(tag.get("lookup_value_name"))
                    if temp_list:
                        new_charge.charge_tag_id = temp_list
                    del temp_list
                if item.get("issue_note") is not None:
                    new_charge.issue_note = item.get("issue_note")
                if item.get("dynamic_process") is not None and isinstance(
                    item["dynamic_process"], dict
                ):
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
                if item.get("external_id") is not None:
                    new_charge.external_id = item.get("external_id")

                standard_key_list = standard_charges_keys()
                custom_fields = {
                    key: value
                    for key, value in item.items()
                    if key not in standard_key_list
                }
                if custom_fields is not None:
                    new_charge.custom_fields = custom_fields
                else:
                    new_charge.custom_fields = {}
                del custom_fields
                new_charge.complete = True

    log(f"Charges Populated for a case.")

    charge_list.gathered = True
    return charge_list


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
    client.client_id = legalserver_data.get("client_id")
    if legalserver_data.get("ssn") is not None:
        client.ssn = legalserver_data.get("ssn")
    if legalserver_data.get("veteran") is not None:
        client.is_veteran = legalserver_data.get("veteran")
    if legalserver_data.get("client_gender") is not None and isinstance(
        legalserver_data.get("client_gender"), dict
    ):
        if legalserver_data["client_gender"].get("lookup_value_name") is not None:
            client.gender = legalserver_data["client_gender"].get("lookup_value_name")
    elif isinstance(legalserver_data.get("client_gender"), str):
        client.gender = legalserver_data.get("client_gender")
    if legalserver_data.get("client_email_address") is not None:
        client.email = legalserver_data.get("client_email_address")
    if legalserver_data.get("date_of_birth") is not None:
        client.birthdate = legalserver_data.get("date_of_birth")
    if legalserver_data.get("dob_status") is not None and isinstance(
        legalserver_data["dob_status"], dict
    ):
        if legalserver_data["dob_status"].get("lookup_value_name") is not None:
            client.dob_status = legalserver_data["dob_status"].get("lookup_value_name")
    if legalserver_data.get("ssn_status") is not None and isinstance(
        legalserver_data["ssn_status"], dict
    ):
        if legalserver_data["ssn_status"].get("lookup_value_name") is not None:
            client.ssn_status = legalserver_data["ssn_status"].get("lookup_value_name")
    if legalserver_data.get("prefix") is not None and isinstance(
        legalserver_data["prefix"], dict
    ):
        if legalserver_data["prefix"].get("lookup_value_name") is not None:
            client.salutation_to_use = legalserver_data["prefix"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("disabled") is not None:
        client.is_disabled = legalserver_data.get("disabled")
    if legalserver_data.get("employment_status") is not None and isinstance(
        legalserver_data["employment_status"], dict
    ):
        if legalserver_data["employment_status"].get("lookup_value_name") is not None:
            client.employment_status = legalserver_data["employment_status"].get(
                "lookup_value_name"
            )
        elif isinstance(legalserver_data.get("employment_status"), str):
            client.employment_status = legalserver_data.get("employment_status")
    if legalserver_data.get("pronouns") is not None and isinstance(
        legalserver_data["pronouns"], dict
    ):
        if legalserver_data["pronouns"].get("lookup_value_name") is not None:
            client.preferred_pronouns = legalserver_data["pronouns"].get(
                "lookup_value_name"
            )

    if legalserver_data.get("preferred_phone_number") is not None and isinstance(
        legalserver_data["preferred_phone_number"], dict
    ):
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
        client.work_phone = legalserver_data.get("work_phone")
    if legalserver_data.get("fax_phone") is not None:
        client.fax_phone = legalserver_data.get("fax_phone")
    if legalserver_data.get("home_phone_note") is not None:
        client.phone_number_note = legalserver_data.get("home_phone_note")
    if legalserver_data.get("mobile_phone_note") is not None:
        client.mobile_number_note = legalserver_data.get("mobile_phone_note")
    if legalserver_data.get("other_phone_note") is not None:
        client.other_phone_note = legalserver_data.get("other_phone_note")
    if legalserver_data.get("work_phone_note") is not None:
        client.work_phone_note = legalserver_data.get("work_phone_note")
    if legalserver_data.get("fax_phone_note") is not None:
        client.fax_phone_note = legalserver_data.get("fax_phone_note")
    if legalserver_data.get("home_phone_safe") is not None:
        client.phone_number_safe = legalserver_data.get("home_phone_safe")
    if legalserver_data.get("mobile_phone_safe") is not None:
        client.mobile_number_safe = legalserver_data.get("mobile_phone_safe")
    if legalserver_data.get("other_phone_safe") is not None:
        client.other_phone_safe = legalserver_data.get("other_phone_safe")
    if legalserver_data.get("work_phone_safe") is not None:
        client.work_phone_safe = legalserver_data.get("work_phone_safe")
    if legalserver_data.get("fax_phone_safe") is not None:
        client.fax_phone_safe = legalserver_data.get("fax_phone_safe")

    if legalserver_data.get("language") is not None and isinstance(
        legalserver_data["language"], dict
    ):
        if legalserver_data["language"].get("lookup_value_name") is not None:
            client.language_name = legalserver_data["language"].get("lookup_value_name")
            if (
                language_code_from_name(
                    str(legalserver_data["language"].get("lookup_value_name"))
                )
                != "Unknown"
            ):
                client.language = language_code_from_name(
                    str(legalserver_data["language"].get("lookup_value_name"))
                )
    if legalserver_data.get("second_language") is not None and isinstance(
        legalserver_data["second_language"], dict
    ):
        if legalserver_data["second_language"].get("lookup_value_name") is not None:
            client.second_language_name = legalserver_data["second_language"].get(
                "lookup_value_name"
            )
            if (
                language_code_from_name(
                    str(legalserver_data["second_language"].get("lookup_value_name"))
                )
                != "Unknown"
            ):
                client.second_language = language_code_from_name(
                    str(legalserver_data["second_language"].get("lookup_value_name"))
                )

    if legalserver_data.get("preferred_spoken_language") is not None and isinstance(
        legalserver_data["preferred_spoken_language"], dict
    ):
        if (
            legalserver_data["preferred_spoken_language"].get("lookup_value_name")
            is not None
        ):
            client.preferred_spoken_language_name = legalserver_data[
                "preferred_spoken_language"
            ].get("lookup_value_name")
            if (
                language_code_from_name(
                    str(
                        legalserver_data["preferred_spoken_language"].get(
                            "lookup_value_name"
                        )
                    )
                )
                != "Unknown"
            ):
                client.preferred_spoken_language = language_code_from_name(
                    str(
                        legalserver_data["preferred_spoken_language"].get(
                            "lookup_value_name"
                        )
                    )
                )

    if legalserver_data.get("preferred_written_language") is not None and isinstance(
        legalserver_data["preferred_written_language"], dict
    ):
        if (
            legalserver_data["preferred_written_language"].get("lookup_value_name")
            is not None
        ):
            client.preferred_written_language_name = legalserver_data[
                "preferred_written_language"
            ].get("lookup_value_name")
            if (
                language_code_from_name(
                    str(
                        legalserver_data["preferred_written_language"].get(
                            "lookup_value_name"
                        )
                    )
                )
                != "Unknown"
            ):
                client.preferred_written_language = language_code_from_name(
                    str(
                        legalserver_data["preferred_written_language"].get(
                            "lookup_value_name"
                        )
                    )
                )

    if legalserver_data.get("languages") is not None and isinstance(
        legalserver_data["languages"], list
    ):
        if (
            len(legalserver_data["languages"]) > 1
            or legalserver_data["languages"][0].get("lookup_value_name") is not None
        ):
            client.languages = []
            client.language_names = []
            for language in legalserver_data["languages"]:
                if language["lookup_value_name"] is not None:
                    client.language_names.append(language["lookup_value_name"])
                    if (
                        language_code_from_name(language["lookup_value_name"])
                        != "Unknown"
                    ):
                        client.languages.append(
                            language_code_from_name(language["lookup_value_name"])
                        )
    if legalserver_data.get("interpreter") is not None:
        client.interpreter = legalserver_data.get("interpreter")
    if legalserver_data.get("marital_status") is not None and isinstance(
        legalserver_data["marital_status"], dict
    ):
        if legalserver_data["marital_status"].get("lookup_value_name") is not None:
            client.marital_status = legalserver_data["marital_status"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("citizenship") is not None and isinstance(
        legalserver_data["citizenship"], dict
    ):
        if legalserver_data["citizenship"].get("lookup_value_name") is not None:
            client.citizenship = legalserver_data["citizenship"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("citizenship_country") is not None and isinstance(
        legalserver_data["citizenship_country"], dict
    ):
        if legalserver_data["citizenship_country"].get("lookup_value_name") is not None:
            client.citizenship_country = legalserver_data["citizenship_country"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("country_of_origin") is not None and isinstance(
        legalserver_data["country_of_origin"], dict
    ):
        if legalserver_data["country_of_origin"].get("lookup_value_name") is not None:
            client.country_of_origin = legalserver_data["country_of_origin"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("immigration_status") is not None and isinstance(
        legalserver_data.get("immigration_status"), dict
    ):
        if legalserver_data["immigration_status"].get("lookup_value_name") is not None:
            client.immigration_status = legalserver_data["immigration_status"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("a_number") is not None:
        client.a_number = legalserver_data.get("a_number")
    if legalserver_data.get("visa_number") is not None:
        client.visa_number = legalserver_data.get("visa_number")

    if legalserver_data.get("race") is not None and isinstance(
        legalserver_data.get("race"), dict
    ):
        if legalserver_data["race"].get("lookup_value_name") is not None:
            client.race = legalserver_data["race"].get("lookup_value_name")
    if legalserver_data.get("ethnicity") is not None and isinstance(
        legalserver_data.get("ethnicity"), dict
    ):
        if legalserver_data["ethnicity"].get("lookup_value_name") is not None:
            client.ethnicity = legalserver_data["ethnicity"].get("lookup_value_name")
    if legalserver_data.get("current_living_situation") is not None and isinstance(
        legalserver_data["current_living_situation"], dict
    ):
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
    if legalserver_data.get("birth_country") is not None and isinstance(
        legalserver_data["birth_country"], dict
    ):
        if legalserver_data["birth_country"].get("lookup_value_name") is not None:
            client.birth_country = legalserver_data["birth_country"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("drivers_license") is not None:
        client.drivers_license = legalserver_data.get("drivers_license")
    if legalserver_data.get("highest_education") is not None and isinstance(
        legalserver_data.get("highest_education"), dict
    ):
        if legalserver_data["highest_education"].get("lookup_value_name") is not None:
            client.highest_education = legalserver_data["highest_education"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("institutionalized") is not None:
        client.institutionalized = legalserver_data.get("institutionalized")
    if legalserver_data.get("institutionalized_at") is not None and isinstance(
        legalserver_data["institutionalized_at"], dict
    ):
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
    if legalserver_data.get("school_status") is not None and isinstance(
        legalserver_data.get("school_status"), dict
    ):
        if legalserver_data["school_status"].get("lookup_value_name") is not None:
            client.school_status = legalserver_data["school_status"].get(
                "lookup_value_name"
            )
    if legalserver_data.get("military_service") is not None and isinstance(
        legalserver_data.get("military_service"), dict
    ):
        if legalserver_data["military_service"].get("lookup_value_name") is not None:
            client.military_service = legalserver_data["military_service"].get(
                "lookup_value_name"
            )

    # Client Home Address
    if legalserver_data.get("client_address_home") is not None and isinstance(
        legalserver_data.get("client_address_home"), dict
    ):
        if legalserver_data["client_address_home"].get("street") is not None:
            client.address.address = legalserver_data["client_address_home"].get(
                "street"
            )
        else:
            client.address.address = "Unknown Street Address"
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
        if legalserver_data["client_address_home"].get("county") is not None:
            if (
                legalserver_data["client_address_home"]["county"].get(
                    "lookup_value_name"
                )
                is not None
            ):
                client.address.county = legalserver_data["client_address_home"][
                    "county"
                ].get("lookup_value_name")
        if legalserver_data["client_address_home"].get("safe_address") is not None:
            client.address.safe_address = legalserver_data["client_address_home"].get(
                "safe_address"
            )

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
                ].get("lookup_value_name")
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
    if legalserver_data.get("client_address_mailing") is not None and isinstance(
        legalserver_data.get("client_address_mailing"), dict
    ):
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
            else:
                client.mailing_address.address = "Unknown Street Address"
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
                and legalserver_data["client_address_mailing"].get("street_2")
                is not None
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
                client.mailing_address.zip = legalserver_data[
                    "client_address_mailing"
                ].get("zip")

    return client


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
                new_contact = populate_contact_data(
                    contact=new_contact, contact_data=item  # type: ignore
                )
                new_contact.complete = True
                log(f"Contacts Populated for a case.")

    contact_list.gathered = True
    return contact_list


def populate_contact_data(*, contact: Individual, contact_data: dict) -> Individual:
    """Take the data from LegalServer and populate an individual Contact Record.

    This is a keyword defined function that takes a given Individual and populates
    it with Contact data from LegalServer.

    Args:
        contact (Individual): required Individual for
            the contact.
        contact_data (dict): required dictionary of the contact data from a
            LegalServer request.

    Returns:
        An Individual object.

    Raises:
        TypeError: If contact_data is not a dictionary or contact is not an Individual.
    """
    try:
        if not isinstance(contact_data, dict):
            raise TypeError("contact_data must be a dictionary")

        if not isinstance(contact, Individual):
            raise TypeError("contact must be an Individual object")

        # Check if contact_data contains an error key
        if contact_data.get("error") is not None:
            log(f"Error in contact data: {contact_data.get('error')}")
            contact.has_error = True
            contact.error_message = str(contact_data.get("error"))
            return contact

        contact.uuid = contact_data.get("contact_uuid")
        if contact_data.get("id") is not None:
            contact.id = contact_data.get("id")
        if contact_data.get("case_contact_uuid") is not None:
            contact.case_contact_uuid = contact_data.get("case_contact_uuid")

        contact.initializeAttribute("name", IndividualName)
        if contact_data.get("first") is not None:
            contact.name.first = contact_data.get("first")
        if contact_data.get("middle") is not None:
            contact.name.middle = contact_data.get("middle")
        if contact_data.get("last") is not None:
            contact.name.last = contact_data.get("last")
        if contact_data.get("case_contact_type") is not None and isinstance(
            contact_data.get("case_contact_type"), dict
        ):
            if contact_data["case_contact_type"].get("lookup_value_name") is not None:
                contact.type = contact_data["case_contact_type"].get(
                    "lookup_value_name"
                )
        if contact_data.get("suffix") is not None:
            contact.name.suffix = contact_data.get("suffix")
        if contact_data.get("business_phone") is not None:
            contact.phone = contact_data.get("business_phone")
        if contact_data.get("email") is not None:
            contact.email = contact_data.get("email")

        templist = []
        if contact_data.get("type") is not None and isinstance(
            contact_data.get("type"), list
        ):
            for type in contact_data["type"]:
                if type.get("lookup_value_name") is not None:
                    templist.append(type.get("lookup_value_name"))
            if templist:
                contact.type = templist
        else:
            log(f"Error processing contact type data: not a list or missing")
        del templist

        templist = []
        if contact_data.get("contact_types") is not None and isinstance(
            contact_data.get("contact_types"), list
        ):
            # contact_types is a list of dicts, so we need to extract the names
            for type in contact_data["contact_types"]:
                if type.get("lookup_value_name") is not None:
                    templist.append(type.get("lookup_value_name"))
            if templist:
                contact.contact_types = templist
        else:
            log(f"Error processing contact_types data: not a list or missing")

        del templist

        try:
            standard_key_list = standard_contact_keys()
            custom_fields = {
                key: value
                for key, value in contact_data.items()
                if key not in standard_key_list
            }
            if custom_fields is not None:
                contact.custom_fields = custom_fields
            else:
                contact.custom_fields = {}
        except Exception as e:
            log(f"Error processing custom fields: {str(e)}")

        contact.complete = True

    except Exception as e:
        log(f"Error in populate_contact_data: {str(e)}")
        if isinstance(contact, dict | Individual | DAObject):
            contact.has_error = True
            contact.error_message = str(e)

    return contact


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


def populate_documents(
    *,
    document_list: DAList,
    legalserver_data: dict | None = None,
    legalserver_matter_uuid: str = "",
    legalserver_site: str = "",
) -> DAList:
    """Take the data from LegalServer and populate a list of LegalServer
    Document records into a DAList of DAObjects.

    This is a keyword defined function that takes a DAList of DAObjects and
    populates it with the document details related to a case. If the general
    legalserver_data from the `get_matter_details` response is not included, it will
    make an API call using the `search_matter_documents_data` function.

    Args:
        document_list (DAList[DAObject]): DAList of DAObjects.
        legalserver_data (dict): Optional dictionary of the matter data from a
            LegalServer request.
        legalserver_matter_uuid (str): needed if the `legalserver_data` is not
            provided.
        legalserver_site (str): needed if the `legalserver_data` is
            not provided.

    Returns:
        DAList of DAObjects
    """

    source = get_source_module_data(
        source_type="documents",
        legalserver_data=legalserver_data,
        legalserver_matter_uuid=legalserver_matter_uuid,
        legalserver_site=legalserver_site,
    )

    if source:
        for item in source:
            if isinstance(item, dict):
                # item: DAObject = item  # type annotation
                new_document = document_list.appendObject()
                new_document.uuid = item.get("uuid")
                if item.get("id") is not None:
                    new_document.id = item.get("id")
                if item.get("name") is not None:
                    new_document.name = item.get("name")
                else:
                    new_document.name = ""
                if item.get("title") is not None:
                    new_document.title = item.get("title")
                else:
                    new_document.title = ""
                if item.get("mime_type") is not None:
                    new_document.mime_type = item.get("mime_type")
                else:
                    new_document.mime_type = ""
                if item.get("virus_free") is not None:
                    new_document.virus_free = item.get("virus_free")
                if item.get("date_create") is not None:
                    new_document.date_create = item.get("date_create")
                if item.get("download_url") is not None:
                    new_document.download_url = item.get("download_url")
                if item.get("virus_scanned") is not None:
                    new_document.virus_scanned = item.get("virus_scanned")
                if item.get("disk_file_size") is not None:
                    new_document.disk_file_size = item.get("disk_file_size")
                else:
                    new_document.disk_file_size = 0
                if item.get("storage_backend") is not None and isinstance(
                    item.get("storage_backend"), dict
                ):
                    if item["storage_backend"].get("lookup_value_name") is not None:
                        new_document.storage_backend = item["storage_backend"].get(
                            "lookup_value_name"
                        )
                if item.get("type") is not None:
                    if item["type"].get("lookup_value_name") is not None and isinstance(
                        item.get("type"), dict
                    ):
                        new_document.type = item["type"].get("lookup_value_name")
                if item.get("programs") is not None and isinstance(
                    item.get("programs"), list
                ):
                    # programs is a list of dicts, so we need to extract the names
                    temp_list = []
                    for program in item["programs"]:
                        if program.get("lookup_value_name") is not None:
                            temp_list.append(program.get("lookup_value_name"))
                    if temp_list:
                        new_document.programs = temp_list
                    del temp_list
                if item.get("folder") is not None:
                    new_document.folder = item.get("folder")
                if item.get("funding_code") is not None:
                    new_document.funding_code = item.get("funding_code")
                if item.get("hyperlink") is not None:
                    new_document.hyperlink = item.get("hyperlink")
                if item.get("shared_with_sj_client") is not None:
                    new_document.shared_with_sj_client = item.get(
                        "shared_with_sj_client"
                    )
                new_document.complete = True

    log(f"Documents Populated for a case.")

    document_list.gathered = True

    return document_list


def populate_event_data(*, event: DAObject, event_data: dict) -> DAObject:
    """Take the data from LegalServer and populate a given event from the
    LegalServer data.

    This is a keyword defined function that takes a given DAObject and
    populates it with event details from LegalServer.
    Args:
        event (DAObject): DAObject for the event
        event_data (dict): Optional dictionary of the event data from a
            LegalServer request.

    Returns:
        A DAObject with the given event record.
    """

    # item: DAObject = item  # type annotation

    event.uuid = event_data.get("event_uuid")
    if event_data.get("id") is not None:
        event.id = event_data.get("id")
    if event_data.get("title") is not None:
        event.title = event_data.get("title")
    if event_data.get("location") is not None:
        event.location = event_data.get("location")
    if event_data.get("front_desk") is not None:
        event.front_desk = event_data.get("front_desk")
    if event_data.get("broadcast_event") is not None:
        event.broadcast_event = event_data.get("broadcast_event")
    if event_data.get("court") is not None and isinstance(
        event_data.get("court"), dict
    ):
        if event_data["court"].get("organization_name") is not None:
            event.court_name = event_data["court"].get("organization_name")
        if event_data["court"].get("organization_uuid") is not None:
            event.court_uuid = event_data["court"].get("organization_uuid")
    if event_data.get("courtroom") is not None:
        event.courtroom = event_data.get("courtroom")
    if event_data.get("event_type") is not None and isinstance(
        event_data.get("event_type"), dict
    ):
        if event_data["event_type"].get("lookup_value_name") is not None:
            event.event_type = event_data["event_type"].get("lookup_value_name")
    if event_data.get("judge") is not None:
        event.judge = event_data.get("judge")
    if event_data.get("attendees") is not None:
        event.attendees = event_data.get("attendees")
    if event_data.get("private_event") is not None:
        event.private_event = event_data.get("private_event")
    if event_data.get("attendees") is not None and isinstance(
        event_data.get("attendees"), list
    ):
        # attendees is a list of dicts, so we need to extract the user_uuid and user_name
        # from each dict and create a new list of dicts with those keys
        # if the user_uuid is not None
        temp_list = []
        for user in event_data["attendees"]:
            if user.get("user_uuid") is not None:
                temp_list.append(
                    {
                        "user_uuid": user.get("user_uuid"),
                        "user_name": user.get("user_name"),
                    }
                )
        if temp_list:
            event.attendees = temp_list
        del temp_list

    if event_data.get("dynamic_process_id") is not None and isinstance(
        event_data.get("dynamic_process_id"), dict
    ):
        if event_data["dynamic_process_id"].get("dynamic_process_id") is not None:
            event.dynamic_process_id = event_data["dynamic_process_id"].get(
                "dynamic_process_id"
            )
        if event_data["dynamic_process_id"].get("dynamic_process_uuid") is not None:
            event.dynamic_process_uuid = event_data["dynamic_process_id"].get(
                "dynamic_process_uuid"
            )
        if event_data["dynamic_process_id"].get("dynamic_process_name") is not None:
            event.dynamic_process_name = event_data["dynamic_process_id"].get(
                "dynamic_process_name"
            )
    # start and end dates of None if not otherwise
    # if item.get("start_datetime") is not None:
    event.start_datetime = event_data.get("start_datetime")
    # if item.get("end_datetime") is not None:
    event.end_datetime = event_data.get("end_datetime")
    if event_data.get("all_day_event") is not None:
        event.all_day_event = event_data.get("all_day_event")
    if event_data.get("program") is not None and isinstance(
        event_data.get("program"), dict
    ):
        if event_data["program"].get("lookup_value_name") is not None:
            event.program = event_data["program"].get("lookup_value_name")
    if event_data.get("office") is not None and isinstance(
        event_data.get("office"), dict
    ):
        if event_data["office"].get("office_name") is not None:
            event.office_name = event_data["office"].get("office_name")
        if event_data["office"].get("office_code") is not None:
            event.office_code = event_data["office"].get("office_code")
    if event_data.get("external_id") is not None:
        event.external_id = event_data.get("external_id")

    standard_key_list = standard_event_keys()
    custom_fields = {
        key: value for key, value in event_data.items() if key not in standard_key_list
    }
    if custom_fields is not None:
        event.custom_fields = custom_fields
    else:
        event.custom_fields = {}
    del custom_fields

    return event


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
                new_event = event_list.appendObject(DAObject)
                new_event = populate_event_data(event=new_event, event_data=item)
                new_event.complete = True

    event_list.gathered = True
    return event_list


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
    if not defined("assignment_list.gathered"):
        assignment_list = populate_assignments(
            assignment_list=assignment_list,
            legalserver_data=legalserver_data,
            legalserver_matter_uuid=legalserver_matter_uuid,
            legalserver_site=legalserver_site,
        )
    earliest_assignment_start_date = current_datetime()
    earliest_user_uuid = ""
    for assignment in assignment_list:
        if isinstance(assignment, DAObject):
            if assignment.end_date is None and assignment.type == "Pro Bono":
                if (
                    date_difference(
                        assignment.start_date,
                        earliest_assignment_start_date,
                    ).days  # type: ignore
                    > 0
                ):
                    earliest_user_uuid = assignment.user_uuid
                    earliest_assignment_start_date = assignment.start_date

    if not earliest_user_uuid == "":
        user_data = get_user_details(
            legalserver_site=legalserver_site,
            legalserver_user_uuid=earliest_user_uuid,
            custom_fields=user_custom_fields,
        )
        legalserver_first_pro_bono_assignment = populate_user_data(
            user=legalserver_first_pro_bono_assignment, user_data=user_data
        )
        legalserver_first_pro_bono_assignment.assignment_start_date = (
            earliest_assignment_start_date
        )
    del earliest_user_uuid
    del earliest_assignment_start_date
    return legalserver_first_pro_bono_assignment


def populate_given_contact(
    *,
    legalserver_contact: Individual,
    legalserver_contact_uuid: str,
    legalserver_site: str = "",
    contact_custom_fields: List | None = None,
) -> Individual:
    """
    This is a keyword defined function that takes an Individual object and populates
    it with the Contact data of the given LegalServer Contact.

    Args:
        legalserver_contact (Individual): Individual object that will be returned
        legalserver_contact_uuid (str):
        legalserver_site (str):
        contact_custom_fields (list): Optional list of custom fields to gather on the Contact record

    Returns:
        The supplied Individual object.
    """

    contact_data = get_contact_details(
        legalserver_site=legalserver_site,
        legalserver_contact_uuid=legalserver_contact_uuid,
        custom_fields=contact_custom_fields,
    )
    legalserver_contact = populate_contact_data(
        contact=legalserver_contact, contact_data=contact_data
    )
    return legalserver_contact


def populate_given_event(
    *,
    legalserver_event: DAObject,
    legalserver_event_uuid: str,
    legalserver_site: str = "",
    event_custom_fields: List | None = None,
) -> DAObject:
    """
    This is a keyword defined function that takes an DAObject object and populates
    it with the event data of the given LegalServer event.

    Args:
        legalserver_event (DAObject): DAObject object that will be returned
        legalserver_event_uuid (str):
        legalserver_site (str):
        event_custom_fields (list): Optional list of custom fields to gather on the Contact record

    Returns:
        The supplied DAObject object.
    """

    event_data = get_event_details(
        legalserver_site=legalserver_site,
        legalserver_event_uuid=legalserver_event_uuid,
        custom_fields=event_custom_fields,
    )
    legalserver_event = populate_event_data(
        event=legalserver_event, event_data=event_data
    )
    return legalserver_event


def populate_given_organization(
    *,
    legalserver_organization: Person,
    legalserver_organization_uuid: str,
    legalserver_site: str = "",
    organization_custom_fields: List | None = None,
) -> Person:
    """
    This is a keyword defined function that takes an Person object and populates
    it with the Organization data of a given LegalServer Organization.

    Args:
        legalserver_organization (Person): Person object that will be returned
        legalserver_organization_uuid (str):
        legalserver_site (str):
        organization_custom_fields (list): Optional list of custom fields to
            gather on the Organization record

    Returns:
        The supplied Person object.
    """

    organization_data = get_organization_details(
        legalserver_site=legalserver_site,
        legalserver_organization_uuid=legalserver_organization_uuid,
        custom_fields=organization_custom_fields,
    )
    legalserver_organization = populate_organization_data(
        organization=legalserver_organization, organization_data=organization_data
    )
    return legalserver_organization


def populate_given_task(
    *,
    legalserver_task: DAObject,
    legalserver_task_uuid: str,
    legalserver_site: str = "",
    task_custom_fields: List | None = None,
) -> DAObject:
    """
    This is a keyword defined function that takes a DAObject object and populates
    it with the Task data of the given LegalServer task.

    Args:
        legalserver_task (DAObject): DAObject object that will be returned
        legalserver_task_uuid (str):
        legalserver_site (str):
        task_custom_fields (list): Optional list of custom fields to gather on the Task record

    Returns:
        The supplied DAObject object.
    """

    task_data = get_task_details(
        legalserver_site=legalserver_site,
        legalserver_task_uuid=legalserver_task_uuid,
        custom_fields=task_custom_fields,
    )
    legalserver_task = populate_task_data(
        legalserver_task=legalserver_task, task_data=task_data
    )
    return legalserver_task


def populate_given_user(
    *,
    legalserver_user: Individual,
    legalserver_user_uuid: str,
    legalserver_site: str = "",
    user_custom_fields: List | None = None,
) -> Individual:
    """
    This is a keyword defined function that takes an Individual object and populates
    it with the user data of a given LegalServer user .

    Args:
        legalserver_user (Individual): Individual object that will be returned
        legalserver_user_uuid (str):
        legalserver_site (str):
        user_custom_fields (list): Optional list of custom fields to gather on the User record

    Returns:
        The supplied Individual object.
    """

    user_data = get_user_details(
        legalserver_site=legalserver_site,
        legalserver_user_uuid=legalserver_user_uuid,
        custom_fields=user_custom_fields,
    )
    legalserver_user = populate_user_data(user=legalserver_user, user_data=user_data)
    return legalserver_user


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
            if item.get("id") is not None:
                new_income.id = item.get("id")
            if item.get("family_id") is not None:
                new_income.family_id = item.get("family_id")
            if item.get("other_family") is not None:
                new_income.other_family = item.get("other_family")
            if item.get("type") is not None and isinstance(item.get("type"), dict):
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
    if not defined("assignment_list.gathered"):
        assignment_list = populate_assignments(
            assignment_list=assignment_list,
            legalserver_data=legalserver_data,
            legalserver_matter_uuid=legalserver_matter_uuid,
            legalserver_site=legalserver_site,
        )
    assignment_start_date = date.today() - date_interval(years=100)
    assignment_user_uuid = ""
    for assignment in assignment_list:
        if isinstance(assignment, DAObject):
            if assignment.end_date is None and assignment.type == "Pro Bono":
                if (
                    date_difference(
                        assignment.start_date,
                        assignment_start_date,
                    ).days  # type: ignore
                    < 0
                ):
                    assignment_user_uuid = assignment.user_uuid
                    assignment_start_date = assignment.start_date
    if not assignment_user_uuid == "":
        user_data = get_user_details(
            legalserver_site=legalserver_site,
            legalserver_user_uuid=assignment_user_uuid,
            custom_fields=user_custom_fields,
        )
        legalserver_latest_pro_bono_assignment = populate_user_data(
            user=legalserver_latest_pro_bono_assignment, user_data=user_data
        )
        legalserver_latest_pro_bono_assignment.assignment_start_date = (
            assignment_start_date
        )
    del assignment_start_date
    del assignment_user_uuid
    return legalserver_latest_pro_bono_assignment


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
                if item.get("court_id") is not None and isinstance(
                    item.get("court_id"), dict
                ):
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
                if item.get("dynamic_process") is not None and isinstance(
                    item.get("dynamic_process"), dict
                ):
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
                if item.get("litigation_relationship") is not None and isinstance(
                    item.get("litigation_relationship"), dict
                ):
                    if (
                        item["litigation_relationship"].get("lookup_value_name")
                        is not None
                    ):
                        new_litigation.litigation_relationship = item[
                            "litigation_relationship"
                        ].get("lookup_value_name")
                if item.get("filing_type") is not None and isinstance(
                    item.get("filing_type"), dict
                ):
                    if item["filing_type"].get("lookup_value_name") is not None:
                        new_litigation.filing_type = item["filing_type"].get(
                            "lookup_value_name"
                        )
                if item.get("number_of_people_served") is not None:
                    new_litigation.number_of_people_served = item.get(
                        "number_of_people_served"
                    )
                if item.get("external_id") is not None:
                    new_litigation.external_id = item.get("external_id")

                standard_key_list = standard_litigation_keys()
                custom_fields = {
                    key: value
                    for key, value in item.items()
                    if key not in standard_key_list
                }
                if custom_fields is not None:
                    new_litigation.custom_fields = custom_fields
                else:
                    new_litigation.custom_fields = {}
                del custom_fields
                new_litigation.complete = True
        log(f"Litigations Populated for a case.")
    litigation_list.gathered = True
    return litigation_list


def populate_organization_data(
    *, organization: Person, organization_data: Dict
) -> Person:
    """
    This is a keyword defined function that takes a Person object and populates
    it with the organization data of the relevant organization record.

    Args:
        organization (Person): Person object that will be returned
        organization_data (Dict | None): dictionary of the organization data
            from a LegalServer request

    Returns:
        The supplied Person object.
    """

    organization.uuid = organization_data.get("uuid")
    if organization_data.get("id") is not None:
        organization.id = organization_data.get("id")
    organization.initializeAttribute("name", IndividualName)
    if organization_data.get("name") is not None:
        organization.name.text = organization_data.get("name")

    if organization_data.get("abbreviation") is not None:
        organization.abbreviation = organization_data.get("abbreviation")
    if organization_data.get("description") is not None:
        organization.description = organization_data.get("description")
    if organization_data.get("referral_contact_phone") is not None:
        organization.referral_contact_phone = organization_data.get(
            "referral_contact_phone"
        )
    if organization_data.get("referral_contact_email") is not None:
        organization.referral_contact_email = organization_data.get(
            "referral_contact_email"
        )

    if organization_data.get("active") is not None:
        organization.active = organization_data.get("active")
    if organization_data.get("is_master") is not None:
        organization.is_master = organization_data.get("is_master")
    if organization_data.get("website") is not None:
        organization.website = organization_data.get("website")
    if organization_data.get("date_org_entered") is not None:
        organization.date_org_entered = organization_data.get("date_org_entered")
    if organization_data.get("parent_organization") is not None:
        organization.parent_organization = organization_data.get("parent_organization")

    if organization_data.get("types") is not None and isinstance(
        organization_data.get("types"), list
    ):
        # types is a list of dicts, so we need to extract the names
        temp_list = []
        for type in organization_data["types"]:
            if type.get("lookup_value_name") is not None:
                temp_list.append(type.get("lookup_value_name"))
        if temp_list:
            organization.types = temp_list
        del temp_list

    if organization_data.get("phone") is not None:
        organization.phone_business = organization_data.get("phone")
    if organization_data.get("fax") is not None:
        organization.phone_fax = organization_data.get("fax")

    if organization_data.get("external_site_uuids") is not None:
        organization.external_site_uuids = organization_data.get("external_site_uuids")
    organization.initializeAttribute("address", Address)
    if (
        organization_data.get("street") is not None
        and organization_data.get("street_2") is not None
        and organization_data.get("city") is not None
        and organization_data.get("state") is not None
        and organization_data.get("zip") is not None
    ):

        # Work Address
        if organization_data.get("street") is not None:
            organization.address.address = organization_data.get("street")
        ## LS Supports both Apt Num and Street2
        if organization_data.get("street_2") is not None:
            organization.address.unit = organization_data.get("street_2")

        if organization_data.get("city") is not None:
            organization.address.city = organization_data.get("city")
        if organization_data.get("state") is not None:
            organization.address.state = organization_data.get("state")
        if organization_data.get("zip") is not None:
            organization.address.zip = organization_data.get("zip")

    if organization_data.get("dynamic_process") is not None and isinstance(
        organization_data.get("dynamic_process"), dict
    ):
        organization.dynamic_process_id = organization_data["dynamic_process"].get(
            "dynamic_process_id"
        )
        organization.dynamic_process_uuid = organization_data["dynamic_process"].get(
            "dynamic_process_uuid"
        )
        organization.dynamic_process_name = organization_data["dynamic_process"].get(
            "dynamic_process_name"
        )

    standard_key_list = standard_organization_keys()
    custom_fields = {
        key: value
        for key, value in organization_data.items()
        if key not in standard_key_list
    }
    if custom_fields is not None:
        organization.custom_fields = custom_fields
    else:
        organization.custom_fields = {}
    del custom_fields

    return organization


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
            if item.get("id") is not None:
                new_nap.id = item.get("id")
            if item.get("organization_name") is None:
                new_nap.initializeAttribute("name", IndividualName)
                if item.get("first") is not None:
                    new_nap.name.first = item.get("first")
                if item.get("middle") is not None:
                    new_nap.name.middle = item.get("middle")
                if item.get("last") is not None:
                    new_nap.name.last = item.get("last")
                if item.get("suffix") is not None:
                    new_nap.name.suffix = item.get("suffix")
            else:
                new_nap.initializeAttribute("name", Name)
                new_nap.name.text = item.get("organization_name")
            if item.get("date_of_birth") is not None:
                new_nap.date_of_birth = item.get("date_of_birth")
            if item.get("approximate_dob") is not None:
                new_nap.approximate_dob = item.get("approximate_dob")
            if item.get("relationship_type") is not None and isinstance(
                item.get("relationship_type"), dict
            ):
                if item["relationship_type"].get("lookup_value_name") is not None:
                    new_nap.relationship_type = item["relationship_type"].get(
                        "lookup_value_name"
                    )
            if item.get("language") is not None and isinstance(
                item.get("language"), dict
            ):
                if item["language"].get("lookup_value_name") is not None:
                    new_nap.language_name = item["language"].get("lookup_value_name")
                    if (
                        language_code_from_name(
                            item["language"].get("lookup_value_name")
                        )
                        != "Unknown"
                    ):
                        new_nap.language = language_code_from_name(
                            item["language"].get("lookup_value_name")
                        )
            if item.get("gender") is not None and isinstance(item.get("gender"), dict):
                if item["gender"].get("lookup_value_name") is not None:
                    new_nap.gender = item["gender"].get("lookup_value_name")
            if item.get("ssn") is not None:
                new_nap.ssn = item.get("ssn")
            if item.get("country_of_birth") is not None and isinstance(
                item.get("country_of_birth"), dict
            ):
                ## TODO country codes
                if item["country_of_birth"].get("lookup_value_name") is not None:
                    new_nap.country_of_birth_name = item["country_of_birth"].get(
                        "lookup_value_name"
                    )
            if item.get("race") is not None and isinstance(item.get("race"), dict):
                if item["race"].get("lookup_value_name") is not None:
                    new_nap.race = item["race"].get("lookup_value_name")
            if item.get("veteran") is not None:
                new_nap.veteran = item.get("veteran")
            if item.get("disabled") is not None:
                new_nap.disabled = item.get("disabled")
            if item.get("hud_race") is not None and isinstance(
                item.get("hud_race"), dict
            ):
                if item["hud_race"].get("lookup_value_name") is not None:
                    new_nap.hud_race = item["hud_race"].get("lookup_value_name")
            if item.get("hud_9902_ethnicity") is not None and isinstance(
                item.get("hud_9902_ethnicity"), dict
            ):
                if item["hud_9902_ethnicity"].get("hud_9902_ethnicity") is not None:
                    new_nap.hud_9902_ethnicity = item["hud_9902_ethnicity"].get(
                        "lookup_value_name"
                    )
            if item.get("hud_disabling_condition") is not None and isinstance(
                item.get("hud_disabling_condition"), dict
            ):
                if item["hud_disabling_condition"].get("lookup_value_name") is not None:
                    new_nap.hud_disabling_condition = item[
                        "hud_disabling_condition"
                    ].get("lookup_value_name")
            if item.get("visa_number") is not None:
                new_nap.visa_number = item.get("visa_number")
            if item.get("immigration_status") is not None and isinstance(
                item.get("immigration_status"), dict
            ):
                if item["immigration_status"].get("lookup_value_name") is not None:
                    new_nap.immigration_status = item["immigration_status"].get(
                        "lookup_value_name"
                    )
            if item.get("citizenship_status") is not None and isinstance(
                item.get("citizenship_status"), dict
            ):
                if item["citizenship_status"].get("lookup_value_name") is not None:
                    new_nap.citizenship_status = item["citizenship_status"].get(
                        "lookup_value_name"
                    )
            if item.get("marital_status") is not None and isinstance(
                item.get("marital_status"), dict
            ):
                if item["marital_status"].get("lookup_value_name") is not None:
                    new_nap.marital_status = item["marital_status"].get(
                        "lookup_value_name"
                    )
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
            if item.get("county") is not None and isinstance(item.get("county"), dict):
                if item["county"].get("lookup_value_name") is not None:
                    new_nap.address.county = item["county"].get("lookup_value_name")
                    if item["county"].get("lookup_value_uuid") is not None:
                        new_nap.address.county_uuid = item["county"].get(
                            "lookup_value_uuid"
                        )
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
            else:
                new_nap.custom_fields = {}
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
                if item.get("id") is not None:
                    new_note.id = item.get("id")
                if item.get("subject") is not None:
                    new_note.subject = item.get("subject")
                if item.get("body") is not None:
                    new_note.body = item.get("body")
                if item.get("note_type") is not None and isinstance(
                    item.get("note_type"), dict
                ):
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
                if item.get("created_by") is not None and isinstance(
                    item.get("created_by"), dict
                ):
                    if item["created_by"].get("user_uuid") is not None:
                        new_note.created_by_uuid = item["created_by"].get("user_uuid")
                    if item["created_by"].get("user_name") is not None:
                        new_note.created_by_name = item["created_by"].get("user_name")
                if item.get("last_updated_by") is not None and isinstance(
                    item.get("last_updated_by"), dict
                ):
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
    if not defined("assignment_list.gathered"):
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
    if not defined("assignment_list.gathered"):
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

                new_service.uuid = item.get("uuid")
                if item.get("id") is not None:
                    new_service.id = item.get("id")
                if item.get("title") is not None:
                    new_service.title = item.get("title")
                if item.get("start_date") is not None:
                    new_service.start_date = item.get("start_date")
                if item.get("type") is not None and isinstance(item.get("type"), dict):
                    if item["type"].get("lookup_value_name") is not None:
                        new_service.type = item["type"].get("lookup_value_name")
                if item.get("end_date") is not None:
                    new_service.end_date = item.get("end_date")
                if item.get("closed_by") is not None and isinstance(
                    item.get("closed_by"), dict
                ):
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
                if item.get("dynamic_process") is not None and isinstance(
                    item.get("dynamic_process"), dict
                ):
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
                if item.get("decision") is not None and isinstance(
                    item.get("decision"), dict
                ):
                    if item["decision"].get("lookup_value_name") is not None:
                        new_service.decision = item["decision"].get("lookup_value_name")
                if item.get("funding_code") is not None:
                    new_service.funding_code = item.get("funding_code")
                if item.get("external_id") is not None:
                    new_service.external_id = item.get("external_id")
                if item.get("uscis_receipt_number") is not None:
                    new_service.uscis_receipt_number = item.get("uscis_receipt_number")

                standard_key_list = standard_services_keys()
                custom_fields = {
                    key: value
                    for key, value in item.items()
                    if key not in standard_key_list
                }
                if custom_fields is not None:
                    new_service.custom_fields = custom_fields
                else:
                    new_service.custom_fields = {}
                del custom_fields
                new_service.complete = True
        log(f"Services Populated for a case.")

    services_list.gathered = True
    return services_list


def populate_task_data(
    *,
    legalserver_task: DAObject,
    task_data: dict,
) -> DAObject:
    """Take the data from LegalServer about a given task and populate a given
    DAObject with the data.

    Args:
        legalserver_task (DAObject):  DAObject to be returned.
        task_data (dict): Dictionary of the task data from a
            LegalServer request.

    Returns:
        A DAObject of a task record."""

    legalserver_task.uuid = task_data.get("task_uuid")
    if task_data.get("id") is not None:
        legalserver_task.id = task_data.get("id")
    if task_data.get("title") is not None:
        legalserver_task.title = task_data.get("title")
    if task_data.get("list_date") is not None:
        legalserver_task.list_date = task_data.get("list_date")
    if task_data.get("due_date") is not None:
        legalserver_task.due_date = task_data.get("due_date")
    if task_data.get("active") is not None:
        legalserver_task.active = task_data.get("active")
    if task_data.get("task_type") is not None and isinstance(
        task_data["task_type"], dict
    ):
        if task_data["task_type"].get("lookup_value_name") is not None:
            legalserver_task.task_type = task_data["task_type"].get("lookup_value_name")
    if task_data.get("deadline_type") is not None and isinstance(
        task_data["deadline_type"], dict
    ):
        if task_data["deadline_type"].get("lookup_value_name") is not None:
            legalserver_task.deadline_type = task_data["deadline_type"].get(
                "lookup_value_name"
            )
    if task_data.get("deadline") is not None:
        legalserver_task.deadline = task_data.get("deadline")
    if task_data.get("private") is not None:
        legalserver_task.private = task_data.get("private")
    if task_data.get("completed") is not None:
        legalserver_task.completed = task_data.get("completed")
    if task_data.get("completed_by") is not None and isinstance(
        task_data["completed_by"], dict
    ):
        if task_data["completed_by"].get("user_uuid") is not None:
            legalserver_task.completed_by_uuid = task_data["completed_by"].get(
                "user_uuid"
            )
        if task_data["completed_by"].get("user_name") is not None:
            legalserver_task.completed_by_name = task_data["completed_by"].get(
                "user_name"
            )
    if task_data.get("completed_date") is not None:
        legalserver_task.completed_date = task_data.get("completed_date")

    if task_data.get("users") is not None and isinstance(task_data["users"], list):
        temp_list = []
        for user in task_data["users"]:
            if user.get("user_uuid") is not None:
                temp_list.append(
                    {
                        "user_uuid": user.get("user_uuid"),
                        "user_name": user.get("user_name"),
                    }
                )
        if temp_list:
            legalserver_task.users = temp_list
        del temp_list

    if task_data.get("dynamic_process") is not None and isinstance(
        task_data.get("dynamic_process"), dict
    ):
        if task_data["dynamic_process"].get("dynamic_process_id") is not None:
            legalserver_task.dynamic_process_id = task_data["dynamic_process"].get(
                "dynamic_process_id"
            )
        if task_data["dynamic_process"].get("dynamic_process_uuid") is not None:
            legalserver_task.dynamic_process_uuid = task_data["dynamic_process"].get(
                "dynamic_process_uuid"
            )
        if task_data["dynamic_process"].get("dynamic_process_name") is not None:
            legalserver_task.dynamic_process_name = task_data["dynamic_process"].get(
                "dynamic_process_name"
            )
    if task_data.get("is_this_a_case_alert") is not None:
        legalserver_task.is_this_a_case_alert = task_data.get("is_this_a_case_alert")
    if task_data.get("statute_of_limitations") is not None:
        legalserver_task.statute_of_limitations = task_data.get(
            "statute_of_limitations"
        )
    if task_data.get("created_date") is not None:
        legalserver_task.created_date = task_data.get("created_date")
    if task_data.get("created_by") is not None and isinstance(
        task_data["created_by"], dict
    ):
        if task_data["created_by"].get("user_uuid") is not None:
            legalserver_task.created_by_uuid = task_data["created_by"].get("user_uuid")
        if task_data["created_by"].get("user_name") is not None:
            legalserver_task.created_by_name = task_data["created_by"].get("user_name")
    if task_data.get("program") is not None and isinstance(task_data["program"], dict):
        if task_data["program"].get("lookup_value_name") is not None:
            legalserver_task.program = task_data["program"].get("lookup_value_name")
    if task_data.get("office") is not None and isinstance(task_data["office"], dict):
        if task_data["office"].get("office_name") is not None:
            legalserver_task.office_name = task_data["office"].get("office_name")
        if task_data["office"].get("office_code") is not None:
            legalserver_task.office_code = task_data["office"].get("office_code")

    standard_key_list = standard_task_keys()
    custom_fields = {
        key: value for key, value in task_data.items() if key not in standard_key_list
    }
    if custom_fields is not None:
        legalserver_task.custom_fields = custom_fields
    else:
        legalserver_task.custom_fields = {}
    del custom_fields

    return legalserver_task


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
        A DAList of DAObjects with each being a separate task record."""

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
                new_task = populate_task_data(legalserver_task=new_task, task_data=item)
                new_task.complete = True

    task_list.gathered = True
    return task_list


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

    user.user_uuid = user_data.get("user_uuid")
    if user_data.get("id") is not None:
        user.id = user_data.get("id")
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
    if user_data.get("title") is not None:
        user.title = user_data.get("title")
    if user_data.get("suffix") is not None:
        user.suffix = user_data.get("suffix")
    if user_data.get("need_password_change_next_login") is not None:
        user.need_password_change_next_login = user_data.get(
            "need_password_change_next_login"
        )
    if user_data.get("types") is not None and isinstance(user_data.get("types"), list):
        temp_list = []
        for type in user_data["types"]:
            if type.get("lookup_value_name") is not None:
                temp_list.append(type.get("lookup_value_name"))
        if temp_list:
            user.types = temp_list
        del temp_list
    if user_data.get("role") is not None and isinstance(user_data["role"], dict):
        if user_data["role"].get("lookup_value_name") is not None:
            user.role = user_data["role"].get("lookup_value_name")
    if user_data.get("gender") is not None and isinstance(user_data["gender"], dict):
        if user_data["gender"].get("lookup_value_name") is not None:
            user.gender = user_data["gender"].get("lookup_value_name")
    if user_data.get("race") is not None and isinstance(user_data.get("race"), dict):
        if user_data["race"].get("lookup_value_name") is not None:
            user.race = user_data["race"].get("lookup_value_name")
    if user_data.get("dob") is not None:
        user.birthdate = user_data.get("dob")
    if user_data.get("office") is not None and isinstance(
        user_data.get("office"), dict
    ):
        if user_data["office"].get("office_name") is not None:
            user.office = user_data.get("office")
    if user_data.get("program") is not None and isinstance(user_data["program"], dict):
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
    if user_data.get("additional_programs") is not None and isinstance(
        user_data["additional_programs"], list
    ):
        temp_list = []
        for program in user_data["additional_programs"]:
            if program.get("lookup_value_name") is not None:
                temp_list.append(program.get("lookup_value_name"))
        if temp_list:
            user.additional_programs = temp_list
        del temp_list

    if user_data.get("additional_offices") is not None:
        if isinstance(user_data["additional_offices"], list):
            temp_list = []
            for office in user_data["additional_offices"]:
                if office.get("office_name") is not None:
                    temp_list.append(office.get("office_name"))
            if temp_list:
                user.additional_offices = temp_list
            del temp_list
        else:
            user.additional_offices = user_data.get("additional_offices")

    if user_data.get("external_guid") is not None:
        user.external_guid = user_data.get("external_guid")

    if user_data.get("highest_court_admitted") is not None:
        user.highest_court_admitted = user_data.get("highest_court_admitted")
    if user_data.get("languages") is not None and isinstance(
        user_data["languages"], list
    ):
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
    if user_data.get("preferred_phone") is not None:
        if user_data["preferred_phone"].get("lookup_value_name") is not None:
            user.preferred_phone = user_data["preferred_phone"].get("lookup_value_name")
    if user_data.get("practice_state") is not None:
        user.practice_state = user_data.get("practice_state")
    if user_data.get("member_good_standing") is not None and isinstance(
        user_data["member_good_standing"], dict
    ):
        if user_data["member_good_standing"].get("lookup_value_name") is not None:
            user.member_good_standing = user_data["member_good_standing"].get(
                "lookup_value_name"
            )
    if user_data.get("recruitment") is not None and isinstance(
        user_data["recruitment"], dict
    ):
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

    if user_data.get("counties") is not None and isinstance(
        user_data["counties"], list
    ):
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

    if user_data.get("address_mailing") is not None:
        user.address_mailing = user_data.get("address_mailing")

    if user_data.get("contractor_assignment_types") is not None and isinstance(
        user_data["contractor_assignment_types"], list
    ):
        temp_list = []
        for type in user_data["contractor_assignment_types"]:
            if type.get("lookup_value_name") is not None:
                temp_list.append(type.get("lookup_value_name"))
        if temp_list:
            user.contractor_assignment_types = temp_list
        del temp_list

    if user_data.get("organization_affiliations") is not None and isinstance(
        user_data["organization_affiliations"], list
    ):
        temp_list = []
        for affiliation in user_data["organization_affiliations"]:
            temp_list.append(affiliation)
        if temp_list:
            user.organization_affiliations = temp_list
        del temp_list

    # Work Address
    if user_data.get("address_work") is not None and isinstance(
        user_data["address_work"], dict
    ):
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
    if user_data.get("address_home") is not None and isinstance(
        user_data["address_home"], dict
    ):
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

    # Mailing Address

    if user_data.get("address_mailing") is not None and isinstance(
        user_data["address_mailing"], dict
    ):
        if (
            user_data["address_mailing"].get("street") is not None
            or user_data["address_mailing"].get("apt_num") is not None
            or user_data["address_mailing"].get("street_2") is not None
            or user_data["address_mailing"].get("city") is not None
            or user_data["address_mailing"].get("state") is not None
            or user_data["address_mailing"].get("zip") is not None
        ):
            user.initializeAttribute("mailing_address", Address)

        if user_data["address_mailing"].get("street") is not None:
            user.mailing_address.address = user_data["address_mailing"].get("street")
        ## LS Supports both Apt Num and Street2
        if (
            user_data["address_mailing"].get("street_2") is not None
            and user_data["address_mailing"].get("apt_num") is None
        ):
            user.mailing_address.unit = user_data["address_mailing"].get("street_2")
        if (
            user_data["address_mailing"].get("apt_num") is not None
            and user_data["address_mailing"].get("street_2") is None
        ):
            user.mailing_address.unit = user_data["address_mailing"].get("apt_num")
        if (
            user_data["address_mailing"].get("apt_num") is not None
            and user_data["address_mailing"].get("street_2") is not None
        ):
            user.mailing_address.unit = user_data["address_mailing"].get("apt_num")
            if user.mailing_address.address is None:
                user.mailing_address.address = user_data["address_mailing"].get(
                    "street_2"
                )
            else:
                user.mailing_address.address = f'{user.mailing_address.address}, {user_data["address_home"].get("street_2")}'
        if user_data["address_mailing"].get("city") is not None:
            user.mailing_address.city = user_data["address_mailing"].get("city")
        if user_data["address_mailing"].get("state") is not None:
            user.mailing_address.state = user_data["address_mailing"].get("state")
        if user_data["address_mailing"].get("zip") is not None:
            user.mailing_address.zip = user_data["address_mailing"].get("zip")

    if user_data.get("dynamic_process") is not None and isinstance(
        user_data["dynamic_process"], dict
    ):
        user.dynamic_process_id = user_data["dynamic_process"].get("dynamic_process_id")
        user.dynamic_process_uuid = user_data["dynamic_process"].get(
            "dynamic_process_uuid"
        )
        user.dynamic_process_name = user_data["dynamic_process"].get(
            "dynamic_process_name"
        )

    if user_data.get("vendor_id") is not None:
        user.vendor_id = user_data.get("vendor_id")
    if user_data.get("adp_number") is not None:
        user.adp_number = user_data.get("adp_number")
    if user_data.get("snum") is not None:
        user.snum = user_data.get("snum")
    if user_data.get("contractor_doing_business_as") is not None:
        user.contractor_doing_business_as = user_data.get(
            "contractor_doing_business_as"
        )
    if user_data.get("contact_uuid") is not None:
        user.contact_uuid = user_data.get("contact_uuid")

    if user_data.get("supervisors") is not None and isinstance(
        user_data["supervisors"], list
    ):
        temp_list = []
        for supervisor in user_data["supervisors"]:
            temp_object = {}
            if supervisor.get("supervisor_type") is not None and isinstance(
                supervisor.get("supervisor_type"), dict
            ):
                if supervisor["supervisor_type"].get("lookup_value_name") is not None:
                    temp_object["supervisor_type"] = supervisor["supervisor_type"].get(
                        "lookup_value_name"
                    )
                else:
                    temp_object["supervisor_type"] = "Supervisor"
            temp_object["supervisor_uuid"] = supervisor.get("uuid")
            if supervisor.get("supervisor") is not None and isinstance(
                supervisor.get("supervisor"), dict
            ):
                if supervisor["supervisor"].get("user_uuid") is not None:
                    temp_object["user_uuid"] = supervisor["supervisor"].get("user_uuid")
                if supervisor["supervisor"].get("user_name") is not None:
                    temp_object["user_name"] = supervisor["supervisor"].get("user_name")
            temp_list.append(temp_object)
        if temp_list:
            user.supervisors = temp_list
        del temp_list

    if user_data.get("supervisees") is not None and isinstance(
        user_data["supervisees"], list
    ):
        temp_list = []
        for supervisee in user_data["supervisees"]:
            temp_object = {}
            if supervisee.get("supervisor_type") is not None and isinstance(
                supervisee.get("supervisor_type"), dict
            ):
                if supervisee["supervisor_type"].get("lookup_value_name") is not None:
                    temp_object["supervisor_type"] = supervisee["supervisor_type"].get(
                        "lookup_value_name"
                    )
                else:
                    temp_object["supervisor_type"] = "Supervisor"
            temp_object["supervisee_record_uuid"] = supervisee.get("uuid")
            temp_object["supervisor_record_uuid"] = supervisee.get("supervisor_uuid")
            if supervisee.get("supervisee") is not None and isinstance(
                supervisee.get("supervisor"), dict
            ):
                if supervisee["supervisee"].get("user_uuid") is not None:
                    temp_object["user_uuid"] = supervisee["supervisee"].get("user_uuid")
                if supervisee["supervisee"].get("user_name") is not None:
                    temp_object["user_name"] = supervisee["supervisee"].get("user_name")
            temp_list.append(temp_object)
        if temp_list:
            user.supervisees = temp_list
        del temp_list

    standard_key_list = standard_user_keys()
    custom_fields = {
        key: value for key, value in user_data.items() if key not in standard_key_list
    }
    if custom_fields is not None:
        user.custom_fields = custom_fields
    else:
        user.custom_fields = {}
    del custom_fields

    return user


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


def search_contact_data(
    *,
    legalserver_site: str,
    contact_search_params: dict | None = None,
    custom_fields=[],
    sort: str | None = None,
    page_limit: int | None = None,
    custom_results=[],
) -> List[Dict]:
    """Search Contacts in LegalServer for a set of search parameters.

    This uses LegalServer's Search Contacts API to get back details of any
    contact records that match a set of parameters.

    Args:
        legalserver_site (str): The specific LegalServer site to
            check for the organization on.
        contact_search_params (dict): The specific parameters to search for when
            looking at contacts.
        custom_fields (list): An optional list of custom fields to include.
        sort (str): Optional string to sort the results by. Defaults to ASC.
        page_limit (int): Optional integer to limit the number of results returned.
        custom_results (list): An optional list of fields to return.

    Returns:
        A list of dictionaries for the matching contacts.

    Raises:
        Errors are handled in the response. Errors will be present when the
        dictionary response includes a key of 'error'
    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/contacts"
    if not contact_search_params:
        contact_search_params = {}
    if custom_fields:
        if has_valid_items(custom_fields):
            contact_search_params["custom_fields"] = format_field_list(custom_fields)

    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="contacts"):
            contact_search_params["custom_results"] = custom_results

    if sort == "asc":
        contact_search_params["sort"] = "asc"
    elif sort == "desc":
        contact_search_params["sort"] = "desc"

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="contact",
        params=contact_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
        page_limit=page_limit,
    )

    return return_data


def search_document_data(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str | None = None,
    document_search_params: dict | None = None,
    sort: str | None = None,
    page_limit: int | None = None,
    custom_results: List[str] = [],
) -> List[Dict]:
    """Search document data in LegalServer for a specific matter.

    This uses LegalServer's Search Documents API to get back details of any
    documents that match a given set of parameters. Typically, this will be
    limited to a single case using the matter's UUID, but it does not have to
    be limited.

    Args:
        legalserver_site (str): The specific LegalServer site to
            check for the organization on.
        legalserver_matter_uuid (dict): The UUID of the specific LegalServer
            organization to retrieve
        document_search_params (dict): A dictionary of search parameters to filter
            for in the request.
        sort (str): Optional string to sort the results by. Defaults to ASC.
        page_limit (int): Optional integer to limit the number of results returned.
        custom_results (list): An optional list of fields to return.

    Returns:
        A list of dictionaries of matching documents.
    """

    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/documents"
    if not document_search_params:
        document_search_params = {}
    if legalserver_matter_uuid:
        document_search_params["matters"] = legalserver_matter_uuid
    if sort == "asc":
        document_search_params["sort"] = "asc"
    elif sort == "desc":
        document_search_params["sort"] = "desc"

    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="documents"):
            document_search_params["custom_results"] = custom_results

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="documents",
        params=document_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
        page_limit=page_limit,
    )

    return return_data


def search_event_data(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str | None = None,
    event_search_params: dict | None = None,
    custom_fields=[],
    sort: str | None = None,
    page_limit: int | None = None,
    custom_results: List[str] = [],
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
        sort (str): Optional string to sort the results by. Defaults to ASC.
        page_limit (int): Optional integer to limit the number of results returned.
        custom_results (list): An optional list of fields to return.

    Returns:
        A list of dictionaries of matching events.

    Raises:
        Errors are handled in the response. Errors will be present when the
        dictionary response includes a key of 'error'
    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/events"
    if not event_search_params:
        event_search_params = {}
    if legalserver_matter_uuid:
        event_search_params["matters"] = legalserver_matter_uuid
    if custom_fields:
        if has_valid_items(custom_fields):
            event_search_params["custom_fields"] = format_field_list(custom_fields)

    if sort == "asc":
        event_search_params["sort"] = "asc"
    elif sort == "desc":
        event_search_params["sort"] = "desc"

    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="events"):
            event_search_params["custom_results"] = custom_results

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="events",
        params=event_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
        page_limit=page_limit,
    )

    return return_data


def search_matter_additional_names(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    matter_additional_names_search_params: dict | None = None,
    sort: str | None = None,
    page_limit: int | None = None,
    custom_results: List[str] = [],
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
        sort (str): Optional string to sort the results by. Defaults to ASC.
        page_limit (int): Optional integer to limit the number of results returned.
        custom_results (list): An optional list of fields to return.

    Returns:
        A list of dictionaries with the additional names data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/additional_names"

    if not matter_additional_names_search_params:
        matter_additional_names_search_params = {}
    if sort == "asc":
        matter_additional_names_search_params["sort"] = "asc"
    elif sort == "desc":
        matter_additional_names_search_params["sort"] = "desc"

    if custom_results:
        if check_for_valid_fields(
            source_list=custom_results, module="additional_names"
        ):
            matter_additional_names_search_params["custom_results"] = custom_results

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="additional_names",
        params=matter_additional_names_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
        page_limit=page_limit,
    )

    return return_data


def search_matter_adverse_parties(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    matter_adverse_parties_search_params: dict | None = None,
    sort: str | None = None,
    page_limit: int | None = None,
    custom_results: List[str] = [],
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
        sort (str): Optional string to sort the results by. Defaults to ASC.
        page_limit (int): Optional integer to limit the number of results returned.
        custom_results (list): An optional list of fields to return.

    Returns:
        A list of dictionaries with the Adverse Parties data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/adverse_parties"

    if not matter_adverse_parties_search_params:
        matter_adverse_parties_search_params = {}
    if sort == "asc":
        matter_adverse_parties_search_params["sort"] = "asc"
    elif sort == "desc":
        matter_adverse_parties_search_params["sort"] = "desc"

    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="adverse_parties"):
            matter_adverse_parties_search_params["custom_results"] = custom_results

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="adverse_parties",
        params=matter_adverse_parties_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
        page_limit=page_limit,
    )

    return return_data


def search_matter_assignments_data(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    matter_assignment_search_params: dict | None = None,
    sort: str | None = None,
    page_limit: int | None = None,
    custom_results: List[str] = [],
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
        sort (str): Optional string to sort the results by. Defaults to ASC.
        page_limit (int): Optional integer to limit the number of results returned.
        custom_results (list): An optional list of fields to return.

    Returns:
        A list of dictionaries with the assignment data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/assignments"

    if not matter_assignment_search_params:
        matter_assignment_search_params = {}
    if sort == "asc":
        matter_assignment_search_params["sort"] = "asc"
    elif sort == "desc":
        matter_assignment_search_params["sort"] = "desc"

    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="assignments"):
            matter_assignment_search_params["custom_results"] = custom_results

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="assignments",
        params=matter_assignment_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
        page_limit=page_limit,
    )

    return return_data


def search_matter_charges_data(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    charges_search_params: dict | None = None,
    custom_fields: list | None = None,
    sort: str | None = None,
    page_limit: int | None = None,
    custom_results: List[str] = [],
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
        sort (str): Optional string to sort the results by. Defaults to ASC.
        page_limit (int): Optional integer to limit the number of results returned.
        custom_results (list): An optional list of fields to return.

    Returns:
        A list of dictionaries with the charges data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/charges"
    if not charges_search_params:
        charges_search_params = {}
    if custom_fields:
        if has_valid_items(custom_fields):
            charges_search_params["custom_fields"] = format_field_list(custom_fields)

    if sort == "asc":
        charges_search_params["sort"] = "asc"
    elif sort == "desc":
        charges_search_params["sort"] = "desc"

    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="charges"):
            charges_search_params["custom_results"] = custom_results

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="charges",
        params=charges_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
        page_limit=page_limit,
    )

    return return_data


def search_matter_contacts_data(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    matter_contact_search_params: dict | None = None,
    sort: str | None = None,
    page_limit: int | None = None,
    custom_results: List[str] = [],
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
        sort (str): Optional string to sort the results by. Defaults to ASC.
        page_limit (int): Optional integer to limit the number of results returned.
        custom_results (list): An optional list of fields to return.

    Returns:
        A list of dictionaries with the contacts data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/contacts"
    if not matter_contact_search_params:
        matter_contact_search_params = {}
    if sort == "asc":
        matter_contact_search_params["sort"] = "asc"
    elif sort == "desc":
        matter_contact_search_params["sort"] = "desc"

    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="matter_contacts"):
            matter_contact_search_params["custom_results"] = custom_results

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="matter_contact",
        params=matter_contact_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
        page_limit=page_limit,
    )

    return return_data  # type: ignore


def search_matter_income_data(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    income_type: str = "",
    search_income_params: dict | None = None,
    sort: str | None = None,
    page_limit: int | None = None,
    custom_results: List[str] = [],
) -> List[Dict]:
    """Search Income on a given Matter within LegalServer.

    This is a keyword defined function that gets back all of the income on a case.
    The income can be filtered in the API call based on the income_type. This uses the
    Search Matter Income
    API endpoint. They are returned as a list of income.

    Args:
        legalserver_site (str): required
        legalserver_matter_uuid (str): required
        income_type (str): Optional string to filter on Income Type
        search_income_params (dict): Optional dictionary of search parameters
        sort (str): Optional string to sort the results by. Defaults to ASC.
        page_limit (int): Optional integer to limit the number of results returned.
        custom_results (list): An optional list of fields to return.

    Returns:
        A list of dictionaries with the income data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/incomes"

    if not search_income_params:
        search_income_params = {}
    if income_type:
        search_income_params["type"] = income_type
    if sort == "asc":
        search_income_params["sort"] = "asc"
    elif sort == "desc":
        search_income_params["sort"] = "desc"

    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="incomes"):
            search_income_params["custom_results"] = custom_results

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="incomes",
        params=search_income_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
        page_limit=page_limit,
    )

    return return_data


def search_matter_litigation_data(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    litigation_search_params: dict | None = None,
    custom_fields: list | None = None,
    sort: str | None = None,
    page_limit: int | None = None,
    custom_results: List[str] = [],
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
        sort (str): Optional string to sort the results by. Defaults to ASC.
        page_limit (int): Optional integer to limit the number of results returned.
        custom_results (list): An optional list of fields to return.

    Returns:
        A list of dictionaries with the litigation data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/litigations"

    if not litigation_search_params:
        litigation_search_params = {}
    if custom_fields:
        if has_valid_items(custom_fields):
            litigation_search_params["custom_fields"] = format_field_list(custom_fields)

    if sort == "asc":
        litigation_search_params["sort"] = "asc"
    elif sort == "desc":
        litigation_search_params["sort"] = "desc"

    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="litigations"):
            litigation_search_params["custom_results"] = custom_results

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="litigation",
        params=litigation_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
        page_limit=page_limit,
    )

    return return_data


def search_matter_notes_data(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    note_type: str = "",
    search_note_params: dict | None = None,
    sort: str | None = None,
    page_limit: int | None = None,
    custom_results: List[str] = [],
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
        sort (str): Optional string to sort the results by. Defaults to ASC.
        page_limit (int): Optional integer to limit the number of results returned.
        custom_results (list): An optional list of fields to return.

    Returns:
        A list of dictionaries with the notes data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/notes"

    if not search_note_params:
        search_note_params = {}
    if note_type:
        search_note_params["note_type"] = note_type
    if sort == "asc":
        search_note_params["sort"] = "asc"
    elif sort == "desc":
        search_note_params["sort"] = "desc"

    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="notes"):
            search_note_params["custom_results"] = custom_results

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="notes",
        params=search_note_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
        page_limit=page_limit,
    )

    return return_data


def search_matter_non_adverse_parties(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    matter_non_adverse_parties_search_params: dict | None = None,
    sort: str | None = None,
    page_limit: int | None = None,
    custom_results: List[str] = [],
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
        sort (str): Optional string to sort the results by. Defaults to ASC.
        page_limit (int): Optional integer to limit the number of results returned.
        custom_results (list): An optional list of fields to return.

    Returns:
        A list of dictionaries with the Adverse Parties data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/non_adverse_parties"

    if not matter_non_adverse_parties_search_params:
        matter_non_adverse_parties_search_params = {}
    if sort == "asc":
        matter_non_adverse_parties_search_params["sort"] = "asc"
    elif sort == "desc":
        matter_non_adverse_parties_search_params["sort"] = "desc"

    if custom_results:
        if check_for_valid_fields(
            source_list=custom_results, module="non_adverse_parties"
        ):
            matter_non_adverse_parties_search_params["custom_results"] = custom_results

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="adverse_parties",
        params=matter_non_adverse_parties_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
        page_limit=page_limit,
    )

    return return_data


def search_matter_services_data(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str,
    services_search_params: dict | None = None,
    custom_fields: list | None = None,
    sort: str | None = None,
    page_limit: int | None = None,
    custom_results: List[str] = [],
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
        sort (str): Optional string to sort the results by. Defaults to ASC.
        page_limit (int): Optional integer to limit the number of results returned.
        custom_results (list): An optional list of fields to return.

    Returns:
        A list of dictionaries with the services data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/matters/{legalserver_matter_uuid}/services"
    if not services_search_params:
        services_search_params = {}
    if custom_fields:
        if has_valid_items(custom_fields):
            services_search_params["custom_fields"] = format_field_list(custom_fields)

    if sort == "asc":
        services_search_params["sort"] = "asc"
    elif sort == "desc":
        services_search_params["sort"] = "desc"

    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="services"):
            services_search_params["custom_results"] = custom_results

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="services",
        params=services_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
        page_limit=page_limit,
    )

    return return_data  # type: ignore


def search_task_data(
    *,
    legalserver_site: str,
    legalserver_matter_uuid: str | None = None,
    task_search_params: dict | None = None,
    custom_fields=[],
    sort: str | None = None,
    page_limit: int | None = None,
    custom_results: List[str] = [],
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
        sort (str): Optional string to sort the results by. Defaults to ASC.
        page_limit (int): Optional integer to limit the number of results returned.
        custom_results (list): An optional list of fields to return.

    Returns:
        A list of dictionaries of matching tasks.

    Raises:
        Errors are handled in the response. Errors will be present when the
        dictionary response includes a key of 'error'
    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/tasks"
    if not task_search_params:
        task_search_params = {}
    if legalserver_matter_uuid:
        task_search_params["matters"] = legalserver_matter_uuid
    if custom_fields:
        if has_valid_items(custom_fields):
            task_search_params["custom_fields"] = format_field_list(custom_fields)

    if sort == "asc":
        task_search_params["sort"] = "asc"
    elif sort == "desc":
        task_search_params["sort"] = "desc"

    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="tasks"):
            task_search_params["custom_results"] = custom_results

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="tasks",
        params=task_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
        page_limit=page_limit,
    )

    return return_data


def search_user_data(
    *,
    legalserver_site: str,
    user_search_params: dict | None = None,
    custom_fields: list | None = None,
    sort: str | None = None,
    page_limit: int | None = None,
    custom_results: List[str] = [],
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
        sort (str): Optional string to sort the results by. Defaults to ASC.
        page_limit (int): Optional integer to limit the number of results returned.
        custom_results (list): An optional list of fields to return.

    Returns:
        A list of dictionaries for the identified users.

    Raises:
        Errors are handled in the response. Errors will be present when the
        dictionary response includes a key of 'error'
    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/users"
    if not user_search_params:
        user_search_params = {}
    if custom_fields:
        if has_valid_items(custom_fields):
            user_search_params["custom_fields"] = format_field_list(custom_fields)

    if sort == "asc":
        user_search_params["sort"] = "asc"
    elif sort == "desc":
        user_search_params["sort"] = "desc"

    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="users"):
            user_search_params["custom_results"] = custom_results

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="user",
        params=user_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
        page_limit=page_limit,
    )

    return return_data


def search_organization_data(
    *,
    legalserver_site: str,
    organization_search_params: dict | None = None,
    custom_fields: list | None = None,
    sort: str | None = None,
    page_limit: int | None = None,
    custom_results: List[str] = [],
) -> List[Dict]:
    """
    Search Organizations within LegalServer for a given set of parameters and custom fields.

    This uses LegalServer's Search Organizations API to get back a list of Organizations.

    Args:
        legalserver_site (str):
        organization_search_params (dict):
        custom_fields (list):
        sort (str): Optional string to sort the results by. Defaults to ASC.
        page_limit (int): Optional integer to limit the number of results returned.
        custom_results (list): An optional list of fields to return.

    Returns:
        List of dictionaries

    Raises:
        Errors are handled in the response. Errors will be present when the dictionary response includes a key of 'error'

    """
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"
    if not organization_search_params:
        organization_search_params = {}
    url = f"https://{legalserver_site}.legalserver.org/api/v2/organizations"
    if custom_fields:
        if has_valid_items(custom_fields):
            organization_search_params["custom_fields"] = format_field_list(
                custom_fields
            )

    if sort == "asc":
        organization_search_params["sort"] = "asc"
    elif sort == "desc":
        organization_search_params["sort"] = "desc"

    if custom_results:
        if check_for_valid_fields(source_list=custom_results, module="organizations"):
            organization_search_params["custom_results"] = custom_results

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="organizations",
        params=organization_search_params,
        legalserver_site=legalserver_site,
        header_content=header_content,
        page_limit=page_limit,
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
        A list of dictionaries with the user Organization Affiliation data."""
    header_content = get_legalserver_token(legalserver_site=legalserver_site)
    header_content["Accept"] = "application/json"

    url = f"https://{legalserver_site}.legalserver.org/api/v2/users/{legalserver_user_uuid}/organization_affiliation"

    return_data = loop_through_legalserver_responses(
        url=url,
        source_type="organization_affiliation",
        params={},
        legalserver_site=legalserver_site,
        header_content=header_content,
    )

    return return_data


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
        "city",
        "county",
        "gender",
        "ssn",
        "state",
        "street_address",
        "street_address_2",
        "zip_code",
    ]

    return standard_adverse_party_keys


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
        "external_id",
        "charge_name",
    ]
    return standard_charges_keys


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
        "safe_address",
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
        "contact_uuid",
        "case_contact_uuid",
        "contact_types",
        "case_contact_type",
    ]
    return standard_contact_keys


def standard_document_keys() -> List[str]:
    """Return the list of keys present in a Document response from LegalServer to
    better identify the custom fields.

    Args:
        None.

    Returns:
        A list of strings.
    """
    standard_document_keys = [
        "id",
        "uuid",
        "name",
        "title",
        "mime_type",
        "virus_free",
        "date_create",
        "download_url",
        "virus_scanned",
        "disk_file_size",
        "storage_backend",
        "type",
        "programs",
        "folder",
        "funding_code",
        "hyperlink",
        "shared_with_sj_client",
    ]
    return standard_document_keys


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
        "external_id",
    ]
    return standard_event_keys


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
        "external_id",
    ]
    return standard_litigation_keys


def standard_matter_keys() -> List[str]:
    """Return the list of keys present in a Matter response from LegalServer to
    better identify the custom fields.

    Args:
        None.

    Returns:
        A list of strings.
    """
    standard_matter_keys = [
        "a_number",
        "additional_assistance",
        "additional_names",
        "adverse_parties",
        "adverse_party_conflict_status",
        "api_integration_preference",
        "ap_conflict_waived",
        "asset_assistance",
        "asset_eligible",
        "assignments",
        "associated_cases",
        "birth_city",
        "birth_country",
        "case_disposition",
        "case_email_address",
        "case_exclusions",
        "case_id",
        "case_number",
        "case_profile_url",
        "case_restrictions",
        "case_status",
        "case_title",
        "case_type",
        "cause_number",
        "charges",
        "citizenship",
        "citizenship_country",
        "client_address_home",
        "client_address_mailing",
        "client_approved_transfer",
        "client_conflict_status",
        "client_email_address",
        "client_full_name",
        "client_gender",
        "client_id",
        "close_reason",
        "conflict_status_note",
        "conflict_status_note_ap",
        "conflict_waived",
        "contacts",
        "contractor_work_orders",
        "country_of_origin",
        "county_of_dispute",
        "county_of_residence",
        "court_tracking_numbers",
        "created_by_integration_or_api",
        "current_living_situation",
        "date_closed",
        "date_of_appointment_retention",
        "date_of_birth",
        "date_opened",
        "date_rejected",
        "days_open",
        "disabled",
        "dob_status",
        "documents",
        "drivers_license",
        "dropbox_folder_id",
        "dynamic_process",
        "employment_status",
        "ethnicity",
        "events",
        "exclude_from_search_results",
        "external_id",
        "fax_phone",
        "fax_phone_note",
        "fee_generating",
        "first",
        "google_drive_folder_id",
        "highest_education",
        "home_phone",
        "home_phone_note",
        "how_referred",
        "hud_ami_category",
        "hud_area_median_income_percentage",
        "hud_entity_poverty_band",
        "hud_statewide_median_income_percentage",
        "hud_statewide_poverty_band",
        "impact",
        "immigration_status",
        "income_change_significantly",
        "income_change_type",
        "income_eligible",
        "incomes",
        "institutionalized",
        "institutionalized_at",
        "intake_date",
        "intake_office",
        "intake_program",
        "intake_type",
        "intake_user",
        "interpreter",
        "is_group",
        "is_lead_case",
        "is_this_a_prescreen",
        "language",
        "languages",
        "last",
        "lead_case",
        "legal_problem_category",
        "legal_problem_code",
        "level_of_expertise",
        "litigations",
        "lsc_eligible",
        "marital_status",
        "matter_uuid",
        "middle",
        "military_service",
        "military_status",
        "mobile_phone",
        "mobile_phone_note",
        "modified_by_integration_or_api",
        "non_adverse_parties",
        "notes",
        "number_of_adults",
        "number_of_children",
        "online_intake_payload",
        "organization_name",
        "other_phone",
        "other_phone_note",
        "pai_case",
        "percentage_of_poverty",
        "preferred_phone_number",
        "preferred_spoken_language",
        "preferred_written_language",
        "prescreen_date",
        "prescreen_office",
        "prescreen_program",
        "prescreen_screening_status",
        "prescreen_user",
        "priorities",
        "prior_client",
        "pro_bono_appropriate_volunteer",
        "pro_bono_engagement_type",
        "pro_bono_expiration_date",
        "pro_bono_interest_cc",
        "pro_bono_opportunity_available_date",
        "pro_bono_opportunity_cc",
        "pro_bono_opportunity_county",
        "pro_bono_opportunity_court_and_filing_fee_information",
        "pro_bono_opportunity_guardian_ad_litem_certification_needed",
        "pro_bono_opportunity_note",
        "pro_bono_opportunity_paupers_eligible",
        "pro_bono_opportunity_placement_date",
        "pro_bono_opportunity_special_issues",
        "pro_bono_opportunity_status",
        "pro_bono_opportunity_summary",
        "pro_bono_opportunity_summary_of_upcoming_dates",
        "pro_bono_opportunity_summary_of_work_needed",
        "pro_bono_skills_developed",
        "pro_bono_time_commitment",
        "pro_bono_urgent",
        "race",
        "referring_organizations",
        "rejected",
        "rejection_reason",
        "rural",
        "school_status",
        "second_language",
        "sending_site_identification_number",
        "services",
        "sharepoint_site_library",
        "sharepoint_tracer_document_id",
        "simplejustice_opportunity_community",
        "simplejustice_opportunity_helped_community",
        "simplejustice_opportunity_legal_topic",
        "simplejustice_opportunity_skill_type",
        "special_characteristics",
        "special_legal_problem_code",
        "ssi_eatra",
        "ssi_months_client_has_received_welfare_payments",
        "ssi_section8_housing_type",
        "ssi_welfare_case_num",
        "ssi_welfare_status",
        "ssn",
        "ssn_status",
        "suffix",
        "tasks",
        "transfer_reject_notes",
        "transfer_reject_reason",
        "trial_date",
        "veteran",
        "victim_of_domestic_violence",
        "visa_number",
        "work_phone",
        "work_phone_note",
        "prefix",
        "home_phone_safe",
        "mobile_phone_safe",
        "other_phone_safe",
        "work_phone_safe",
        "fax_phone_safe",
        "pronouns",
    ]
    return standard_matter_keys


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
        "documents",
        "zip",
    ]
    return standard_organization_keys


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
        "external_id",
        "uscis_receipt_number",
    ]
    return standard_services_keys


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
        "address_mailing",
        "adp_number",
        "contact_uuid",
        "documents",
        "dynamic_process_id",
        "need_password_change_next_login",
        "preferred_phone",
        "snum",
        "suffix",
        "title",
        "vendor_id",
        "contractor_doing_business_as",
        "organization_affiliations",
        "contractor_assignment_types",
        "supervisors",
        "supervisees",
    ]
    return standard_user_keys
