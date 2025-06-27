# monkeytype-saver

A frontend/backend to fetch and save your new Monkeytype typing test results every day.

## Overview

**monkeytype-saver** is a Python-based project that automates the retrieval and storage of your Monkeytype typing test results, then provides a web dashboard to visualize your performance over time. It consists of:
- **Backend:** Periodically fetches Monkeytype results using your API key and saves them locally.
- **Frontend:** A Dash app to visualize your WPM, accuracy, averages, and personal bests.

## Features

- Automatically fetches and updates your Monkeytype typing test results at a configurable interval.
- Stores results in a local JSON file (`monkeytype_results.json`).
- Interactive dashboard to visualize:
  - Speed (WPM) per test
  - Averages across the last 10 and 100 tests
  - Personal best progression
  - Support for multiple languages
- Customizable themes and layout.

## Requirements

### Backend
- Python 3.8+
- `requests` (see `requirements_backend.txt`)

### Frontend
- Python 3.8+
- `dash`, `pandas`, `plotly`, `requests` (see `requirements_frontend.txt`)

## Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Monnandre/monkeytype-saver.git
   cd monkeytype-saver
   ```

2. **Install dependencies**

   For the backend:
   ```bash
   pip install -r requirements_backend.txt
   ```

   For the frontend:
   ```bash
   pip install -r requirements_frontend.txt
   ```

## Usage

### 1. Set up your Monkeytype API Key

- Obtain your `ApeKey` from Monkeytype's API.
- Set it as an environment variable:
  ```bash
  export MONKEYTYPE_APE_KEY="your_apekey_here"
  ```

- (Optional) Change how many times per day to fetch results:
  ```bash
  export UPDATES_PER_DAY=2  # Fetches twice per day
  ```

### 2. Run the backend fetcher

This will start fetching and saving your results in `monkeytype_results.json`:

```bash
python backend.py
```

### 3. Run the dashboard

In a new terminal (ensure `monkeytype_results.json` exists):

```bash
python frontend.py
```

- Open your browser and go to [http://localhost:8050](http://localhost:8050) to view your stats.

## Docker Compose Setup

You can run both backend and frontend with Docker Compose. Replace the placeholder paths with your actual directories as needed.

```yaml
services:
  monkeytype-frontend:
    build:
      context: /host/docker-services/monkeytypestats # <-- Replace with your actual path
      dockerfile: Dockerfile_frontend
    container_name: monkeytype-ui
    volumes:
      - /home/alex/docker-services/monkeytypestats:/app # <-- Replace with your actual path
    restart: unless-stopped
    ports:
      - "8050:8050"

  monkeytype-backend:
    build:
      context: /host/docker-services/monkeytypestats # <-- Replace with your actual path
      dockerfile: Dockerfile_backend
    container_name: monkeytype-fetcher
    environment:
      - UPDATES_PER_DAY=${UPDATES_PER_DAY}
      - MONKEYTYPE_APE_KEY=${MONKEYTYPE_APE_KEY}
    volumes:
      - /home/alex/docker-services/monkeytypestats:/app # <-- Replace with your actual path
    restart: unless-stopped
```

**Environment Variables Needed:**
- `MONKEYTYPE_APE_KEY` - Your Monkeytype API key
- `UPDATES_PER_DAY` - (optional) How many times per day to fetch results

## File Structure

- `backend.py` — Script to fetch and update your Monkeytype results.
- `frontend.py` — Dash app for visualizing your stats.
- `monkeytype_results.json` — Saved results (created/updated automatically).
- `requirements_backend.txt` — Backend dependencies.
- `requirements_frontend.txt` — Frontend dependencies.

## Notes

- The backend fetcher runs in an infinite loop. Use `Ctrl+C` to stop it.
- If you want to reset your data, delete `monkeytype_results.json`.

## License

*No license specified yet.*

---

*Project by [Monnandre](https://github.com/Monnandre)*
