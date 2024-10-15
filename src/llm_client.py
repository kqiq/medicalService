# handle the llm client stuffs : gonna create anthropic key..
from anthropic import Anthropic, DefaultHttpxClient
from config import CONFIG

client = Anthropic(
    api_key=CONFIG.get('MODEL_API'),
    http_client=DefaultHttpxClient(
        proxies=CONFIG.get('PROXY_URL'),
    ),
)
