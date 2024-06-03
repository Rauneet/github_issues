import requests
import os
import re
import json
import time
import schedule
import logging
from github_issues_config import (
    github_personal_access_token, github_owner, github_repo,
    clickup_api_key, clickup_list_id, clickup_space_id,
    request_type_custom_field_id, label_to_request_type_id ,
    label_to_priority, slack_webhook_url
)

# Environment variables 
# clickup_api_key =   # this is not the facets clickup api key
# clickup_list_id =                                   # list id which is not of facets
# clickup_space_id =                                  # space id which is not of facets 
# github_personal_access_token =   # My github personal access token
# github_owner =         # github repo is also for testing 
# github_repo =    # repo name

# Github and clickup API URL and Headers 
github_api_url = f"https://api.github.com/repos/{github_owner}/{github_repo}/issues"   
github_headers = {
   "Authorization": f'token {github_personal_access_token}',
   "Accept": "application/vnd.github+json" 
}

clickup_api_url = "https://api.clickup.com/api/v2"                                     
clickup_headers = {
    "Authorization": clickup_api_key,
    "Content-Type": 'application/json'
}

# Map of GitHub labels to ClickUp "Request Type" IDs
# Replace these request type field id with the facets request type ids 
label_to_request_type_id = {
    'bug': 'bb6de1dc-da65-4a85-9d0e-5065919fede5',          # request type id for bug 
    'enhancement': '15c61688-3ad5-4dc5-bb7f-17b6c6ff30d9',  # request type id for enhancement 
    'question': '3328c6c2-06f8-41e4-a76c-4fb435df2bb2',     # request type id for question 
    'task': '7abfef5b-9190-4726-8ed5-d5e317eb9c93'          # request type id for task
}

# Map of github labels to clickup priority value 
label_to_priority = {
    'p0': 1,    # Urgent 
    'p1': 2,    # High
    'bug': 2,   # High
    'enhancement': 3,  # Normal
}

#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def fetch_github_issues():
    """Fetches github issues and return a list of issues"""
    response = requests.get(github_api_url, headers=github_headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f'Failed to fetch issues. Status code: {response.status_code}')
        response.raise_for_status()

