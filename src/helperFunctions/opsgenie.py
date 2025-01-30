import requests
from config import settings
from typing import Dict, Tuple
from requests.exceptions import RequestException
import logging
import json
from pathlib import Path
from config import get_settings, Settings


logger = logging.getLogger(__name__)

settings = get_settings()


class OpsGenieError(Exception):
    pass


# version working with the api
# def get_team_responder(incident, options_file: str = "options.json") -> list:
#     """Get responder based on incident's suspected owning team"""
#     try:
#         with open(options_file) as f:
#             options = json.load(f)
#             teams = options.get('responders', {})

#             # Check if incident's suspected team exists in our teams
#             if incident.suspected_team in teams:
#                 return [{
#                     "type": "team",
#                     "name": incident.suspected_team
#                 }]
#             else:
#                 logger.warning(f"Team {incident.suspected_team} not found in options.json")
#                 return []
#     except FileNotFoundError:
#         logger.error(f"Options file {options_file} not found")
#         return []
#     except json.JSONDecodeError:
#         logger.error(f"Invalid JSON in {options_file}")
#         return []


MOCK_OPSGENIE_TEAMS = {"3rd Party": "ExampleSupport", "Algo Trading team": "Betting - Algo", "Broadcast Monitoring Team": "Streaming Technical Support", "Competition Manager": "Competition Management", "Customer Integrations": "CRISIS", "Digital Marketing": "REAP-media", "Operational DBA": "DBA", "Technical Services": "Internal Tools and Technical Services", "Feed Acquisition and Integrity": "Feeds Acquisition and Integrity", "FIBA Organizer": "Competition Management Developers", "Fixtures": "Fixtures", "Genius Sport Support": "Sport First Line Support", "Volleyball Competition Management": "Volleyball Sport Management", "IT Infrastructure": "IT Infrastructure", "Play by Play Aggregation": "Play by Play Aggregation", "Play by Play Collection": "Play by Play Collection 1", "Play by Play Statistics": "Play by Play Statistics", "Multibet": "Betting - Sportsbook Management 4", "NSCM - NCAA": "NCAA Support", "Odds Ingestion and Standardization": "Odds Ingestion and Standardization", "Operational Tools Fixtures": "Fixtures",
                       "Operational Tools Reporters": "Operational Tools Reporters", "Risk Management Control": "Betting - Sportsbook Management 4", "Risk Management Assessment": "Betting - Sportsbook Management 4", "RiskManagement": "Betting - Sportsbook Management 4", "Sportsbook 1": "Betting - Sportsbook Management 1", "Sportsbook 2": "Betting - Sportsbook Management 2", "Sportsbook 3": "Betting - Sportsbook Management 3", "Sportsbook 4": "Betting - Sportsbook Management 4", "Sportsbook Management Integrations": "Betting - Sportsbook Management Integrations SBMI", "Sportsbook Implementation Team": "Betting - Management", "Content Graph": "ContentGraph", "Sports Modelling API": "Betting - Sports Models", "SportzCast": "Sportzcast", "Sports Reporting Tools": "Play by Play Statistics", "Stats Engine": "Stats Engine", "Video Distribution - Genius Live": "Video Ingress and Distribution 1 and 2", "Sports Content": "SportsContent", "Volleyball On Court": "Volleyball on Court Applications", "Volleyball Competition Manager": "Volleyball Sport Management", "Other": "CRISIS"}


def get_team_responder(incident) -> list:
    """Get responder based on incident's suspected owning team using mock OpsGenie data."""
    if not incident.suspected_owning_team:
        logger.warning("No suspected owning team provided")
        return []

    if isinstance(incident.suspected_owning_team, str):
        team = incident.suspected_owning_team
    elif isinstance(incident.suspected_owning_team, list):
        if not incident.suspected_owning_team:
            return []
        team = incident.suspected_owning_team[0]
    else:
        logger.error(
            f"Unexpected type for suspected_owning_team: {type(incident.suspected_owning_team)}")
        return []

    if team in MOCK_OPSGENIE_TEAMS:
        return [{
            "type": "team",
            "name": MOCK_OPSGENIE_TEAMS[team]
        }]
    else:
        logger.warning(f"Team {team} not found in OpsGenie mock data")
        return []


async def create_alert(incident) -> Dict:
    url = "https://api.opsgenie.com/v2/alerts"
    headers = {
        "Authorization": f"GenieKey {settings.opsgenie_api_key}",
        "Content-Type": "application/json",
    }

    tags = ["SOS"]
    responders = get_team_responder(incident)

    payload = {
        "message": "Service Outage Alert",
        "description": (
            f"A new incident has been created regarding a service outage.\n\n"
            f"Description:\n"
            f"{incident.description}\n"
            f"For more details, you can check the Jira issue here: {settings.jira_server}/browse/{incident.jira_issue_key}"
        ),
        "priority": "P1",
        "tags": tags,
        "responders": responders
    }

    logger.info("Final Payload Being Sent to OpsGenie:")
    logger.info(json.dumps(payload, indent=2))

    try:
        logger.info(
            f"Creating OpsGenie alert for incident {incident.jira_issue_key}")
        response = requests.post(url, json=payload, headers=headers)

        # Log the complete response
        logger.info(f"OpsGenie Response Status Code: {response.status_code}")
        logger.info(f"OpsGenie Response Headers: {dict(response.headers)}")
        logger.info(f"OpsGenie Response Body: {response.text}")

        # Try to parse the response as JSON for more detailed error information
        try:
            response_data = response.json()
            logger.info(
                f"OpsGenie Response JSON: {json.dumps(response_data, indent=2)}")
        except json.JSONDecodeError:
            logger.warning("Could not parse OpsGenie response as JSON")

        # Check if the request was successful
        if response.status_code == 202:  # OpsGenie uses 202 for successful alert creation
            logger.info("Alert created successfully")
            return {
                "data": response.json() if response.text else {},
                "status_code": response.status_code,
                "message": "Alert created successfully"
            }
        else:
            error_message = f"OpsGenie returned status code {response.status_code}"
            logger.error(error_message)
            logger.error(f"Response content: {response.text}")
            raise OpsGenieError(error_message)

    except requests.exceptions.RequestException as e:
        error_message = "Failed to create OpsGenie alert"
        logger.error(error_message)

        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Error status code: {e.response.status_code}")
            logger.error(f"Error response body: {e.response.text}")
            try:
                error_json = e.response.json()
                logger.error(
                    f"Error response JSON: {json.dumps(error_json, indent=2)}")
            except json.JSONDecodeError:
                logger.error("Could not parse error response as JSON")

        raise OpsGenieError(f"{error_message}: {str(e)}") from e
    except Exception as e:
        error_message = f"Unexpected error creating OpsGenie alert: {str(e)}"
        logger.error(error_message)
        raise OpsGenieError(error_message) from e
