import os
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_tasks_from_user():
    print("Enter your admin tasks for today, separated by commas (e.g. 'renew license, call landlord'):")
    tasks_input = input("> ")
    raw_tasks = [task.strip() for task in tasks_input.split(",") if task.strip()]
    unique_tasks = list(dict.fromkeys(raw_tasks))  # remove duplicates
    return unique_tasks

def build_prompt(task_list):
    prompt = f"""
You are a productivity planning agent.

Your user has provided a list of unstructured tasks:
{task_list}

Your job is to:
1. Select the most important and achievable tasks for TODAY only.
2. Order them logically (e.g. quick wins first, deep work earlier in the day).
3. Estimate time for each task.
4. Add one motivational message to start the day.
5. Add a suggestion for how the user should review and plan for tomorrow.

Format:

🗓️ **Today’s Plan**
- Task 1 (time)
- Task 2 (time)
...

💬 Motivation:
[message]

🔁 Follow-up Suggestion:
[how to plan tomorrow based on today’s performance]
"""
    return prompt

def ask_openai(prompt):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a helpful agent."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content

if __name__ == "__main__":
    tasks = get_tasks_from_user()
    print("\n🧠 Processing your daily schedule...\n")
    prompt = build_prompt(", ".join(tasks))
    result = ask_openai(prompt)
    print(result)

    with open("today_plan.txt", "w", encoding="utf-8") as f:
        f.write(result)

    print("\n✅ Your plan has been saved to today_plan.txt")