# New function to fetch github issues 
def fetch_issue_details(issue_number):
    """Function to fetch the github issue details """
    url = f"{github_api_url}/{issue_number}"
    response = requests.get(url, headers=github_headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to fetch issue details. Status code: {response.status_code}")
        response.raise_for_status()

# Function to fetch images from github issues 
def extract_image_urls(issue_body):
    urls = re.findall(r"(https?://\S+\.(?:jpg|jpeg|png|gif))", issue_body)
    return urls

def upload_image_to_clickup_task(task_id, image_url):
    image_response = requests.get(image_url)
    if image_response.status_code == 200:
        files = {'file': (os.path.basename(image_url), image_response.content)}
        upload_url = f"{clickup_api_url}/task/{task_id}/attachment"
        response = requests.post(upload_url, headers=clickup_headers, files=files)
        if response.status_code == 200:
            print("Image uploaded successfully.")
        else:
            print(f"Failed to upload image {response.status_code}")
    else:
        print(f"Failed to download image {image_response.status_code}")

def fetch_clickup_list_details():
    """Fetches details of the specified Clickup list"""
    list_url = f'{clickup_api_url}/list/{clickup_list_id}'
    response = requests.get(list_url, headers=clickup_headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f'Failed to fetch list details. Status code: {response.status_code}')
        print(f"Response: {response.text}")
        response.raise_for_status()

def fetch_clickup_tasks():
    """Fetches task from the specified Clickup list and returns a list of tasks"""
    tasks_url = f'{clickup_api_url}/list/{clickup_list_id}/task'
    response = requests.get(tasks_url, headers=clickup_headers)
    if response.status_code == 200:
        tasks_data = response.json()   #new line added 
        return tasks_data['tasks'] if 'tasks' in tasks_data else []                                                                        #return response.json().get('tasks', [])
    else:
        print(f'Failed to fetch tasks. Status code: {response.status_code}')
        response.raise_for_status()

def get_valid_status():
    """Retrieves the valid status for new tasks from the ClickUp list and returns string for new task"""
    list_details = fetch_clickup_list_details()
    statuses = list_details.get('statuses', [])
    for status in statuses:
        if status.get('status', '').upper() == 'TO DO':
            return status['status']
    return statuses[0]['status'] if statuses else None

# def valid_status():
#     try:
#         list_details = fetch_clickup_list_details()
#         statuses = list_details.get('status', [])
#         normalized_statuses = {status['status'].strip().upper(): status['status'] for status in statuses}
#         target_statuses = ["OPEN", "BLOCKED", "DUPLICATE"]
#         for target_status in target_statuses:
#             if target_status in normalized_statuses:
#                 return normalized_statuses[target_status]
#         return statuses[0]['status'] if statuses else None
#     except Exception as e:
#         print(f'Error fetching and processing statuses {e}')
#         return None
                
def get_request_type_value(labels):
    """ Retrieves the request type value based on GitHub labels."""
    for label in labels:
        if label['name'].lower() in label_to_request_type_id:
            return label_to_request_type_id[label['name'].lower()]
    return '7abfef5b-9190-4726-8ed5-d5e317eb9c93'  # Default to 'Task' if no match

def get_priority_value(labels, request_type_value):
    """Retrieves the priority value based on GitHub labels and request type"""
    for label in labels:
        if label['name'].lower() in label_to_priority:
            return label_to_priority[label['name'].lower()]
    # Default priority based on request type
    if request_type_value ==  label_to_request_type_id['bug']:                                    #"e44ee5e4-c5a7-465c-982b-5bbc6475a20a":  #if it is a bug 
        return 1
    #if request type is task , enhancement , question
    elif request_type_value in [label_to_request_type_id['enhancement'], label_to_request_type_id['task'], label_to_request_type_id['question']]:
        return 3
    else:
        return 2

def task_exists(issue, clickup_tasks):
    """Checks if a task exists in ClickUp based on the GitHub issue title."""
    issue_title = issue['title'].strip().lower()  # Normalize the issue title
    for task in clickup_tasks:
        if 'name' in task and task['name'].strip().lower() == issue_title:  # Ensure name exists and compare
            return True
    return False

# def task_exists(issue, clickup_tasks):
#     issue_title = issue['title'].strip().lower()
#     for task in clickup_tasks:
#         task_name = task['name'].strip().lower()
#         if issue_title == task_name:
#             return True
#         return False
# def task_exists(issue,clickup_tasks):
#     """Checks the task exist in the list then skip the creation of duplicate tasks"""
#     for task in clickup_tasks:
#         if issue['title'] in task['name']:
#             return True
#         return False

def create_clickup_task(issue, valid_statuses, request_type_custom_field_id):
    """Creates a clickup task for the corresponding github issue and also fetches the request type , priority value and add the task title as the issue title
    and add the description if provided and embed it with the issue link and set the request type and priority based on guthub labels"""
    request_type_value = get_request_type_value(issue['labels'])
    priority_value = get_priority_value(issue['labels'], request_type_value)
    task_url = f'{clickup_api_url}/list/{clickup_list_id}/task'
    body_content = issue.get("body", "No Description provided") or "No description provided"
    description = body_content + f'\n\nOriginal GitHub Issue: {issue["html_url"]}'
    issue_details = fetch_issue_details(issue["number"])
    image_urls = extract_image_urls(issue_details["body"])
    if image_urls:
        description += f'\n![Image]({url})'
    task_data = {
        'name': issue['title'],
        'description': description,                                          #issue.get('body', 'No description provided') + f'\n\nOriginal GitHub Issue: {issue["html_url"]}',
        'status': valid_statuses,
        'priority': priority_value,
        'assignees': [],
        'custom_fields': [
            {
                'id': request_type_custom_field_id,
                'value': request_type_value
            }
        ]
    }
    print(f"Request Data: {json.dumps(task_data, indent=4)}")
    response = requests.post(task_url, headers=clickup_headers, json=task_data)
    if response.status_code == 200:
        task = response.json()   #task is not included here , this line was not included here 
        clickup_task_url = task['url']
        task_id = task['id'] 
        task_name = task['name']
        github_issue_url = issue["html_url"]
        task_priority = task.get("priority", {}).get("id")
        if task_priority in ["1", "2"]:
            for url in image_urls:
                upload_image_to_clickup_task(task_id, url)
            send_slack_notification(issue['html_url'], task_name, clickup_task_url)   #these are not included, intended so that the notification is sent only for urgent/high priority ticket
        return task
    else:
        print(f'Failed to create task in clickup. Status code {response.status_code}')
        print(f"Response: {response.text}")
        response.raise_for_status()

response = requests.get(f"{clickup_api_url}/space/{clickup_space_id}/field", headers=clickup_headers)
if response.status_code == 200:
    custom_fields = response.json()
    for field in custom_fields['fields']:
        print(f"Field Name: {field['name']}, Field ID: {field['id']}")
        if field['name'] == "Request Type":  # Replace with the actual name of your custom field
            request_type_custom_field_id = field['id']
else:
    print(f"Failed to fetch custom fields. Status code {response.status_code}")
    print(f"Response: {response.text}")


#This is the working slack notification function
def send_slack_notification(github_issue_url, task_name, clickup_task_url):
    message = f"New ticket is created: {task_name} \n Ticket link: {clickup_task_url}\n Github issue link: {github_issue_url} "
    payload = {
        "text": message
    }
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(slack_webhook_url,json=payload, headers=headers)
    if response.status_code == 200:
        print(f"Notification sent to slack successfully")
    else:
        print(f"Failed to send notification to Slack. Status code {response.status_code}")
        print(f"Response: {response.text}")


# Remove this function just for testing 
def update_clickup_task(clickup_task_id, updates):
    url = f'{clickup_api_url}/task/{clickup_task_id}'
    response = requests.put(url,headers=clickup_headers, json=updates)
    if response.status_code == 200:
        print(f"Task updated successfully")
    else:
        print(f"Failed to update task")
        print(f"Response: {response.text}")

# Remove this function just for testing 
def sync_github_issue_to_clickup_task(issue, clickup_tasks):
    exists = False
    for task in clickup_tasks:
        if task['name'] == issue['title']:
            exists = True
            # Prepare for updates
            updates = {}
            if 'description' in issue and issue['body'] != task['description']:
                updates['description'] = issue['body'] + f'\n\nOriginal GitHub Issue: {issue["html_url"]}'
            if issue['state'] == 'closed' and task['status'] != 'complete':
                updates['status'] = 'complete'
            if updates:
                update_clickup_task(task['id'], updates)
            break
    if not exists:
        create_clickup_task(issue, 'TO DO', request_type_custom_field_id)

# Remove this function just for testing 
def handle_deleted_issues(github_issues, clickup_tasks):
    github_titles = {issue["title"] for issue in github_issues}
    for task in clickup_tasks:
         if task['name'] not in github_titles:
              update_clickup_task(task['id'], {'status': 'complete'})

# Remove this function just for testing 
def fetch_github_comments(issue_number):
    url = f"{github_api_url}/repos/{github_owner}/{github_repo}/issues/{issue_number}/comments"
    response = requests.get(url, headers=github_headers)
    if response.status_code == 200:
        print(f"Comments fetched successfully")
        return response.json()
    else:
        return []
    
# Remove this function just for testing 
def add_comment_to_clickup(task_id, comment_text):
    url = f"{clickup_api_url}/task/{task_id}/comment"
    data = {
        'comment_text': comment_text
    }
    response = requests.post(url, headers=clickup_headers, json=data)
    if response.status_code == 200:
        print(f"Comment added to clickup {response.text}")
    else:
        print(f"Failed to add comment to clickup")

# Remove this function just for testing  
def add_comment_to_github(issue_number, comment_text):
    url = f"{github_api_url}/repos/{github_owner}/{github_repo}/issues/{issue_number}/comments"
    data = {
        'body': comment_text
    }
    response = requests.post(url, headers=github_headers, json=data)
    if response.status_code != 201:
        print("Failed to add comment to GitHub issue:", response.text)


# Remove this function just for testing     
def fetch_clickup_comments(task_id):  
    url = f"{clickup_api_url}/task/{task_id}/comment"
    response = requests.get(url, headers=clickup_headers)
    if response.status_code == 200:
        print(f"Fetching comments from clickup")
        return response.json()
    else:
        return []
    
# Remove this function just for testing  
def sync_comments_between_github_clickup(issue, task_id):
    github_comments = fetch_github_comments(issue['number'])
    clickup_comments = fetch_clickup_comments(task_id)
    for comment in github_comments:
        comment_text = f"{comment['user']['login']}: {comment['body']}"
        add_comment_to_clickup(task_id, comment_text)
    for comment in clickup_comments["comments"]:
        comment_text = f"{comment['user']['username']}: {comment['comment_text']}"
        add_comment_to_github(issue['number'], comment_text)
    

# Uncomment this function as this was the main function which is working 

def sync_github_to_clickup():
    """Sync with github make sure that the issues"""
    try:
        print(f'Fetching github issues....')
        issues = fetch_github_issues()
        clickup_tasks = fetch_clickup_tasks()
        print(f"Existing ClickUp tasks: {[task['name'] for task in clickup_tasks]}")  # Debugging line
        list_details = fetch_clickup_list_details()
        valid_statuses = get_valid_status()
        initial_status = valid_statuses[0] if valid_statuses else 'TO DO' 
        request_type_custom_field_id = "0f3ee9db-dd7d-4893-80ae-3f2f816043d4"                                         #'c7bcbc1f-d7ee-4355-98d5-8706cf0f9bcc'  # Request type id
        # Update existing tasks or create new tasks for each GitHub issue
        for issue in issues:
            if task_exists(issue, clickup_tasks):
                # If the task exists, sync it with the current state of the GitHub issue
                sync_github_issue_to_clickup_task(issue, clickup_tasks) # remove this 
                print(f"Task for issue #{issue['number']} updated or verified as existing.") # remove this 
                print(f"Task for issue #{issue['number']} already exists. Skipping creation.") 
                continue                                                                        
            print(f"Creating ClickUp task for issue #{issue['number']}: {issue['title']}")
            clickup_task = create_clickup_task(issue, valid_statuses,request_type_custom_field_id)
            print(f"Created ClickUp task: {clickup_task['id']}")
        handle_deleted_issues(issues, clickup_tasks)  # remove this 
        print("All issues have been successfully added to ClickUp.")
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

# def sync_github_to_clickup():
#     """Sync with github make sure that the issues."""
#     try:
#         print(f'Fetching github issues....')
#         issues = fetch_github_issues()
#         clickup_tasks = fetch_clickup_tasks()
#         print(f"Existing ClickUp tasks: {[task['name'] for task in clickup_tasks]}")  # Debugging line
#         list_details = fetch_clickup_list_details()
#         valid_statuses = get_valid_status()
#         initial_status = valid_statuses[0] if valid_statuses else 'TO DO' 
#         request_type_custom_field_id = "0f3ee9db-dd7d-4893-80ae-3f2f816043d4"  # Request type id

#         for issue in issues:
#             task_found = False
#             for task in clickup_tasks:
#                 if 'name' in task and task['name'] == issue['title']:
#                     task_found = True
#                     # Sync comments after confirming task exists
#                     sync_comments_between_github_clickup(issue, task['id'])
#                     print(f"Task for issue #{issue['number']} updated or verified as existing.")
#                     break
#             if not task_found:
#                 print(f"Creating ClickUp task for issue #{issue['number']}: {issue['title']}")
#                 new_task = create_clickup_task(issue, initial_status, request_type_custom_field_id)
#                 print(f"Created ClickUp task: {new_task['id']}")
#                 # Sync comments for the newly created task
#                 sync_comments_between_github_clickup(issue, new_task['id'])

#         print("All issues have been successfully added to ClickUp.")
#     except requests.exceptions.RequestException as e:
#         print(f"An error occurred: {e}")

# def schedule_script():
#     """script will run every 4 hour and check for new issue in github and creates task"""
#     schedule.every(4).hours.do(sync_github_to_clickup)
#     while True:
#         schedule.run_pending()
#         time.sleep(1)    

if __name__ == '__main__':
    sync_github_to_clickup()
    #schedule_script()
