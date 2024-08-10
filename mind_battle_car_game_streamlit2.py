import streamlit as st
import time
import numpy as np
import pandas as pd
from PIL import Image
import base64
import io
import os
from rdoclient import RandomOrgClient

MAX_BATCH_SIZE = 1000  # Maximum batch size for requests to random.org
RETRY_LIMIT = 3  # Number of retry attempts for random.org requests
REQUEST_INTERVAL = 0.5  # Interval between requests (in seconds)

def configure_random_org(api_key):
    """Configure the RANDOM.ORG client if the API key is valid."""
    try:
        client = RandomOrgClient(api_key)
        return client
    except Exception as e:
        st.error(f"Error configuring the random.org client: {e}")
        return None

def get_random_bits_from_random_org(num_bits, client=None):
    """Get random bits from random.org or use a local pseudorandom generator."""
    try:
        if client:
            # Use RANDOM.ORG
            random_bits = client.generate_integers(num_bits, 0, 1)
            return random_bits, True
        else:
            # Use a local pseudorandom generator
            random_bits = get_local_random_bits(num_bits)
            return random_bits, False
    except Exception:
        # In case of error, use a local pseudorandom generator
        random_bits = get_local_random_bits(num_bits)
        return random_bits, False

def get_local_random_bits(num_bits):
    """Generate pseudorandom bits locally."""
    return list(np.random.randint(0, 2, size=num_bits))

def calculate_entropy(bits):
    """Calculate entropy using Shannon's formula."""
    n = len(bits)
    counts = np.bincount(bits, minlength=2)
    p = counts / n
    p = p[np.nonzero(p)]
    entropy = -np.sum(p * np.log2(p))
    return entropy

def move_car(car_pos, distance):
    """Move the car a certain distance."""
    car_pos += distance
    if car_pos > 900:  # Shorten the track to leave room for the flag
        car_pos = 900
    return car_pos

def image_to_base64(image):
    """Convert an image to base64."""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def reset_game():
    """Reset the game state."""
    st.session_state.car_pos = 50
    st.session_state.car2_pos = 50
    st.session_state.car1_moves = 0
    st.session_state.car2_moves = 0
    st.session_state.data_for_excel_1 = []
    st.session_state.data_for_excel_2 = []
    st.session_state.data_for_condition_1 = []
    st.session_state.data_for_condition_2 = []
    st.session_state.random_numbers_1 = []
    st.session_state.random_numbers_2 = []
    st.session_state.widget_key_counter += 1
    st.session_state.player_choice = None
    st.session_state.running = False
    st.session_state.show_end_buttons = False
    st.write(reset_game_message)
    display_cars()

def main():
    st.set_page_config(page_title="Car Mind Race", layout="wide")

    if "language" not in st.session_state:
        st.session_state.language = "Italiano"

    if "api_key" not in st.session_state:
        st.session_state.api_key = ""

    if "warned_random_org" not in st.session_state:
        st.session_state.warned_random_org = False

    if "player_choice" not in st.session_state:
        st.session_state.player_choice = None

    if "car_pos" not in st.session_state:
        st.session_state.car_pos = 50

    if "car2_pos" not in st.session_state:
        st.session_state.car2_pos = 50

    if "car1_moves" not in st.session_state:
        st.session_state.car1_moves = 0

    if "car2_moves" not in st.session_state:
        st.session_state.car2_moves = 0

    if "random_numbers_1" not in st.session_state:
        st.session_state.random_numbers_1 = []

    if "random_numbers_2" not in st.session_state:
        st.session_state.random_numbers_2 = []

    if "data_for_excel_1" not in st.session_state:
        st.session_state.data_for_excel_1 = []

    if "data_for_excel_2" not in st.session_state:
        st.session_state.data_for_excel_2 = []

    if "data_for_condition_1" not in st.session_state:
        st.session_state.data_for_condition_1 = []

    if "data_for_condition_2" not in st.session_state:
        st.session_state.data_for_condition_2 = []

    if "car_start_time" not in st.session_state:
        st.session_state.car_start_time = None

    if "best_time" not in st.session_state:
        st.session_state.best_time = None

    if "running" not in st.session_state:
        st.session_state.running = False

    if "widget_key_counter" not in st.session_state:
        st.session_state.widget_key_counter = 0

    if "show_end_buttons" not in st.session_state:
        st.session_state.show_end_buttons = False

    # Function to change language
    def toggle_language():
        if st.session_state.language == "Italiano":
            st.session_state.language = "English"
        else:
            st.session_state.language = "Italiano"

    # Button to change language
    st.sidebar.button("Change Language", on_click=toggle_language)

    if st.session_state.language == "Italiano":
        title_text = "Car Mind Race"
        instruction_text = "..."
        choose_bit_text = "Scegli il tuo bit per la macchina verde..."
        start_race_text = "Avvia Gara"
        stop_race_text = "Blocca Gara"
        reset_game_text = "Resetta Gioco"
        download_data_text = "Scarica Dati"
        api_key_text = "Inserisci API Key per random.org"
        new_race_text = "Nuova Gara"
        end_game_text = "Termina Gioco"
        reset_game_message = "Gioco resettato!"
        error_message = "Errore nella generazione dei bit casuali. Fermato il gioco."
        win_message = "Vince l'auto {}, complimenti!"
        api_description_text = "Per garantire il corretto utilizzo..."
        move_multiplier_text = "Moltiplicatore di Movimento"
    else:
        title_text = "Car Mind Race"
        instruction_text = "..."
        choose_bit_text = "Choose your bit for the green car..."
        start_race_text = "Start Race"
        stop_race_text = "Stop Race"
        reset_game_text = "Reset Game"
        download_data_text = "Download Data"
        api_key_text = "Enter API Key for random.org"
        new_race_text = "New Race"
        end_game_text = "End Game"
        reset_game_message = "Game reset!"
        error_message = "Error generating random bits. Game stopped."
        win_message = "The {} car wins, congratulations!"
        api_description_text = "To ensure proper use..."
        move_multiplier_text = "Movement Multiplier"

    st.title(title_text)

    # Resto del codice per il layout e il gioco...
    # (includi tutte le altre funzioni, come display_cars, check_winner, etc.)

    # Start and stop buttons
    if st.sidebar.button(start_race_text, disabled=st.session_state.player_choice is None):
        st.session_state.running = True
        st.session_state.show_end_buttons = False

    if st.sidebar.button(stop_race_text):
        st.session_state.running = False

    # Resto del codice...

if __name__ == "__main__":
    main()

