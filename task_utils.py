import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/tasks']

def get_tasks_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config(
                {
                    "installed": {
                        "client_id": os.getenv("GOOGLE_CLIENT_ID"),
                        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
                        "redirect_uris": ["http://localhost:8080/"],
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token"
                    }
                },
                SCOPES
            )
            creds = flow.run_local_server(port=8080)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('tasks', 'v1', credentials=creds)
    return service

def create_google_task(service, title, due_datetime):
    due_utc = due_datetime.astimezone(timezone.utc)
    task = {
        'title': title,
        'due': due_utc.isoformat(timespec='seconds').replace('+00:00', 'Z')
    }
    created_task = service.tasks().insert(tasklist='@default', body=task).execute()
    return created_task['id']

def complete_google_task(service, task_id):
    try:
        task = service.tasks().get(tasklist='@default', task=task_id).execute()
        task['status'] = 'completed'
        service.tasks().update(tasklist='@default', task=task_id, body=task).execute()
    except Exception as e:
        print(f"Error completing task: {e}")

def list_tasks(service):
    try:
        results = service.tasks().list(tasklist='@default', showCompleted=True).execute()
        return results.get('items', [])
    except Exception as e:
        print(f"Error listing tasks: {e}")
        return []

def delete_all_tasks(service):
    try:
        tasks = list_tasks(service)
        for task in tasks:
            service.tasks().delete(tasklist='@default', task=task['id']).execute()
    except Exception as e:
        print(f"Error deleting tasks: {e}")

def categorize_tasks(tasks):
    overdue = []
    pending = []
    completed = []

    now = datetime.now(timezone.utc).date()  # Only date

    for task in tasks:
        title = task.get('title', 'Untitled')
        due = task.get('due')
        status = task.get('status', 'needsAction')

        if due:
            due_dt = datetime.fromisoformat(due.replace('Z', '+00:00'))
            due_date = due_dt.date()

            if status == 'completed':
                completed.append((title, due_dt))
            elif due_date < now:
                overdue.append((title, due_dt))
            else:
                pending.append((title, due_dt))
        else:
            if status == 'completed':
                completed.append((title, None))
            else:
                pending.append((title, None))

    return overdue, pending, completed
