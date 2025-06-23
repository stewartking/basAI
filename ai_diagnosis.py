import os, openai, json

openai.api_key = os.getenv("OPENAI_API_KEY")

PROMPT_TEMPLATE = """
You are a building automation diagnostic assistant.
Given this data:
{data}
Provide:
1. A summary of current status.
2. Any abnormal readings.
3. Possible chances and what to do.
Return JSON with keys: summary, abnormalities, recommendations.
"""

def analyze(data_json):
    prompt = PROMPT_TEMPLATE.format(data=json.dumps(data_json))
    resp = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    try:
        return json.loads(resp.choices[0].message.content)
    except Exception:
        return {"summary": resp.choices[0].message.content, "abnormalities": [], "recommendations": []}
