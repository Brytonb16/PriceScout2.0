import json
import os
import openai

openai.api_key = os.environ.get("OPENAI_API_KEY")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

PROMPT_TEMPLATE = (
    "Provide a JSON array of product search results for the query '{query}'. "
    "Each item should have title, price, in_stock, source, link, and image." )


def search_openai(query: str):
    """Use OpenAI to generate product search results for *query*.

    The function expects the model to return a JSON array formatted as
    described in ``PROMPT_TEMPLATE``. If parsing fails, an empty list is
    returned.
    """
    prompt = PROMPT_TEMPLATE.format(query=query)
    try:
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a helpful product search engine."},
                {"role": "user", "content": prompt},
            ],
        )
        content = response["choices"][0]["message"]["content"]
        return json.loads(content)
    except Exception:
        return []
