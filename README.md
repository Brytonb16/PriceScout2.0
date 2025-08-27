# PriceScout

Fully deployable with Flask, Playwright, scrapers, and working UI.

## Usage

Install the required dependencies and Playwright browsers:

```bash
pip install -r requirements.txt
playwright install --with-deps chromium
```

If deploying to a service like Render, ensure the Playwright browsers are
installed during the build step so the scrapers can launch Chromium.

If the browser cannot be installed or Playwright fails at runtime, the
scrapers will automatically fall back to a standard HTTP request so results are
still returned whenever possible.

Start the development server:

```bash
python app.py
```
