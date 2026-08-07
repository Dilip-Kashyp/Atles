import logging
from app.config import get_settings

log = logging.getLogger(__name__)

async def format_error(exc: Exception) -> str:
    exc_str = str(exc)
    settings = get_settings()

    try:
        from google import genai
        client = genai.Client(api_key=settings.gemini_api_key)

        prompt = (
            "You are a helpful AI bot. You just encountered this technical error while trying to help a user. Don't use any emoji's in the response."
            f"Explain to the user what went wrong in a natural, friendly, and non-technical way (1-2 sentences max). Error: {exc_str}"
        )

        resp = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
        )
        return resp.text or "I hit an unexpected snag."
    except Exception as fallback_exc:
        log.warning("[CHECKPOINT: RESPONSE_FORMATTER_FALLBACK] Small LLM failed to format error: %s", fallback_exc)
        if "429" in exc_str and "RESOURCE_EXHAUSTED" in exc_str:
            return "*Oops! I've run out of AI energy for now.* (My API quota is exhausted). Let me rest a bit, or please upgrade my API billing plan!"
        elif "401" in exc_str or "403" in exc_str:
            return "*I'm having trouble authenticating* with one of my tools. Please check my API keys in the server config."
        else:
            return "*I hit an unexpected snag while thinking.* (Check the server logs for the technical details)."

async def format_response(response: str) -> str:
    settings = get_settings()

    try:
        from google import genai
        client = genai.Client(api_key=settings.gemini_api_key)

        prompt = (
            "You are a helpful AI Slack bot. Reformat the following response so it is clean, "
            "uses appropriate Slack markdown (like *bold* or `code`), and sounds natural. "
            "Do not change the technical meaning or remove any important information. Don't use any emoji's in the response. "
            f"Response to format:\n\n{response}"
        )

        resp = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
        )
        return resp.text or response
    except Exception as exc:
        log.warning("[CHECKPOINT: RESPONSE_FORMATTER_FALLBACK] Small LLM failed to format response: %s", exc)
        return response
