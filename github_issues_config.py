import os
import json 
from dotenv import load_dotenv

load_dotenv()

# Load configuration from config.json
with open('github_issues_config.json') as config_file:
    config = json.load(config_file)

# Github Configuration
github_personal_access_token=os.getenv("github_personal_access_token")
github_owner = os.getenv('github_owner')
github_repo = os.getenv('github_repo')

# ClickUp configuration
clickup_api_key = os.getenv('clickup_api_key')
clickup_list_id = os.getenv('clickup_list_id')
clickup_space_id = os.getenv('clickup_space_id')
slack_webhook_url = os.getenv('slack_webhook_url')
request_type_custom_field_id = os.getenv('request_type_custom_field_id')

# Request type IDs
label_to_request_type_id = config.get('label_to_request_type_id', {
    'bug': 'bb6de1dc-da65-4a85-9d0e-5065919fede5',          # request type id for bug
    'enhancement': '15c61688-3ad5-4dc5-bb7f-17b6c6ff30d9',  # request type id for enhancement
    'question': '3328c6c2-06f8-41e4-a76c-4fb435df2bb2',     # request type id for question
    'task': '7abfef5b-9190-4726-8ed5-d5e317eb9c93'          # request type id for task
})

# Priority mapping if issue has a label p0 then it is set to urgent, if the label is p1 then priority is high, if request type is bug then priority is high, similarly for enhancement and task the priority is normal 
label_to_priority = config.get('label_to_priority', {
    'p0': 1,    
    'p1': 2,
    'bug': 2,
    'enhancement': 3,
    'task': 3,
})