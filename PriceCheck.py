import os
import sqlite3
import requests

# --- Configuration ---
# Get a free API client ID from platform.seatgeek.com
SEATGEEK_CLIENT_ID = os.getenv("SEATGEEK_CLIENT_ID")

# Simply add any artists you want to track to this list
TRACKED_ARTISTS = [
    "katseye",
    "sabrina carpenter",
    "chappell roan",
    "billie eilish"
]
CITY = "boston"

# Webhook to send notifications (Discord, Slack, or Twilio for SMS)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DB_FILE = "ticket_monitor.db"


def init_db():
    """Initializes a local database to store lowest tracked prices by unique event ID."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS price_tracker (
            event_id TEXT PRIMARY KEY,
            artist TEXT,
            venue TEXT,
            lowest_recorded_price REAL
        )
    """
    )
    conn.commit()
    conn.close()


def get_current_lowest_price(artist_name):
    """Fetches the current cheapest ticket for a specific artist from the SeatGeek API."""
    url = "https://seatgeek.com"
    params = {
        "q": f"{artist_name} {CITY}",
        "client_id": os.getenv("SEATGEEK_CLIENT_ID"),
        "per_page": 1,
    }

    try:
        response = requests.get(url, params=params).json()
        if not response.get("events"):
            print(f"No matching events found for {artist_name}.")
            return None

        event = response["events"][0]
        event_id = event["id"]
        venue = event["venue"]["name"]

        # 'lowest_price' field gives the cheapest available ticket before checkout
        current_low = event["stats"].get("lowest_price")

        return {
            "id": str(event_id),
            "artist": artist_name,
            "venue": venue,
            "price": float(current_low) if current_low else None,
            "url": event["url"],
        }
    except Exception as e:
        print(f"Error fetching data from API for {artist_name}: {e}")
        return None


def check_and_alert(event_data):
    """Compares current price to database and alerts if it's an all-time low."""
    if not event_data or event_data["price"] is None:
        return

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Check what the previous lowest recorded price was
    cursor.execute(
        "SELECT lowest_recorded_price FROM price_tracker WHERE event_id = ?",
        (event_data["id"],),
    )
    row = cursor.fetchone()

    artist_display = event_data["artist"].upper()

    if row is None:
        # First time tracking this event, save the current price as the baseline
        cursor.execute(
            "INSERT INTO price_tracker VALUES (?, ?, ?, ?)",
            (
                event_data["id"],
                event_data["artist"],
                event_data["venue"],
                event_data["price"],
            ),
        )
        conn.commit()
        print(f"Started tracking {artist_display}. Baseline low set to ${event_data['price']}.")
    else:
        historical_low = row[0]

        # If current price is strictly cheaper than the historical low, trigger alert
        if event_data["price"] < historical_low:
            send_alert(event_data, historical_low)

            # Update the database with the new all-time low
            cursor.execute(
                "UPDATE price_tracker SET lowest_recorded_price = ? WHERE event_id = ?",
                (event_data["price"], event_data["id"]),
            )
            conn.commit()
            print(f"New all-time low recorded for {artist_display}: ${event_data['price']}")
        else:
            print(
                f"Current price for {artist_display} (${event_data['price']}) is higher than all-time low (${historical_low})."
            )

    conn.close()


def send_alert(event, old_low):
    """Sends a notification payload to a Discord channel."""
    payload = {
        "content": (
            f"🚨 **ALL-TIME CHEAP TICKET ALERT!** 🚨\n"
            f"Tickets for **{event['artist'].upper()}** at {event['venue']} just dropped!\n"
            f"📉 Previous Low: ${old_low:.2f}\n"
            f"🔥 **New All-Time Low: ${event['price']:.2f}**\n"
            f"👉 Buy Tickets Here: {event['url']}"
        )
    }
    requests.post(DISCORD_WEBHOOK_URL, json=payload)


if __name__ == "__main__":
    init_db()
    print("🤖 Launching multi-artist price tracker...")
    
    # Iterate through every artist configured in the tracking array
    for artist in TRACKED_ARTISTS:
        current_listings = get_current_lowest_price(artist)
        check_and_alert(current_listings)
        
    print("🏁 Track routine finished.")
