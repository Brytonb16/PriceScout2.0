import json
import os
import openai

openai.api_key = os.environ.get("OPENAI_API_KEY")
MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

PROMPT_TEMPLATE = (
    "You help technicians find replacement and repair parts. "
    "Return a JSON array of 6-10 offers for the search '{query}'. "
    "Each item must include: title, price (as a number), in_stock (boolean), "
    "source (store name), link (product URL), and image (product photo). "
    "Prioritize MobileSentrix, Amazon, and Ebay listings whenever available, "
    "avoid accessories, and sort items by price from lowest to highest so the "
    "best deals appear first."
)


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
