import json
import uuid
from anthropic import Anthropic, DefaultHttpxClient
from dotenv import dotenv_values
import dbm
from socketify import App

CONFIG = dotenv_values("../.env")

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
        "description": "Generates a detailed diagnosis report based on the patient's answers to the diagnostic questions. This tool should be used to provide a comprehensive diagnosis report including detailed diagnosis, related categories, keywords, urgency level, suggested medication, and recommended expertise. in persian",
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
            "required": ["diagnosis", "differential", "category", "keywords", "user_urgent", "medication", "expertise"]
        }
    }
]

# Open the dbm database
db = dbm.open('/tmp/xnoyabDb', 'c')

def structLLMReq(prs, role, tool_name, user_info):
    query = f"""
    Patient Information:
    Name: {user_info['name']}
    Gender: {user_info['gender']}
    Age: {user_info['age']}
    Root Symptom: {user_info['root_symptom']}

    Patient root problem:
    <problem>
    {prs}
    </problem>

    Use the `{tool_name}` tool.
    """

    response = client.messages.create(
        model=HEIKO,
        max_tokens=4096,
        tools=tools,
        system="You are an advanced and expert doctor capable of diagnosing a wide range of medical conditions. You have expertise in various fields of medicine including pharmacology, internal medicine, surgery, psychiatry, and other specialties. Always respond in Persian and provide detailed and attentive answers to user queries. ALWAYS RESPOND in persian", # <-- role prompt
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

# upload the user info  , name, gender , age
async def upload_user_info(res, req):
    data = await res.get_json()
    name = data.get("name")
    gender = data.get("gender")
    age = data.get("age")
    root_symptom = data.get("root_symptom")

    user_info = {
        "name": name,
        "gender": gender,
        "age": age,
        "root_symptom": root_symptom
    }

    # Generate a unique session ID
    session_id = str(uuid.uuid4())

    # Store user info in dbm database
    db[session_id] = json.dumps(user_info, ensure_ascii=False)

    # res.cork(lambda res: res.end(json.dumps({"session_id": session_id}, ensure_ascii=False)))

    res.cork(lambda res: res.write_header("Access-Control-Allow-Origin", "*")
                        .write_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                        .write_header("Access-Control-Allow-Headers", "Content-Type")
                        .end(json.dumps({"session_id": session_id}, ensure_ascii=False)))


# generate questions base on the current symp
async def generate_questions(res, req):
    data = await res.get_json()

    session_id = data.get("session_id")

    # Get user info from db
    user_info = json.loads(db[session_id])

    root_symptom = user_info.get("root_symptom")

    questions_json = structLLMReq(root_symptom, "generate_questions", "generate_questions", user_info)
    questions = json.loads(questions_json)["qs"]

    # Store generated questions in dbm database
    db[f"{session_id}_questions"] = json.dumps(questions, ensure_ascii=False)

    res.cork(lambda res: res.end(json.dumps({"questions": questions}, ensure_ascii=False)))

# generate following up questions base on previous questions.
async def generate_followup_questions(res, req):
    data = await res.get_json()
    session_id = data.get("session_id")
    answers = data.get("answers")

    # Store the user's answers in the database
    db[f"{session_id}_answers"] = json.dumps(answers, ensure_ascii=False)

    user_info = json.loads(db[session_id])

    answers_str = json.dumps(answers, indent=2)
    followup_questions_json = structLLMReq(answers_str, "generate_followup_questions", "generate_followup_questions", user_info)
    followup_questions = json.loads(followup_questions_json)["followup_qs"]

    # Store follow-up questions in dbm database
    db[f"{session_id}_followup_questions"] = json.dumps(followup_questions, ensure_ascii=False)

    res.cork(lambda res: res.end(json.dumps({"followup_questions": followup_questions}, ensure_ascii=False)))

# generate diagnosis report
async def generate_diagnosis_report(res, req):
    data = await res.get_json()
    session_id = data.get("session_id")
    followup_answers = data.get("followup_answers")

    # Retrieve initial answers from the database
    initial_answers = json.loads(db[f"{session_id}_answers"])

    # Combine initial and follow-up answers into a single dictionary
    all_answers = {**initial_answers, **followup_answers}

    print(all_answers);

    # Store all answers in the database
    db[f"{session_id}_all_answers"] = json.dumps(all_answers, ensure_ascii=False)

    user_info = json.loads(db[session_id])

    all_answers_str = json.dumps(all_answers, indent=2)
    diagnosis_json = structLLMReq(all_answers_str, "diagnose", "diagnose", user_info)
    diagnosis_report = json.loads(diagnosis_json)

    db[f"{session_id}_diagnosis_report"] = json.dumps(diagnosis_report, ensure_ascii=False)

    res.cork(lambda res: res.end(json.dumps(diagnosis_report, ensure_ascii=False)))

async def get_session_stats(res, req):
    data = await res.get_json()
    session_id = data.get("session_id")
    if not session_id:
        res.cork(lambda res: res.end(json.dumps({"error": "session_id is required"}, ensure_ascii=False)))
        return

    user_info = db.get(session_id.encode())
    questions = db.get(f"{session_id}_questions".encode())
    followup_questions = db.get(f"{session_id}_followup_questions".encode())
    diagnosis_report = db.get(f"{session_id}_diagnosis_report".encode())

    stats = {
        "user_info": json.loads(user_info) if user_info else None,
        "questions": json.loads(questions) if questions else None,
        "followup_questions": json.loads(followup_questions) if followup_questions else None,
        "diagnosis_report": json.loads(diagnosis_report) if diagnosis_report else None
    }

    res.cork(lambda res: res.end(json.dumps(stats, ensure_ascii=False)))




# this also for swagger types of stuffs.
# async def serve_openapi_spec(res, req):
#     with open("./swagger.json", "r") as file:
#         content = file.read()
#         res.cork(lambda res: res.write_header("Access-Control-Allow-Origin", "*")
#                             .write_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
#                             .write_header("Access-Control-Allow-Headers", "Content-Type")
#                             .end(content, "content-type/json"))


if __name__ == "__main__":
    app = App()

    # generate_diagnosis_report
    app.post('/gdr', generate_diagnosis_report)

    # generate_followup_questions
    app.post('/gfq', generate_followup_questions)

    # generate_questions
    app.post('/gq', generate_questions)

    # upload user info
    app.post('/uui', upload_user_info)

    # upload user info
    app.post('/stats', get_session_stats)

    # this is fro the swagger types of stuffs.
    # # serve openapi.yaml
    # app.get('/swagger', serve_openapi_spec)

    app.listen(int(CONFIG['PORT']), lambda config: print(f"Listening on port http://localhost:{int(CONFIG['PORT'])} now\n"))

    app.run()
