
import json
from llm_client import client
from config import CONFIG
from logger import logger



# gonna create this service base on some tools.
class LLMService:
    def __init__(self, tools, system):
        self.system = system
        self.tools = tools

    def struct_llm_req(self, prs, role, tool_name, user_info):
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
                max_tokens=int(CONFIG.get('MXT')),
                tools=self.tools,
                system=self.system,
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
            logger.error(f"Error in struct_llm_req: {e}")
            return None
