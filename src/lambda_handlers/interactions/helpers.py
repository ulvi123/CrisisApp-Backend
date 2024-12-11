import logging
from datetime import datetime
from typing import Dict, Any
from aws_lambda_powertools import Logger
from src.helperFunctions.jira import create_jira_ticket
from src.helperFunctions.slack_utils import (
    open_slack_response_modal, 
    create_slack_channel, 
    post_message_to_slack
)
from src.helperFunctions.status_page import create_statuspage_incident,update_statuspage_incident_status
from src.helperFunctions.opsgenie import create_alert
from src.helperFunctions.team_channel_mapping_to_slack import get_slack_channel_id_for_team
from src import schemas
from src import models
from config import get_settings,Settings
from sqlalchemy.orm import Session


logger = Logger()

settings = get_settings()


#functions to be used in the router
def extract_incident_data(state_values):
    required_fields = ["start_time", "start_time_picker", "end_time", "end_time_picker", "so_number", "affected_products", "suspected_owning_team", "severity"]
    
    for field in required_fields:
        if field not in state_values:
            logger.error(f"Missing {field} in state values")
            raise ValueError(f"Missing {field}")
    
    start_date = state_values.get("start_time", {}).get("start_date_action", {}).get("selected_date")
    start_time = state_values.get("start_time_picker", {}).get("start_time_picker_action", {}).get("selected_time")
    end_date = state_values.get("end_time", {}).get("end_date_action", {}).get("selected_date")
    end_time = state_values.get("end_time_picker", {}).get("end_time_picker_action", {}).get("selected_time")

    if not start_date or not start_time:
        raise ValueError("Missing start datetime")
    if not end_date or not end_time:
        raise ValueError("Missing end datetime")

    start_datetime_str = f"{start_date}T{start_time}:00"
    end_datetime_str = f"{end_date}T{end_time}:00"

    try:
        start_time_obj = datetime.strptime(start_datetime_str, "%Y-%m-%dT%H:%M:%S")
        end_time_obj = datetime.strptime(end_datetime_str, "%Y-%m-%dT%H:%M:%S")
    except ValueError as e:
        raise ValueError("Invalid datetime format") from e

    so_number = state_values.get("so_number", {}).get("so_number_action", {}).get("value")
    if not so_number:
        logger.error("Missing SO number")
        raise ValueError("Missing SO number")

    affected_products_options = state_values.get("affected_products", {}).get("affected_products_action", {}).get("selected_options", [])
    affected_products = [option["value"] for option in affected_products_options]

    suspected_owning_team_options = state_values.get("suspected_owning_team", {}).get("suspected_owning_team_action", {}).get("selected_options", [])
    suspected_owning_team = [option["value"] for option in suspected_owning_team_options]

    suspected_affected_components_options = state_values.get("suspected_affected_components", {}).get("suspected_affected_components_action", {}).get("selected_options", [])
    suspected_affected_components = [option["value"] for option in suspected_affected_components_options]

    severity_option = state_values.get("severity", {}).get("severity_action", {}).get("selected_option", {})
    severity = severity_option.get("value") if severity_option else None
    severity = [severity] if severity else []

    return {
        "so_number": so_number,
        "affected_products": affected_products,
        "severity": severity,
        "suspected_owning_team": suspected_owning_team,
        "start_time": start_time_obj.isoformat(),
        "end_time": end_time_obj.isoformat(),
        "p1_customer_affected": extract_checkbox(state_values, "p1_customer_affected"),
        "suspected_affected_components": suspected_affected_components,
        "description": state_values.get("description", {}).get("description_action", {}).get("value"),
        "message_for_sp": state_values.get("message_for_sp", {}).get("message_for_sp_action", {}).get("value", ""),
        "statuspage_notification": extract_checkbox(state_values, "flags_for_statuspage_notification", "statuspage_notification"),
        "separate_channel_creation": extract_checkbox(state_values, "flags_for_statuspage_notification", "separate_channel_creation"),
    }

def extract_checkbox(state_values, key, value=None):
    options = state_values.get(key, {}).get(f"{key}_action", {}).get("selected_options", [])
    return any(option.get("value") == (value or key) for option in options)
    
