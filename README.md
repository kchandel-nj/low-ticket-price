# low-ticket-price

This program constantly monitors ticket prices for given artists and alerts when they reach an all-time low.

## Current Application Behavior

When executed, the program runs a sequential automation cycle across all configured performers. Here is exactly what happens step-by-step:

### 1. Database Initialization
* The program establishes a local SQLite database connection (`ticket_monitor.db`).
* It automatically builds a tracking table keyed by unique `event_id` structures if it doesn't already exist. This ensures it maps price histories cleanly to specific concert dates.

### 2. Multi-Artist Query Cycle
The script iterates directly through the defined `TRACKED_ARTISTS` collection. For each artist, it performs the following tasks:
* **API Ingestion:** Sends an authenticated request to the SeatGeek API filtering by the target artist name and defined global city constraint.
* **Extraction:** Parses the response payload to isolate the specific event metadata: venue name, event platform URL, and the core baseline property `lowest_price` (the absolute lowest ticket threshold currently listed on the marketplace).

### 3. Comparison Logic & Threshold Evaluations
Once data is retrieved for an event, the state is compared against the database records:
* **Scenario A (First Run / New Event):** If the `event_id` is missing from the database, it inserts a new row. The current price is saved as the initial benchmark baseline.
* **Scenario B (No Price Improvement):** If the current marketplace minimum price is equal to or higher than the stored historical minimum, the script skips alerting and logs the status to the local console.
* **Scenario C (Price Drop Detected):** If the marketplace minimum falls strictly **below** the stored historical minimum, it updates the database row with the new deal value and shifts to the notification phase.

### 4. Alert Routing
* When a price drop triggers Scenario C, the script constructs a formatted JSON payload.
* It dispatches an immediate `POST` request to the configured Discord or Slack incoming Webhook URL.
* The outgoing alert includes the artist's name, the venue name, the previous low benchmark, the new pricing deal, and a direct clickable URL so you can jump straight to the ticket listings.
