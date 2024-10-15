
import json
import uuid
from logger import logger
from db import Database
from llm_service import LLMService

class Handlers:
    def __init__(self, db_path, tools, system):
        self.db = Database(db_path)
        self.llm_service = LLMService(tools, system)

    async def upload_user_info(self, res, req):

        try:
            data = await res.get_json()
            gender = data.get("gender")
            age = data.get("age")
            root_symptom = data.get("root_symptom")
            id = data.get('id');

            if not all([gender, age, root_symptom]):
                res.cork(lambda res: res.end(json.dumps({"error": "All fields are required"}, ensure_ascii=False)))
                return

            user_info = {
                "gender": gender,
                "age": age,
                "root_symptom": root_symptom
            }

            # you can get the id by parsing it ID-:
            session_id = f"{str(uuid.uuid4())}-ID-:{str(id)}"
            self.db.set(session_id, user_info)

            res.cork(lambda res: res.write_header("Access-Control-Allow-Origin", "*")
                                .write_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                                .write_header("Access-Control-Allow-Headers", "Content-Type")
                                .end(json.dumps({"session_id": session_id}, ensure_ascii=False)))
        except Exception as e:
            logger.error(f"Error in upload_user_info: {e}")
            res.cork(lambda res: res.end(json.dumps({
                "error": "Something went wrong. Please ensure your data is in the following format: { \"gender\":\"male|string\", \"age\":26|int, \"root_symptom\":\"i have a headache|string\", \"id\":12345|int|string}"
            }, ensure_ascii=False)))

    async def generate_questions(self, res, req):
        try:
            data = await res.get_json()
            session_id = data.get("session_id")

            if not session_id:
                res.cork(lambda res: res.end(json.dumps({"error": "session_id is required"}, ensure_ascii=False)))
                return

            user_info = self.db.get(session_id)
            root_symptom = user_info.get("root_symptom")

            questions_json = self.llm_service.struct_llm_req(root_symptom, "generate_questions", "generate_questions", user_info)
            if not questions_json:
                res.cork(lambda res: res.end(json.dumps({"error": "Failed to generate questions"}, ensure_ascii=False)))
                return

            questions = json.loads(questions_json)["qs"]
            self.db.set(f"{session_id}_questions", questions)

            res.cork(lambda res: res.end(json.dumps({"questions": questions}, ensure_ascii=False)))
        except Exception as e:
            logger.error(f"Error in generate_questions: {e}")
            #res.cork(lambda res: res.end(json.dumps({"error": "Internal server error"}, ensure_ascii=False)))

            res.cork(lambda res: res.end(json.dumps({
                "error": "Something went wrong. Please ensure your data is in the following format: { \"session_id\":\"hash|string\"}"
            }, ensure_ascii=False)))

    async def generate_followup_questions(self, res, req):
        try:
            data = await res.get_json()
            session_id = data.get("session_id")
            answers = data.get("answers")

            if not session_id or not answers:
                res.cork(lambda res: res.end(json.dumps({"error": "session_id and answers are required"}, ensure_ascii=False)))
                return

            self.db.set(f"{session_id}_answers", answers)
            user_info = self.db.get(session_id)

            answers_str = json.dumps(answers, indent=2)
            followup_questions_json = self.llm_service.struct_llm_req(answers_str, "generate_followup_questions", "generate_followup_questions", user_info)
            if not followup_questions_json:
                res.cork(lambda res: res.end(json.dumps({"error": "Failed to generate follow-up questions"}, ensure_ascii=False)))
                return

            followup_questions = json.loads(followup_questions_json)["followup_qs"]
            self.db.set(f"{session_id}_followup_questions", followup_questions)

            res.cork(lambda res: res.end(json.dumps({"followup_questions": followup_questions}, ensure_ascii=False)))
        except Exception as e:
            logger.error(f"Error in generate_followup_questions: {e}")
            #res.cork(lambda res: res.end(json.dumps({"error": "Internal server error"}, ensure_ascii=False)))

            res.cork(lambda res: res.end(json.dumps({
                "error": "Something went wrong. Please ensure your data is in the following format: { \"session_id\": \"hash|string\", \"answers\": { \"Question 1\": \"Answer 1|string\", \"Question 2\": \"Answer 2|string\" } }"
            }, ensure_ascii=False)))

    async def generate_diagnosis_report(self, res, req):
        try:
            data = await res.get_json()
            session_id = data.get("session_id")
            followup_answers = data.get("followup_answers")

            if not session_id or not followup_answers:
                res.cork(lambda res: res.end(json.dumps({"error": "session_id and followup_answers are required"}, ensure_ascii=False)))
                return

            initial_answers = self.db.get(f"{session_id}_answers")
            all_answers = {**initial_answers, **followup_answers}
            self.db.set(f"{session_id}_all_answers", all_answers)

            user_info = self.db.get(session_id)
            all_answers_str = json.dumps(all_answers, indent=2)
            diagnosis_json = self.llm_service.struct_llm_req(all_answers_str, "diagnose", "diagnose", user_info)
            if not diagnosis_json:
                res.cork(lambda res: res.end(json.dumps({"error": "Failed to generate diagnosis report"}, ensure_ascii=False)))
                return

            diagnosis_report = json.loads(diagnosis_json)
            self.db.set(f"{session_id}_diagnosis_report", diagnosis_report)

            res.cork(lambda res: res.end(json.dumps(diagnosis_report, ensure_ascii=False)))
        except Exception as e:
            logger.error(f"Error in generate_diagnosis_report: {e}")

            res.cork(lambda res: res.end(json.dumps({
                "error": "Something went wrong. Please ensure your data is in the following format: { \"session_id\": \"hash|string\", \"answers\": { \"Follow-up Question 1|string\": \"Answer 1|string\", \"Follow-up Question 2\": \"Answer 2|string\" } }"
            }, ensure_ascii=False)))

    async def get_session_stats(self, res, req):
        try:
            data = await res.get_json()
            session_id = data.get("session_id")

            if not session_id:
                res.cork(lambda res: res.end(json.dumps({"error": "session_id is required"}, ensure_ascii=False)))
                return

            user_info = self.db.get(session_id)
            questions = self.db.get(f"{session_id}_questions")
            followup_questions = self.db.get(f"{session_id}_followup_questions")
            diagnosis_report = self.db.get(f"{session_id}_diagnosis_report")

            stats = {
                "user_info": user_info,
                "questions": questions,
                "followup_questions": followup_questions,
                "diagnosis_report": diagnosis_report
            }

            res.cork(lambda res: res.end(json.dumps(stats, ensure_ascii=False)))
        except Exception as e:
            logger.error(f"Error in get_session_stats: {e}")

            res.cork(lambda res: res.end(json.dumps({
                "error": "Something went wrong. Please ensure your data is in the following format: { \"session_id\":\"hash|string\"}"
            }, ensure_ascii=False)))



    async def delete_session(self, res, req):
        try:
            data = await res.get_json()
            session_id = data.get("session_id")

            if not session_id:
                res.cork(lambda res: res.end(json.dumps({"error": "session_id is required"}, ensure_ascii=False)))
                return

            self.db.delete(session_id)
            self.db.delete(f"{session_id}_questions")
            self.db.delete(f"{session_id}_answers")
            self.db.delete(f"{session_id}_followup_questions")
            self.db.delete(f"{session_id}_all_answers")
            self.db.delete(f"{session_id}_diagnosis_report")

            res.cork(lambda res: res.end(json.dumps({"message": "Session deleted successfully"}, ensure_ascii=False)))
        except Exception as e:
            logger.error(f"Error in delete_session: {e}")


            res.cork(lambda res: res.end(json.dumps({
                "error": "Something went wrong. Please ensure your data is in the following format: { \"session_id\":\"hash|string\"}"
            }, ensure_ascii=False)))

    # empty in supply
    async def get_all_sessions(self, res, req):
        try:
            all_sessions = self.db.get_all_keys()
            res.cork(lambda res: res.end(json.dumps({"sessions": all_sessions}, ensure_ascii=False)))
        except Exception as e:
            logger.error(f"Error in get_all_sessions: {e}")
            res.cork(lambda res: res.end(json.dumps({"error": "Internal server error"}, ensure_ascii=False)))
