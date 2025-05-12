import os
import json
import re
import streamlit as st
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from openai import OpenAI
from task_utils import get_tasks_service, create_google_task, complete_google_task, list_tasks, delete_all_tasks, categorize_tasks

# Load environment
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Sidebar
st.sidebar.title("🔧 Navigation")
if st.sidebar.button("🧹 Clear All Data & Start Fresh"):
    service = get_tasks_service()
    delete_all_tasks(service)
    st.success("✅ All tasks and plans cleared! Refresh to start fresh.")

page = st.sidebar.radio("Go to", ["🏠 Dashboard", "📅 Daily Planner", "📋 Today's Task List", "📚 Plan History"])
service = get_tasks_service()

# Dashboard
if page == "🏠 Dashboard":
    st.title("👋 Welcome to Life Admin Agent")
    now = datetime.now()
    greeting = "Good Morning" if now.hour < 12 else ("Good Afternoon" if now.hour < 18 else "Good Evening")
    st.header(f"{greeting}, Raj! ☀️")
    st.write(f"Today is **{now.strftime('%A, %d %B %Y')}** 📅")

    overdue, pending, completed = categorize_tasks(list_tasks(service))
    st.metric("⏰ Pending Tasks", len(pending))
    st.metric("✅ Completed Tasks", len(completed))
    st.metric("⚠️ Overdue Tasks", len(overdue))

# Daily Planner
if page == "📅 Daily Planner":
    st.title("📅 Daily Planner")
    task_input = st.text_area("Enter tasks separated by commas:")

    if st.button("⚡ Auto Schedule & Push"):
        if not task_input.strip():
            st.warning("⚠️ Please enter some tasks!")
        else:
            raw_tasks = [task.strip() for task in task_input.split(",") if task.strip()]
            current_time = datetime.now().strftime("%I:%M %p")

            prompt = f"""
You are a highly disciplined professional daily planner AI.

Tasks for today ({datetime.now().strftime("%Y-%m-%d")}):
{', '.join(raw_tasks)}

Current Time: {current_time}

Rules:
- Generate a detailed, optimized hourly schedule.
- Strictly use this format for each task:
[Start Time] - [End Time]: [Task Title]

Example:
10:00 AM - 10:30 AM: Study
10:30 AM - 11:00 AM: Break
11:00 AM - 12:00 PM: Job Application

- Do NOT write 'Tonight', 'Tomorrow', or any headings.
- Only list today's tasks.
- No extra explanations or paragraphs.
- No bullet points, no numbering, just direct timeline.

Only output the list. No commentary.
"""

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a professional daily planner assistant."},
                    {"role": "user", "content": prompt}
                ]
            )
            plan = response.choices[0].message.content

            st.text_area("Generated Plan", plan, height=300)

            # Save plan to file
            LOG_FILE = "plans_log.json"
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    logs = json.load(f)
            else:
                logs = []
            logs.append({
                'plan_type': "auto_schedule",
                'timestamp': str(datetime.now()),
                'task_list': raw_tasks,
                'plan_text': plan
            })
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2)

            # Push tasks to Google Tasks
            tasks_pushed = 0
            today = datetime.now().date()
            lines = plan.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                line = line.replace("–", "-").replace("—", "-").strip("•-–— ")

                match = re.match(r"^(\d{1,2}:\d{2}\s?[APMapm]{2})\s*-\s*(\d{1,2}:\d{2}\s?[APMapm]{2}):\s*(.+)$", line)
                if match:
                    try:
                        start_time_str, end_time_str, task_name = match.groups()
                        due_dt = datetime.strptime(end_time_str.strip(), "%I:%M %p").replace(
                            year=today.year, month=today.month, day=today.day
                        ).astimezone(timezone.utc)

                        if due_dt.date() == today:
                            create_google_task(service, task_name, due_dt)
                            tasks_pushed += 1
                    except Exception as e:
                        print("Error parsing task line:", line, "Error:", e)
                        continue

            st.success(f"✅ {tasks_pushed} Tasks pushed successfully!")

# Today's Task List
if page == "📋 Today's Task List":
    st.title("📋 Your Tasks for Today")
    tasks = list_tasks(service)
    overdue, pending, completed = categorize_tasks(tasks)

    if overdue:
        st.subheader("⚠️ Overdue Tasks")
        for idx, (title, due) in enumerate(overdue):
            if st.checkbox(f"❗ {title}", key=f"overdue_{idx}"):
                complete_google_task(service, tasks[[t['title'] for t in tasks].index(title)]['id'])
                st.success(f"✅ Marked '{title}' complete!")
                st.rerun()

    if pending:
        st.subheader("⏰ Pending Tasks")
        for idx, (title, due) in enumerate(pending):
            if st.checkbox(f"🕒 {title}", key=f"pending_{idx}"):
                complete_google_task(service, tasks[[t['title'] for t in tasks].index(title)]['id'])
                st.success(f"✅ Marked '{title}' complete!")
                st.rerun()

    if completed:
        st.subheader("✅ Completed Tasks")
        for idx, (title, due) in enumerate(completed):
            st.write(f"✔️ {title}")

# Plan History
if page == "📚 Plan History":
    st.title("📚 Plan History Log")
    LOG_FILE = "plans_log.json"
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = json.load(f)
        logs = sorted(logs, key=lambda x: x['timestamp'], reverse=True)
        for entry in logs:
            st.subheader(f"📅 {entry['plan_type'].capitalize()} Plan | {entry['timestamp'][:10]}")
            st.markdown(f"**Tasks:** {', '.join(entry['task_list'])}")
            st.text_area("Plan Output", value=entry['plan_text'], height=250)
    else:
        st.info("ℹ️ No plans logged yet.")
