from socketify import App
from config import CONFIG
from logger import logger
from handlers import Handlers
from llm_tools import tools
from llm_tools import llm_system


if __name__ == "__main__":
    app = App()
    handlers = Handlers('/tmp/xnoyabDb', tools, llm_system)
    app.post('/gdr', handlers.generate_diagnosis_report)
    app.post('/gfq', handlers.generate_followup_questions)
    app.post('/gq', handlers.generate_questions)
    app.post('/uui', handlers.upload_user_info)
    app.post('/stats', handlers.get_session_stats)
    app.post('/all_sessions', handlers.get_all_sessions)
    app.post('/delete_session', handlers.delete_session)
    app.listen(int(CONFIG['PORT']), lambda config: logger.info(f"Listening on port http://localhost:{int(CONFIG['PORT'])} now"))
    app.run()
