import os
import json
import re
from typing import Dict, Any, Tuple
import openai
from dotenv import load_dotenv

load_dotenv()

CIRCUIT_BREAKER = False

def extract_json(text: str) -> Dict[str, Any]:
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text.strip())
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
        
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        candidate = text[start:end+1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
            
    raise ValueError("Failed to parse JSON")

def call_llm(messages: list, model: str, retry: bool = True) -> Dict[str, Any]:
    global CIRCUIT_BREAKER
    
    provider = os.getenv("LLM_PROVIDER", "replay")
    if CIRCUIT_BREAKER or provider == "replay":
        return {"error_code": "NOT_RECORDED", "success": False, "error_message": "Replay mode and cache miss", "retryable": False}
        
    client = openai.OpenAI(timeout=1.5)
    
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        content = resp.choices[0].message.content
        usage = resp.usage
        
        parsed = extract_json(content)
        return {
            "success": True,
            "response": parsed,
            "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens
            },
            "provider": provider
        }
    except Exception as e:
        if retry:
            return call_llm(messages, model, retry=False)
        CIRCUIT_BREAKER = True
        return {"success": False, "error_code": "LIVE_CALL_FAILED", "error_message": str(e), "retryable": False}
