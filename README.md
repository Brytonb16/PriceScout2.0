# PriceScout

Fully deployable Flask app that now uses OpenAI for product search.

## Usage

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Set your OpenAI API key before starting the server:

```bash
export OPENAI_API_KEY="sk-your-key"
```

Start the development server:

```bash
python app.py

If the OpenAI request fails or returns no items, the backend will fall back to
scraping the partner sites so searches still surface results.
```
