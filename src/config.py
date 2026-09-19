import os

from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI


load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")
GROQ_TOKEN = os.getenv("GROQ_API_KEY")
ENDPOINT = "https://models.github.ai/inference"
MODEL_NAME = "openai/o4-mini"
GROQ_MODEL_NAME = "openai/gpt-oss-120b"


def get_model_config(provider):
    provider_name = provider.lower().strip()

    if provider_name == "groq":
        if not GROQ_TOKEN:
            raise RuntimeError(
                "Falta GROQ_API_KEY en el entorno. Define la variable en tu archivo .env."
            )
        return {
            "provider": "groq",
            "model_name": GROQ_MODEL_NAME,
            "client": Groq(api_key=GROQ_TOKEN),
        }

    if not TOKEN:
        raise RuntimeError(
            "Falta GITHUB_TOKEN en el entorno. Define la variable en tu archivo .env."
        )
    return {
        "provider": "githubmodel",
        "model_name": MODEL_NAME,
        "client": OpenAI(base_url=ENDPOINT, api_key=TOKEN),
    }