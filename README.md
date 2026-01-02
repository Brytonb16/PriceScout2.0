# Repair Parts Scout

An AI-powered Flask app that hunts down repair and replacement parts across suppliers and surfaces the best-priced options first.

## Quick start

1. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```
2. Export your OpenAI credentials (any compatible chat model is supported via `OPENAI_MODEL`)
   ```bash
   export OPENAI_API_KEY="sk-your-key"
   export OPENAI_MODEL="gpt-4o-mini"  # optional override
   ```
3. Run the server
   ```bash
   python app.py
   ```

Open http://localhost:5000 and enter a part name (for example, “iPhone 13 screen replacement kit”). A built-in offline catalog returns realistic offers instantly (handy for demos and CI), automatically sorted by price and annotated with a “Best price” badge. To enable live scraping from vendors, export `ENABLE_REMOTE_SCRAPERS=true` before starting the server.
