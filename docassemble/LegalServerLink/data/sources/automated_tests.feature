@load
Feature: Test LSAPIs

    Scenario: Testing Document Upload
        Given the maximum seconds for each Step is 200
        Given I log in with the email "PLAYGROUND_EMAIL" and the password "PLAYGROUND_PASSWORD"
        Given I start the interview at "testing_LSAPIs_post_file.yml"
        Then I tap to continue
        Then I should not see the phrase "*ERROR*"
        Then I should see the phrase "There are case notes from zip file uploads today."
        Then I should see the phrase "Legalserver file upload: {‘uuid’:"
        Then I should see the phrase "SharePoint file upload: {‘uuid’:"

    Scenario: Testing Get Matter Details with custom fields loads with no error
        Given the maximum seconds for each Step is 200
        Given I log in with the email "PLAYGROUND_EMAIL" and the password "PLAYGROUND_PASSWORD"
        Given I start the interview at "testing_LSAPIs_get_matter_details_custom.yml"
        Then I should see the phrase "‘matter_uuid’: ‘03f03192-4970-11ec-b6ad-0e5f2f9a47a5’"

    Scenario: Testing Populate Docassemble
        Given the maximum seconds for each Step is 200
        Given I log in with the email "PLAYGROUND_EMAIL" and the password "PLAYGROUND_PASSWORD"
        Given I start the interview at "testing_LSAPIs_populate_docassemble.yml"
        Given I set the variable "legalserver_matter_uuid" to "612f6ca6-3c9c-48df-8025-52e4ac1e020c"
        Given I set the variable "legalserver_site_abbreviation" to "Michael"
        Given I set the variable "legalserver_site_type" to "Test"
        Then I tap to continue
        Then I should not see the phrase "Error"
        Then I should not see the phrase "False"

    Scenario: Testing XML Report Loads
        Given the maximum seconds for each Step is 200
        Given I log in with the email "PLAYGROUND_EMAIL" and the password "PLAYGROUND_PASSWORD"
        Given I start the interview at "testing_LSAPIs_xml_report.yml"
        Then I should not see the phrase "{‘report’: ‘no data’}"
        Then I tap to continue
        Then I should not see the phrase "{‘report’: ‘no data’}"
        Then I tap to continue
        Then I should not see the phrase "{‘report’: ‘no data’}"
        Then I tap to continue

    Scenario: Testing JSON Report Loads
        Given the maximum seconds for each Step is 200
        Given I log in with the email "PLAYGROUND_EMAIL" and the password "PLAYGROUND_PASSWORD"
        Given I start the interview at "testing_LSAPIs_json_report.yml"
        Then I should not see the phrase "{‘report’: ‘no data’}"
        Then I tap to continue
        Then I should not see the phrase "{‘report’: ‘no data’}"
        Then I tap to continue
        Then I should not see the phrase "{‘report’: ‘no data’}"
        Then I tap to continue