import os
import google.generativeai as genai
from typing import List, Dict, Any

class GeminiGenerator:
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        api_key = os.environ.get("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
        else:
            print("[GeminiGenerator] WARNING: GEMINI_API_KEY not found in environment.")

    def generate_response(self, query: str, contexts: List[Dict[str, Any]]) -> str:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return "Error: GEMINI_API_KEY not configured on the server. Please add your Gemini API key to the .env file in the project root."

        # Format context text block
        context_str = ""
        for i, ctx in enumerate(contexts):
            context_str += f"\n--- Context Source: {ctx['metadata']['source']} ---\n{ctx['text']}\n"

        system_instruction = (
            "You are the Intelligent Student Assistant chatbot for Madanapalle Institute of Technology & Science (MITS) college. "
            "Your job is to answer the student's question accurately, professionally, and in a friendly manner. "
            "CRITICAL: Rely strictly on the context provided below. Do not use outside or generic knowledge. If the answer cannot be "
            "found in the provided context (or if the context is insufficient to answer the query), state that you do not have "
            "that information currently and politely guide them to check the official college website or contact the department. "
            "Do not fabricate facts, statistics, links, email addresses, names, or phone numbers. Avoid making assumptions or extrapolations. "
            "Format your answers clearly using bullet points, bold text, and proper markdown formatting."
        )

        prompt = f"""
{system_instruction}

[Context data]
{context_str}

[Student Question]
{query}

Please write your response below:
"""

        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"[GeminiGenerator] Error calling Gemini API: {e}")
            return f"Error: Unable to generate response due to Gemini API failure: {str(e)}"

    def generate_response_stream(self, query: str, contexts: List[Dict[str, Any]]):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            yield "Error: GEMINI_API_KEY not configured on the server."
            return

        context_str = ""
        for i, ctx in enumerate(contexts):
            context_str += f"\n--- Context Source: {ctx['metadata']['source']} ---\n{ctx['text']}\n"

        system_instruction = (
            "You are the Intelligent Student Assistant chatbot for Madanapalle Institute of Technology & Science (MITS) college. "
            "Your job is to answer the student's question accurately, professionally, and in a friendly manner. "
            "CRITICAL: Rely strictly on the context provided below. Do not use outside or generic knowledge. If the answer cannot be "
            "found in the provided context (or if the context is insufficient to answer the query), state that you do not have "
            "that information currently and politely guide them to check the official college website or contact the department. "
            "Do not fabricate facts, statistics, links, email addresses, names, or phone numbers. Avoid making assumptions or extrapolations. "
            "Format your answers clearly using bullet points, bold text, and proper markdown formatting."
        )

        prompt = f"""
{system_instruction}

[Context data]
{context_str}

[Student Question]
{query}

Please write your response below:
"""
        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt, stream=True)
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            print(f"[GeminiGenerator] Error calling Gemini API in streaming: {e}")
            yield f"Error: Streaming failed: {str(e)}"

