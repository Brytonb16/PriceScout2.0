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

Start the development server:

```bash
python app.py
```
