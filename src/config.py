import os

from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI


load_dotenv()

TOKEN = os.getenv("GITHUB_TOKEN")
GROQ_TOKEN = os.getenv("GROQ_API_KEY")
ENDPOINT = "https://models.github.ai/inference"
MODEL_NAME = "openai/o4-mini"
GROQ_MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"


def get_model_config(provider):
    provider_name = provider.lower().strip()

    if provider_name == "groq":
        return {
            "provider": "groq",
            "model_name": GROQ_MODEL_NAME,
            "client": Groq(api_key=GROQ_TOKEN),
        }

    return {
        "provider": "githubmodel",
        "model_name": MODEL_NAME,
        "client": OpenAI(base_url=ENDPOINT, api_key=TOKEN),
    }