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

def main():
    st.set_page_config(page_title="Car Mind Race", layout="wide")

    if "language" not in st.session_state:
        st.session_state.language = "Italiano"

    if "api_key" not in st.session_state:
        st.session_state.api_key = ""

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
        instruction_text = """
            Il primo giocatore sceglie la macchina verde e la cifra che vuole influenzare.
            L'altro giocatore (o il PC) avrà la macchina rossa e l'altra cifra.
            La macchina verde si muove quando l'entropia è a favore del suo bit scelto e inferiore al 5%.
            La macchina rossa si muove quando l'entropia è a favore dell'altro bit e inferiore al 5%.
            Ogni 0.5 secondi, esclusi i tempi di latenza per la versione gratuita senza API, vengono generati 1000 bit casuali per ciascuno slot.
            Il programma utilizza random.org. L'entropia è calcolata usando la formula di Shannon.
            La macchina si muove se l'entropia è inferiore al 5° percentile e la cifra scelta è più frequente.
            La distanza di movimento è calcolata con la formula: Distanza = Moltiplicatore × (1 + ((percentile - entropia) / percentile)).
            """
        choose_bit_text = "Scegli il tuo bit per la macchina verde. Puoi scegliere anche la 'velocità' di movimento indicando il punteggio nello slider 'Moltiplicatore di Movimento'."
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
        api_description_text = "Per garantire il corretto utilizzo, è consigliabile acquistare un piano per l'inserimento della chiave API da questo sito: [https://api.random.org/pricing](https://api.random.org/pricing)."
        move_multiplier_text = "Moltiplicatore di Movimento"
    else:
        title_text = "Car Mind Race"
        instruction_text = """
            The first player chooses the green car and the digit they want to influence.
            The other player (or the PC) will have the red car and the other digit.
            The green car moves when the entropy favors its chosen bit and is below 5%.
            The red car moves when the entropy favors the other bit and is below 5%.
            Every 0.5 seconds, excluding latency times for the free version without API, 1000 random bits are generated for each slot.
            The program uses random.org. Entropy is calculated using Shannon's formula.
            The car moves if the entropy is below the 5th percentile and the chosen digit is more frequent.
            The movement distance is calculated with the formula: Distance = Multiplier × (1 + ((percentile - entropy) / percentile)).
            """
        choose_bit_text = "Choose your bit for the green car. You can also choose the 'speed' of movement by setting the score on the 'Movement Multiplier' slider."
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
        api_description_text = "To ensure proper use, it is advisable to purchase a plan for entering the API key from this site: [https://api.random.org/pricing](https://api.random.org/pricing)."
        move_multiplier_text = "Movement Multiplier"

    st.title(title_text)

    # Generate a unique query string to prevent caching
    import time
    unique_query_string = f"?v={int(time.time())}"

    st.markdown(
        f"""
        <style>
        .stSlider > div > div > div > div {{
            background: white;
        }}
        .stSlider > div > div > div {{
            background: #f0f0f0; /* Lighter color for the slider track */
        }}
        .stSlider > div > div > div > div > div {{
            background: transparent; /* Make slider thumb invisible */
            border-radius: 50%;
            height: 0px;  /* Reduce slider thumb height */
            width: 0px;  /* Reduce slider thumb width */
            position: relative;
            top: 0px; /* Correct slider thumb position */
        }}
        .slider-container {{
            position: relative;
            height: 250px; /* Height to fit sliders and cars */
            margin-bottom: 50px;
        }}
        .slider-container.first {{
            margin-top: 50px;
            margin-bottom: 40px;
        }}
        .car-image {{
            position: absolute;
            top: 50px;  /* Move car 3px higher */
            left: 0px;
            width: 150px;  /* Width of the car image */
            z-index: 20;  /* Ensure cars are above numbers */
        }}
        .number-image {{
            position: absolute;
            top: 30px;  /* Move images 1px lower */
            left: 66px; /* Move images 7px left */
            transform: translateX(-50%); /* Adjust to perfectly center */
            width: 120px;  /* Width of the number images slightly larger */
            z-index: 10;  /* Ensure numbers

