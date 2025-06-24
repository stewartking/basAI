# ai_diagnosis.py
import os, openai, json

openai.api_key = os.getenv("OPENAI_API_KEY")

PROMPT_TEMPLATE = """
You are a building automation diagnostic assistant.
Given this data:
{data}
Provide:
1. A summary of current status.
2. Any abnormal readings.
3. Possible causes and what to do.
Return JSON with keys: summary, abnormalities, recommendations.
Do not wrap the response in a code block.
"""

def analyze(data_json):
    prompt = PROMPT_TEMPLATE.format(data=json.dumps(data_json))
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    content = resp.choices[0].message.content
    # Strip code block if present
    if content.startswith("```json\n") and content.endswith("\n```"):
        content = content[8:-4]
    try:
        return json.loads(content)
    except Exception as e:
        print(f"⚠️ Error parsing LLM response: {e}")
        return {"summary": "Error parsing AI response", "abnormalities": [], "recommendations": []}
