from app.llm_service import llm
from werkzeug.exceptions import InternalServerError, BadRequest
from flask import request, jsonify
from openai import OpenAI
import os

@llm.route("/get_llm_response", methods=["POST"])
def chatbot_response():
    try:
        data = request.get_json()
        if not data:
            raise BadRequest("Missing JSON Body")
        message = data['message']

        script_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(script_dir, "instructions.txt")
        with open(file_path, "r", encoding="utf-8") as file:
            instructions_string = file.read()
        client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key="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",
        )
        completion = client.chat.completions.create(
        model="meituan/longcat-flash-chat:free",
        messages=[
                {
                    "role": "user",
                    "content": f"[System Instructions] {instructions_string} ***** [User Query] {message}"
                }
                ]
        )
        raw_message = completion.choices[0].message.content
        plain_message = raw_message.replace("*", "")
        return jsonify({
            "message": plain_message
        }), 200
    except Exception as e:
        raise InternalServerError(description=f"Failed to fetch response: {e}")