async def process_incident_creation(incident_data: dict, trigger_id: str, settings: Settings, db: None=None):
    logger.info("Starting incident creation process")
    try:
        
        # Create Jira ticket
        incident = schemas.IncidentCreate(**incident_data)
        issue = await create_jira_ticket(incident)
        
        # Update incident data
        incident_data["so_number"] = issue["key"]
        incident_data["jira_issue_key"] = issue["key"]
        #Only if database is provided
        if db:
            # Save to database
            db_incident = models.Incident(**incident_data)
            try:
                db.add(db_incident)
                db.commit()
                db.refresh(db_incident)
            except Exception as db_error:
                logger.error(f"Database error: {str(db_error)}")
                db.rollback()
                raise
        else:
            # If no db is provided, you might want to log this or handle it differently
            logger.warning("No database provided. Skipping database operations.")

        # Send success message to Slack
        try:
            await open_slack_response_modal(
                trigger_id=trigger_id,
                modal_type="success",
                incident_data={
                    "so_number": incident_data["so_number"],
                    "severity": incident_data["severity"],
                    "jira_url": f"{settings.jira_server}/browse/{issue['key']}"
                }
            )
        except Exception as slack_error:
            logger.error(f"Error sending Slack success message: {str(slack_error)}")
            await open_slack_response_modal(
                trigger_id=trigger_id,
                modal_type="error",
                incident_data={
                    "error": str(slack_error)
                }
            )

        # Create Slack channels and send messages
        try:
            channel_name = f"incident-{db_incident.so_number}".lower()
            channel_id = await create_slack_channel(channel_name)
            incident_message = create_incident_message(db_incident, settings)
            await post_message_to_slack(channel_id, incident_message)
            logger.info(f"Posted message to incident channel {channel_name}")
            
            # Post to general outages channel
            general_outages_message = create_general_outages_message(db_incident, channel_id)
            await post_message_to_slack(settings.SLACK_GENERAL_OUTAGES_CHANNEL, general_outages_message)
            logger.info("Posted message to general outages channel")
            
            # Post to team channel
            if db_incident.suspected_owning_team:
                team_name = db_incident.suspected_owning_team[0]
                team_channel_id = get_slack_channel_id_for_team(team_name)
                if team_channel_id:
                    team_message = create_team_message(db_incident, channel_id)
                    await post_message_to_slack(team_channel_id, team_message)
                    logger.info(f"Posted message to {team_name} team channel")

        except Exception as slack_error:
            logger.error(f"Slack API error: {str(slack_error)}")
            
        # Handle Statuspage
        if db_incident.statuspage_notification:
            try:
                statuspage_response = await create_statuspage_incident(db_incident, settings, db)
                logger.info(f"Statuspage incident created with ID: {statuspage_response.get('id')}")
                db_incident.statuspage_incident_id = statuspage_response.statuspage_incident_id
                db.commit()
            except Exception as e:
                logger.error(f"Unexpected error creating Statuspage incident for SO {db_incident.so_number}: {str(e)}")
                db_incident.status = "STATUSPAGE_CREATION_FAILED"
                db.commit()

        #Create OpsGenie alert
        try:
            opsgenie_response = await create_alert(db_incident)
            if opsgenie_response["status_code"] == 201:
                logger.info(f"OpsGenie alert created with ID: {opsgenie_response.json()['id']}")
            else:
                logger.error("Failed to create OpsGenie alert")
        except Exception as e:
            logger.error(f"Error creating OpsGenie alert: {str(e)}")

    except Exception as e:
        logger.error(f"Error in background processing: {str(e)}", exc_info=True)
        try:
            await open_slack_response_modal(
                trigger_id=trigger_id,
                modal_type="error",
                incident_data={
                    "error": "An unexpected error occurred during incident creation. Please try again or contact support."
                }
            )
        except Exception as slack_error:
            logger.error(f"Error sending Slack error message: {str(slack_error)}")

    logger.info("Incident creation process completed")

def create_incident_message(db_incident, settings):
    return (
        f"\U0001F6A8 *New Incident Created* \U0001F6A8\n\n"
        f"*Incident Summary:*\n"
        f"----------------------------------\n"
        f"*SO Number:* {db_incident.so_number}\n"
        f"*Severity Level:* {', '.join(db_incident.severity)}\n"
        f"*Affected Products:* {', '.join(db_incident.affected_products)}\n"
        f"*Customer Impact:* {'Yes' if db_incident.p1_customer_affected else 'No'}\n"
        f"*Suspected Owning Team:* {', '.join(db_incident.suspected_owning_team)}\n"
        f"\n"
        f"*Time Details:*\n"
        f"----------------------------------\n"
        f"Start Time: {db_incident.start_time}\n"
        f"\n"
        f"*Additional Information:*\n"
        f"----------------------------------\n"
        f"🔗 *Jira Link:* [View Incident in Jira]({settings.jira_server}/browse/{db_incident.jira_issue_key})"
    )

def create_general_outages_message(db_incident, channel_id):
    return (
        f"\U0001F6A8 *New Incident Created* \U0001F6A8\n\n"
        f"Incident Summary\n"
        f"------------------------\n"
        f"SO Number: {db_incident.so_number}\n"
        f"Severity: {', '.join(db_incident.severity)}\n"
        f"Affected Products: {', '.join(db_incident.affected_products)}\n"
        f"Customer Impact: {'Yes' if db_incident.p1_customer_affected else 'No'}\n"
        f"Suspected Owning Team: {', '.join(db_incident.suspected_owning_team)}\n\n"
        f"*Time Details:*\n"
        f"------------------------\n"
        f"Start Time: {db_incident.start_time}\n"
        f"*Additional Information:*\n"
        f"----------------------------------\n"
        f"Join the discussion in the newly created incident channel: <#{channel_id}>"
    )

def create_team_message(db_incident, channel_id):
    return (
        f"\U0001F6A8 *New Incident Created* \U0001F6A8\n\n"
        f"Incident Summary\n"
        f"------------------------\n"
        f"SO Number: {db_incident.so_number}\n"
        f"Severity: {', '.join(db_incident.severity)}\n"
        f"Affected Products: {', '.join(db_incident.affected_products)}\n"
        f"Customer Impact: {'Yes' if db_incident.p1_customer_affected else 'No'}\n"
        f"Suspected Owning Team: {', '.join(db_incident.suspected_owning_team)}\n\n"
        f"*Time Details:*\n"
        f"------------------------\n"
        f"Start Time: {db_incident.start_time}\n"
        f"*Additional Information:*\n"
        f"----------------------------------\n"
        f"Join the discussion in the newly created incident channel: <#{channel_id}>"
    )