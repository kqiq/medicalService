# define the tools used by the llm
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

llm_system ="You are an advanced and expert doctor capable of diagnosing a wide range of medical conditions. You have expertise in various fields of medicine including pharmacology, internal medicine, surgery, psychiatry, and other specialties. Always respond in Persian and provide detailed and attentive answers to user queries. ALWAYS RESPOND in persian"

mxt = 4098
