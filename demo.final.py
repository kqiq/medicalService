import json
from anthropic import Anthropic, DefaultHttpxClient

client = Anthropic(
    api_key='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',
    http_client=DefaultHttpxClient(
        proxies="socks5://127.0.0.1:8888",
    ),
)

HEIKO = 'claude-3-haiku-20240307'

tools = [
    {
        "name": "generate_questions",
        "description": "Generates diagnostic questions based on the patient's root symptom. Should be used when the patient's root symptom is provided. in persian",
        "input_schema": {
            "type": "object",
            "properties": {
                "qs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": 'Array of questions related to the patient symptom for diagnosing it. Should be as specific as possible, and can overlap.in persian'
                },
            },
            "required": ["qs"]
        }
    },
    {
        "name": "generate_followup_questions",
        "description": "Generates follow-up questions based on the patient's answers to the initial diagnostic questions. Should be used to gather more detailed information. in persian",
        "input_schema": {
            "type": "object",
            "properties": {
                "followup_qs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": 'Array of follow-up questions related to the patient answers for gathering more detailed information. Should be as specific as possible, and can overlap.in persian'
                },
            },
            "required": ["followup_qs"]
        }
    },
    {
        "name": "diagnose",
        "description": "Generates a detailed diagnosis report based on the patient's answers to the diagnostic questions. This tool should be used to provide a comprehensive diagnosis report including detailed diagnosis, related categories, keywords, urgency level, suggested medication, and recommended expertise.always respond in persian",
        "input_schema": {
            "type": "object",
            "properties": {
                "diagnosis": {
                    "type": "string",
                    "description": "Detailed diagnosis of the user based on the provided data. in persian"
                },

                "differential": {
                    "type": "string",
                    "description": "Detailed Differential diagnosis of the user by the following definition : The differential diagnosis is a systematic process used to identify the most likely condition based on the patient's symptoms, medical history, physical examination, and diagnostic tests. It involves considering various possible conditions or diseases that could explain the patient's presentation. Further diagnostic testing or clinical observation may be required to narrow the list of potential diagnoses. in persian"
                },
                "category": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of categories related to the diagnosis. Should be as specific as possible. in perisan"
                },

                "keywords": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of keywords related to the current user state.in persian"
                },
                "user_urgent": {
                    "type": "string",
                    "description": "Urgency level of the user's condition. Possible values: 'ok', 'neutral', 'urgent'."
                },

                "medication": {
                    "type": "string",
                    "description": "Suggested medication or remedies to try to make the condition better. in persian"
                },
                "expertise": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of medical expertise or specialists that the patient should consult. in persian"
                }
            },
            "required": ["diagnosis","differential" ,  "category", "keywords", "user_urgent", "medication", "expertise"]
        }
    }
]

def structLLMReq(prs, role, tool_name, user_info):
    query = f"""
    Patient Information:
    Name: {user_info['name']}
    Gender: {user_info['gender']}
    Age: {user_info['age']}
    Root Symptom: {user_info['root_symptom']}

    Patient root problem:
    {prs}

    Use the `{tool_name}` tool.
    """

    response = client.messages.create(
        model=HEIKO,
        max_tokens=4096,
        tools=tools,
        system="You are an advanced and expert doctor capable of diagnosing a wide range of medical conditions. You have expertise in various fields of medicine including pharmacology, internal medicine, surgery, psychiatry, and other specialties. Always respond in Persian and provide detailed and attentive answers to user queries.", # <-- role prompt
        messages=[{"role": "user", "content": query}]
    )

    json_summary = None
    for content in response.content:
        if content.type == "tool_use" and content.name == tool_name:
            json_summary = content.input
            break

    if json_summary:
        return json.dumps(json_summary, indent=2)
    else:
        print(response.content)
        print("No JSON summary found in the response.")
        return json_summary

def main():
    # Step 1: Collect user input
    name = input("Enter your name: ")
    gender = input("Enter your gender: ")
    age = input("Enter your age: ")
    root_symptom = input("Describe your root symptom: ")

    user_info = {
        "name": name,
        "gender": gender,
        "age": age,
        "root_symptom": root_symptom
    }

    # Step 2: Generate diagnostic questions
    questions_json = structLLMReq(root_symptom, "generate_questions", "generate_questions", user_info)
    questions = json.loads(questions_json)["qs"]

    # Step 3: Collect user answers
    answers = {}
    for question in questions:
        answer = input(f"{question}: ")
        answers[question] = answer

    # Step 4: Generate follow-up questions
    answers_str = json.dumps(answers, indent=2)
    followup_questions_json = structLLMReq(answers_str, "generate_followup_questions", "generate_followup_questions", user_info)
    followup_questions = json.loads(followup_questions_json)["followup_qs"]

    # Step 5: Collect user answers to follow-up questions
    followup_answers = {}
    for followup_question in followup_questions:
        followup_answer = input(f"{followup_question}: ")
        followup_answers[followup_question] = followup_answer

    # Step 6: Generate diagnosis report
    all_answers = {**answers, **followup_answers}
    all_answers_str = json.dumps(all_answers, ensure_ascii=False,  indent=2)

    print(all_answers_str)

    diagnosis_json = structLLMReq(all_answers_str, "diagnose", "diagnose", user_info)
    diagnosis_report = json.loads(diagnosis_json)

    # Print the diagnosis report
    print("\nDiagnosis Report:")
    print(json.dumps(diagnosis_report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
