import logging

logging.basicConfig(
    level=logging.INFO,  # Set the level to DEBUG for more verbosity
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),  # Outputs logs to the console
        logging.FileHandler("app.log")  # Optionally log to a file
    ]
)
logger = logging.getLogger(__name__)


TEAM_SLACK_CHANNEL_MAPPING = {
    "3rd Party":"",
    "Algo Trading team":"",
    "Broadcast Monitoring Team":"",
    "Competition Manager":"",
    "Customer Integrations":"",
    "Digital Marketing":"",
    "Operational DBA":"",
    "Technical Services":"",
    "Feed Acquisition and Integrity":"",
    "FIBA Organizer":"",
    "Fixtures":"",
    "Genius Sport Support":"",
    "Volleyball Competition Management":"",
    "IT Infrastructure":"CFQUFLKRQ",
    "Play by Play Aggregation":"CFB5BC1PT",
    "Play by Play Collection":"C01VBFV9YPP",
    "Play by Play Statistics":"C04CAGJCWDB",
    "Multibet":"",
    "NSCM - NCAA":"C01FDNHK5CP",
    "Odds Ingestion and Standardization":"",
    "Operational Tools Fixtures":"CFRQFGDG8",
    "Operational Tools Reporters":"",
    "Risk Management Control":"CU8TXHC9J",
    "Risk Management Assessment":"CU8TXHC9J",
    "RiskManagement":"CU8TXHC9J",
    "Sportsbook 1":"",
    "Sportsbook 2":"",
    "Sportsbook 3":"",
    "Sportsbook 4":"",
    "Sportsbook Management Integrations":"",
    "Sportsbook Implementation Team":"",
    "Content Graph":"",
    "Sports Modelling API":"",
    "SportzCast":"",
    "Sports Reporting Tools":"",
    "Stats Engine":"CFFRPCBHR",
    "Video Distribution - Genius Live":"CM9EKPHU4",
    "Sports Content":"",
    "Volleyball On Court":"",
    "Volleyball Competition Manager":"",
}
  
   
def get_slack_channel_id_for_team(team_name:str) -> str | None:
    
    #normalizing the input team name
    normalized_team_name = team_name.strip().lower()
    
    #Debugging
    logger.debug(f"Looking up channel for normalized team name: {normalized_team_name}")
    logger.debug(f"Available mappings: {TEAM_SLACK_CHANNEL_MAPPING}")
    
    #normalized mapping for case insensitive cmaprison
    normalized_mapping = {k.strip().lower(): v for k, v in TEAM_SLACK_CHANNEL_MAPPING.items()}
    
    #Channel ID look up
    channel_id = normalized_mapping.get(normalized_team_name)
    
    if channel_id:
        logger.debug(f"Found channel ID: {channel_id}")
    else:
        logger.warning(f"No channel ID found for team: {team_name}")
    
    return channel_id

