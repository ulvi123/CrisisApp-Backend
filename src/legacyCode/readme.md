older less optimized code for incident generation.The code was working fine but was not optimal when returning the immediate response to slack

 # Handling the incident form creation submission
        # if callback_id == "incident_form":
        #     try:
        #         state_values = (
        #             payload.get("view", {}).get("state", {}).get("values", {})
        #         )
        #         print("State values:", json.dumps(state_values, indent=2))

        #         # Extracting and converting the start_time and end_time
        #         state_values = (
        #             payload.get("view", {}).get("state", {}).get("values", {})
        #         )
        #         start_date = (
        #             state_values.get("start_time", {})
        #             .get("start_date_action", {})
        #             .get("selected_date")
        #         )
        #         start_time = (
        #             state_values.get("start_time_picker", {})
        #             .get("start_time_picker_action", {})
        #             .get("selected_time")
        #         )
        #         end_date = (
        #             state_values.get("end_time", {})
        #             .get("end_date_action", {})
        #             .get("selected_date")
        #         )
        #         end_time = (
        #             state_values.get("end_time_picker", {})
        #             .get("end_time_picker_action", {})
        #             .get("selected_time")
        #         )

        #         if not start_date or not start_time:
        #             raise HTTPException(
        #                 status_code=400, detail="Missing start datetime"
        #             )
        #         if not end_date or not end_time:
        #             raise HTTPException(status_code=400, detail="Missing end datetime")

        #         # Combine date and time strings
        #         start_datetime_str = f"{start_date}T{start_time}:00"
        #         end_datetime_str = f"{end_date}T{end_time}:00"

        #         # Exception handling
        #         try:
        #             start_time_obj = datetime.strptime(
        #                 start_datetime_str, "%Y-%m-%dT%H:%M:%S"
        #             )
        #             end_time_obj = datetime.strptime(
        #                 end_datetime_str, "%Y-%m-%dT%H:%M:%S"
        #             )
        #         except ValueError:
        #             raise HTTPException(
        #                 status_code=400, detail="Invalid datetime format"
        #             ) from e

        #         # Extracting values from the Slack payload
        #         so_number = (state_values.get("so_number", {}).get("so_number_action", {}).get("value"))
                
        #         #checking if so number is properly extracted from slack payload
        #         if not so_number:
        #             logger.error("Missing SO number")
        #             print("Missing SO number")
        #         else:
        #             print(f"SO number: {so_number}")
                
        #         affected_products_options = (
        #             state_values.get("affected_products", {})
        #             .get("affected_products_action", {})
        #             .get("selected_options", [])
        #         )
        #         affected_products = [
        #             option["value"] for option in affected_products_options
        #         ]

        #         suspected_owning_team_options = (
        #             state_values.get("suspected_owning_team", {})
        #             .get("suspected_owning_team_action", {})
        #             .get("selected_options", [])
        #         )
        #         suspected_owning_team = [
        #             option["value"] for option in suspected_owning_team_options
        #         ]

        #         suspected_affected_components_options = (
        #             state_values.get("suspected_affected_components", {})
        #             .get("suspected_affected_components_action", {})
        #             .get("selected_options", [])
        #         )
        #         suspected_affected_components = [
        #             option["value"] for option in suspected_affected_components_options
        #         ]

        #         severity_option = (
        #             state_values.get("severity", {})
        #             .get("severity_action", {})
        #             .get("selected_option", {})
        #         )
        #         severity = severity_option.get("value") if severity_option else None
        #         severity = [severity] if severity else []
                
                
            
        #         # Creating the incident data
        #         incident_data = {
        #             "so_number": so_number,
        #             "affected_products": affected_products,
        #             "severity": severity,
        #             "suspected_owning_team": suspected_owning_team,
        #             "start_time": start_time_obj.isoformat(),
        #             "end_time": end_time_obj.isoformat(),
        #             "p1_customer_affected": any(
        #                 option.get("value") == "p1_customer_affected"
        #                 for option in state_values.get("p1_customer_affected", {})
        #                 .get("p1_customer_affected_action", {})
        #                 .get("selected_options", [])
        #             ),
        #             "suspected_affected_components": suspected_affected_components,
        #             "description": state_values.get("description", {})
        #             .get("description_action", {})
        #             .get("value"),
        #             "message_for_sp": state_values.get("message_for_sp", {})
        #             .get("message_for_sp_action", {})
        #             .get("value", ""),
        #             "statuspage_notification": any(
        #                 option.get("value") == "statuspage_notification"
        #                 for option in state_values.get(
        #                     "flags_for_statuspage_notification", {}
        #                 )
        #                 .get("flags_for_statuspage_notification_action", {})
        #                 .get("selected_options", [])
        #             ),
        #             "separate_channel_creation": any(
        #                 option.get("value") == "separate_channel_creation"
        #                 for option in state_values.get(
        #                     "flags_for_statuspage_notification", {}
        #                 )
        #                 .get("flags_for_statuspage_notification_action", {})
        #                 .get("selected_options", [])
        #             ),
                    
        #         }

        #     except ValidationError as e:
        #         raise HTTPException(
        #             status_code=400, detail=f"Failed to parse request body: {str(e)}"
        #         ) from e

        #     #Creating jira first
        #     incident = schemas.IncidentCreate(**incident_data)
        #     issue = await create_jira_ticket(incident)
            
        #     #Updating the incident with correct SO number
        #     incident_data["so_number"] = issue["key"]
        #     incident_data["jira_issue_key"] = issue["key"]
            
        #     #Saving to the database
        #     db_incident = models.Incident(**incident_data)
        #     db.add(db_incident)
        #     db.commit()
        #     db.refresh(db_incident)
            
            
        #     #Sending back the success or error message to the user in form of a modal popup alert-ready for testing!!!!!!!!!!!!
        #     try:
        #         #On success 
        #         await open_slack_response_modal(trigger_id=trigger_id,modal_type="success",incident_data={
        #             "so_number":incident_data["so_number"],
        #             "severity":incident_data["severity"],
        #             "jira_url":f"{settings.jira_server}/browse/{issue['key']}"
                    
        #         })
        #     except Exception as e:
        #         await open_slack_response_modal(
        #             trigger_id=trigger_id,
        #             modal_type="error",
        #             incident_data ={
        #                 "error":str(e)
        #             }
        #         )
            
            
            
        #     # Step1 - Slack channel creation and message
        #     try:
        #         channel_name = f"incident-{db_incident.so_number}".lower()
        #         channel_id = await create_slack_channel(channel_name)
        #         incident_message = (
        #             f"\U0001F6A8 *New Incident Created* \U0001F6A8\n\n"
        #             f"*Incident Summary:*\n"
        #             f"----------------------------------\n"
        #             f"*SO Number:* {db_incident.so_number}\n"
        #             f"*Severity Level:* {', '.join(db_incident.severity)}\n"
        #             f"*Affected Products:* {', '.join(db_incident.affected_products)}\n"
        #             f"*Customer Impact:* {'Yes' if db_incident.p1_customer_affected else 'No'}\n"
        #             f"*Suspected Owning Team:* {', '.join(db_incident.suspected_owning_team)}\n"
        #             f"\n"
        #             f"*Time Details:*\n"
        #             f"----------------------------------\n"
        #             f"Start Time: {db_incident.start_time}\n"
        #             f"\n"
        #             f"*Additional Information:*\n"
        #             f"----------------------------------\n"
        #             f"🔗 *Jira Link:* [View Incident in Jira]({settings.jira_server}/browse/{db_incident.jira_issue_key})"
        #         )

        #         await post_message_to_slack(channel_id, incident_message)
        #         logger.info(f"Posted message to incident channel {channel_name}")
                
        #         # Step2 - Posting message to general outages channel
        #         general_outages_message = (
        #             f"\U0001F6A8 *New Incident Created* \U0001F6A8\n\n"
        #             f"Incident Summary\n"
        #             f"------------------------\n"
        #             f"SO Number: {db_incident.so_number}\n"
        #             f"Severity: {db_incident.severity}\n"
        #             f"Affected Products: {', '.join(db_incident.affected_products)}\n"
        #             f"Customer Impact: {'Yes' if db_incident.p1_customer_affected else 'No'}\n"
        #             f"Suspected Owning Team: {db_incident.suspected_owning_team}\n\n"
        #             f"*Time Details:*\n"
        #             f"------------------------\n"
        #             f"Start Time: {db_incident.start_time}\n"
        #             f"*Additional Information:*\n"
        #             f"----------------------------------\n"
        #             f"Join the discussion in the newly created incident channel: <#{channel_id}>"
        #         )
        #         await post_message_to_slack(
        #             settings.SLACK_GENERAL_OUTAGES_CHANNEL, general_outages_message
        #         )
        #         logger.info("Posted message to general outages channel")
                
                
        #         #step3 -posting message to team slack channel
                
        #         if isinstance(db_incident.suspected_owning_team, list) and len(db_incident.suspected_owning_team) > 0:
        #             team_name = db_incident.suspected_owning_team[0]
        #             logger.debug(f"Original Team name: {team_name}")
        #             team_channel_id = get_slack_channel_id_for_team(team_name)
        #             logger.debug(f"Found channel ID: {team_channel_id}")
                        
        #             if team_channel_id:
        #                 incident_message = (
        #                         f"\U0001F6A8 *New Incident Created* \U0001F6A8\n\n"
        #                         f"Incident Summary\n"
        #                         f"------------------------\n"
        #                         f"SO Number: {db_incident.so_number}\n"
        #                         f"Severity: {db_incident.severity}\n"
        #                         f"Affected Products: {', '.join(db_incident.affected_products)}\n"
        #                         f"Customer Impact: {'Yes' if db_incident.p1_customer_affected else 'No'}\n"
        #                         f"Suspected Owning Team: {db_incident.suspected_owning_team}\n\n"
        #                         f"*Time Details:*\n"
        #                         f"------------------------\n"
        #                         f"Start Time: {db_incident.start_time}\n"
        #                         f"*Additional Information:*\n"
        #                         f"----------------------------------\n"
        #                         f"Join the discussion in the newly created incident channel: <#{channel_id}>"
        #                     )
                        
        #                 await post_message_to_slack(team_channel_id, incident_message)
        #                 logger.info(f"Posted message to {team_name} team channel")
    
        #     except SlackApiError as slack_error:
        #         logger.error(f"Slack API error: {slack_error.response['error']}", exc_info=True)
        #         raise HTTPException(
        #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #             detail=f"Failed to send Slack notifications: {slack_error.response['error']}"
        #         )
             
             
                 
            
        #     #Sending the incident to Statuspage
        #     if db_incident.statuspage_notification:
        #         try:
        #             statuspage_response = await create_statuspage_incident(db_incident, settings, db)
        #             logging.info(f"Statuspage incident created with ID: {statuspage_response.get('id')}")

        #             # Update the incident with statuspage information
        #             db_incident.statuspage_incident_id = statuspage_response.statuspage_incident_id
        #             db.commit()
                    
        #         except Exception as e:
        #             logging.error(
        #                 f"Unexpected error creating Statuspage incident for SO {db_incident.so_number}: "
        #                 f"{str(e)}"
        #             )
        #             # Update the incident status to reflect the failure
        #             db_incident.status = "STATUSPAGE_CREATION_FAILED"
        #             db.commit()
        #             raise HTTPException(
        #                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #                 detail=f"Unexpected error creating Statuspage incident: {str(e)}"
        #             )
            
        #     #Handling the opsgenie alert creation request
        #     opsgenie_response = await create_alert(db_incident)
        #     if opsgenie_response["status_code"] == 201:
        #         logger.info(f"OpsGenie alert created with ID: {response.json()['id']}")
        #     else:
        #         raise HTTPException(
        #             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        #             detail="Failed to create OpsGenie alert",
        #         )     
                
        #     logger.info(f"Returning response with incident_id: {db_incident.id}, issue_key: {issue['key']}")
            
            
        #     return {"response_action":"clear","incident_id": db_incident.id, "issue_key": issue["key"]}



 # elif callback_id == "statuspage_update":
        #     state_values = payload.get("view",{}).get("state",{}).get("values",{})
        #     #Extracting values from the slack payload
        #     so_number = state_values.get("so_number", {}).get("so_number_action", {}).get("value")
        #     if not so_number:
        #         logging.error("Missing 'SO_number_block' in the Slack payload.")
        #         raise HTTPException(status_code=400, detail="SO Number is required.")
        #     new_status = state_values.get("status_update_block", {}).get("status_action", {}).get("selected_option", {}).get("value")
        #     additional_info = state_values.get("additional_info_block", {}).get("additional_info_action", {}).get("value", "")
            
        #     #Introducing the validations section
        #     if not so_number and not new_status:
        #         raise HTTPException(status_code=400, detail="SO Number and new status are required.")
            
        #     #Fetching the incident from the database
        #      # Fetch incident from database
        #     db_incident = db.query(models.Incident).filter(models.Incident.so_number == so_number).first()
        #     if not db_incident:
        #         raise HTTPException(
        #             status_code=status.HTTP_404_NOT_FOUND,
        #             detail=f"No incident found with SO Number: {so_number}"
        #         )
            
        #     #Updating the status in the statuspage
        #     try:
        #         await update_statuspage_incident_status(
        #             db_incident = db_incident,
        #             new_status=new_status,
        #             additional_info=additional_info,
        #             settings = settings
        #         )
                
        #         #Updating the incident status in the database
        #         db_incident.status = new_status
        #         db.commit()
        #         db.refresh(db_incident)
                
        #         #Returning a response to the user
        #         return JSONResponse(
        #             status_code = 200,
        #             content = {
        #                 "response_type": "ephemeral",
        #                 "view": {
        #                     "type": "modal",
        #                     "title": {"type": "plain_text", "text": "Status Update"},
        #                     "close": {"type": "plain_text", "text": "Close"},
        #                     "blocks": [
        #                         {
        #                             "type": "section",
        #                             "text": {
        #                                 "type": "mrkdwn",
        #                                 "text": f"Status of SO Number: *{so_number}* has been updated to *{new_status}*."
        #                             }
        #                         }
        #                     ]
        #                 }
        #             }
        #         )
                
        #     except Exception as e:
        #         logging.error(f"Failed to update statuspage incident status: {str(e)}")
        #         raise HTTPException(status_code=500, detail="Failed to update statuspage incident status")