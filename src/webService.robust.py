# libs
import json
import uuid
import logging
from anthropic import Anthropic, DefaultHttpxClient
from dotenv import dotenv_values
import dbm
from socketify import App

# Load configuration
CONFIG = dotenv_values("../.env")

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Anthropic client by env values
client = Anthropic(
    api_key=CONFIG.get('MODEL_API_KEY'),
    http_client=DefaultHttpxClient(
        proxies=CONFIG.get('PROXY_URL'),
    ),
)



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

# llm interface
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

    try:
        response = client.messages.create(
            model=CONFIG.get('MODEL_NAME'),
            max_tokens=CONFIG.get('MXT'),
            tools=tools,
            system="You are an advanced and expert doctor capable of diagnosing a wide range of medical conditions. You have expertise in various fields of medicine including pharmacology, internal medicine, surgery, psychiatry, and other specialties. Always respond in Persian and provide detailed and attentive answers to user queries. ALWAYS RESPOND in persian",
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
            logger.error("No JSON summary found in the response.")
            return None
    except Exception as e:
        logger.error(f"Error in structLLMReq: {e}")
        return None

# first trigger of the api
async def upload_user_info(res, req):
    try:
        data = await res.get_json()
        name = data.get("name")
        gender = data.get("gender")
        age = data.get("age")
        root_symptom = data.get("root_symptom")

        if not all([name, gender, age, root_symptom]):
            res.cork(lambda res: res.end(json.dumps({"error": "All fields are required"}, ensure_ascii=False)))
            return

        user_info = {
            "name": name,
            "gender": gender,
            "age": age,
            "root_symptom": root_symptom
        }

        session_id = str(uuid.uuid4())
        db[session_id] = json.dumps(user_info, ensure_ascii=False)

        res.cork(lambda res: res.write_header("Access-Control-Allow-Origin", "*")
                            .write_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                            .write_header("Access-Control-Allow-Headers", "Content-Type")
                            .end(json.dumps({"session_id": session_id}, ensure_ascii=False)))
    except Exception as e:
        logger.error(f"Error in upload_user_info: {e}")
        res.cork(lambda res: res.end(json.dumps({"error": "Internal server error"}, ensure_ascii=False)))

# genereate questions -> works with session id -> must call with some session_id payload
async def generate_questions(res, req):
    try:
        data = await res.get_json()
        session_id = data.get("session_id")

        if not session_id:
            res.cork(lambda res: res.end(json.dumps({"error": "session_id is required"}, ensure_ascii=False)))
            return

        user_info = json.loads(db[session_id])
        root_symptom = user_info.get("root_symptom")

        questions_json = structLLMReq(root_symptom, "generate_questions", "generate_questions", user_info)
        if not questions_json:
            res.cork(lambda res: res.end(json.dumps({"error": "Failed to generate questions"}, ensure_ascii=False)))
            return

        questions = json.loads(questions_json)["qs"]
        db[f"{session_id}_questions"] = json.dumps(questions, ensure_ascii=False)

        res.cork(lambda res: res.end(json.dumps({"questions": questions}, ensure_ascii=False)))
    except Exception as e:
        logger.error(f"Error in generate_questions: {e}")
        res.cork(lambda res: res.end(json.dumps({"error": "Internal server error"}, ensure_ascii=False)))

# generate followup questions -> better to call after generate questions.
async def generate_followup_questions(res, req):
    try:
        data = await res.get_json()
        session_id = data.get("session_id")
        answers = data.get("answers")

        if not session_id or not answers:
            res.cork(lambda res: res.end(json.dumps({"error": "session_id and answers are required"}, ensure_ascii=False)))
            return

        db[f"{session_id}_answers"] = json.dumps(answers, ensure_ascii=False)
        user_info = json.loads(db[session_id])

        answers_str = json.dumps(answers, indent=2)
        followup_questions_json = structLLMReq(answers_str, "generate_followup_questions", "generate_followup_questions", user_info)
        if not followup_questions_json:
            res.cork(lambda res: res.end(json.dumps({"error": "Failed to generate follow-up questions"}, ensure_ascii=False)))
            return

        followup_questions = json.loads(followup_questions_json)["followup_qs"]
        db[f"{session_id}_followup_questions"] = json.dumps(followup_questions, ensure_ascii=False)

        res.cork(lambda res: res.end(json.dumps({"followup_questions": followup_questions}, ensure_ascii=False)))
    except Exception as e:
        logger.error(f"Error in generate_followup_questions: {e}")
        res.cork(lambda res: res.end(json.dumps({"error": "Internal server error"}, ensure_ascii=False)))

# generate diagnosis report  -> better to call after followups
async def generate_diagnosis_report(res, req):
    try:
        data = await res.get_json()
        session_id = data.get("session_id")
        followup_answers = data.get("followup_answers")

        if not session_id or not followup_answers:
            res.cork(lambda res: res.end(json.dumps({"error": "session_id and followup_answers are required"}, ensure_ascii=False)))
            return

        initial_answers = json.loads(db[f"{session_id}_answers"])
        all_answers = {**initial_answers, **followup_answers}
        db[f"{session_id}_all_answers"] = json.dumps(all_answers, ensure_ascii=False)

        user_info = json.loads(db[session_id])
        all_answers_str = json.dumps(all_answers, indent=2)
        diagnosis_json = structLLMReq(all_answers_str, "diagnose", "diagnose", user_info)
        if not diagnosis_json:
            res.cork(lambda res: res.end(json.dumps({"error": "Failed to generate diagnosis report"}, ensure_ascii=False)))
            return

        diagnosis_report = json.loads(diagnosis_json)
        db[f"{session_id}_diagnosis_report"] = json.dumps(diagnosis_report, ensure_ascii=False)

        res.cork(lambda res: res.end(json.dumps(diagnosis_report, ensure_ascii=False)))
    except Exception as e:
        logger.error(f"Error in generate_diagnosis_report: {e}")
        res.cork(lambda res: res.end(json.dumps({"error": "Internal server error"}, ensure_ascii=False)))

# get session data py payloding some stat
async def get_session_stats(res, req):
    try:
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
    except Exception as e:
        logger.error(f"Error in get_session_stats: {e}")
        res.cork(lambda res: res.end(json.dumps({"error": "Internal server error"}, ensure_ascii=False)))

if __name__ == "__main__":
    app = App()

    app.post('/gdr', generate_diagnosis_report)
    app.post('/gfq', generate_followup_questions)
    app.post('/gq', generate_questions)
    app.post('/uui', upload_user_info)
    app.post('/stats', get_session_stats)

    app.listen(int(CONFIG['PORT']), lambda config: logger.info(f"Listening on port http://localhost:{int(CONFIG['PORT'])} now"))

    app.run()
