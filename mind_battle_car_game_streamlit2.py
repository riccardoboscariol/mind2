import streamlit as st
import time
import numpy as np
import pandas as pd
from PIL import Image
import requests
import base64
import io
import os

MAX_BATCH_SIZE = 1000  # Dimensione massima del batch per le richieste a random.org
RETRY_LIMIT = 3  # Numero di tentativi per le richieste a random.org

def get_random_bits_from_random_org(num_bits, api_key=None):
    random_bits = []
    attempts = 0
    while num_bits > 0 and attempts < RETRY_LIMIT:
        batch_size = min(num_bits, MAX_BATCH_SIZE)
        url = "https://www.random.org/integers/"
        params = {
            "num": batch_size,
            "min": 0,
            "max": 1,
            "col": 1,
            "base": 10,
            "format": "plain",
            "rnd": "new"
        }
        headers = {"User-Agent": "streamlit_app"}
        if api_key:
            headers["Random-Org-API-Key"] = api_key.strip()  # Rimuove spazi bianchi

        # Log per il debug
        st.write(f"Request URL: {url}")
        st.write(f"Params: {params}")
        st.write(f"Headers: {headers}")

        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()  # Solleva eccezione per errori HTTP
            random_bits.extend(list(map(int, response.text.strip().split())))
            num_bits -= batch_size
        except requests.HTTPError as http_err:
            st.error(f"Errore HTTP: {http_err}")
            attempts += 1
            time.sleep(2)  # Attendi 2 secondi prima di riprovare
        except requests.RequestException as req_err:
            st.error(f"Errore durante l'accesso a random.org: {req_err}. Tentativo {attempts}/{RETRY_LIMIT}.")
            attempts += 1
            time.sleep(2)  # Attendi 2 secondi prima di riprovare
        except ValueError as val_err:
            st.error(f"Errore nel processamento dei dati da random.org: {val_err}")
            break

        # Se abbiamo raggiunto il limite di tentativi, usa il generatore locale
        if attempts >= RETRY_LIMIT:
            st.warning(f"Utilizzo numeri casuali locali dopo {RETRY_LIMIT} tentativi falliti.")
            random_bits.extend(get_local_random_bits(num_bits))
            break

    return random_bits

def get_local_random_bits(num_bits):
    return list(np.random.randint(0, 2, size=num_bits))

def calculate_entropy(bits):
    n = len(bits)
    counts = np.bincount(bits, minlength=2)
    p = counts / n
    p = p[np.nonzero(p)]
    entropy = -np.sum(p * np.log2(p))
    return entropy

def move_car(car_pos, distance):
    car_pos += distance
    if car_pos > 900:  # Accorciamo la pista per lasciare spazio alla bandierina
        car_pos = 900
    return car_pos

def image_to_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def main():
    st.set_page_config(page_title="Car Mind Race", layout="wide")
    
    if "language" not in st.session_state:
        st.session_state.language = "Italiano"
    
    # Funzione per cambiare la lingua
    def toggle_language():
        if st.session_state.language == "Italiano":
            st.session_state.language = "English"
        else:
            st.session_state.language = "Italiano"

    # Pulsante per cambiare la lingua
    st.sidebar.button("Change Language", on_click=toggle_language)

    if st.session_state.language == "Italiano":
        title_text = "Car Mind Race"
        instruction_text = """
            Il primo giocatore sceglie la macchina verde e la cifra che vuole influenzare.
            L'altro giocatore (o il PC) avrà la macchina rossa e l'altra cifra.
            La macchina verde si muove quando l'entropia è a favore del suo bit scelto e inferiore al 5%.
            La macchina rossa si muove quando l'entropia è a favore dell'altro bit e inferiore al 5%.
            Ogni 0.1 secondi, esclusi i tempi di latenza per la versione gratuita senza API, vengono generati 2500 bit casuali per ciascuno slot.
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
            Every 0.1 seconds, excluding latency times for the free version without API, 2500 random bits are generated for each slot.
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
        api_description_text = "To ensure proper use, it is advisable to purchase a plan for API key insertion from this site: [https://api.random.org/pricing](https://api.random.org/pricing)."
        move_multiplier_text = "Movement Multiplier"

    st.title(title_text)

    st.markdown(instruction_text)

    api_key = st.text_input(api_key_text)

    st.markdown(api_description_text)

    bit_choice = st.radio(choose_bit_text, (0, 1))
    move_multiplier = st.slider(move_multiplier_text, min_value=0.1, max_value=5.0, value=1.0, step=0.1)

    if "car_pos" not in st.session_state:
        st.session_state.car_pos = 0

    if "car2_pos" not in st.session_state:
        st.session_state.car2_pos = 0

    if "race_running" not in st.session_state:
        st.session_state.race_running = False

    car_image = Image.open("car.png")
    car2_image = Image.open("car2.png")
    flag_image = Image.open("flag.png")

    red_car_number_image = Image.open("1.png")  # Assicurati che queste immagini esistano
    green_car_number_image = Image.open("0.png")

    car_image_base64 = image_to_base64(car_image)
    car2_image_base64 = image_to_base64(car2_image)
    flag_image_base64 = image_to_base64(flag_image)

    red_car_number_base64 = image_to_base64(red_car_number_image)
    green_car_number_base64 = image_to_base64(green_car_number_image)

    car_placeholder = st.empty()
    car2_placeholder = st.empty()

    def display_cars():
        car_placeholder.markdown(f"""
            <div class="slider-container first">
                <img src="data:image/png;base64,{red_car_number_base64}" class="number-image" style="left:{st.session_state.car_pos / 10 - 1.5}%">
                <img src="data:image/png;base64,{car_image_base64}" class="car-image" style="left:{st.session_state.car_pos / 10}%">
                <input type="range" min="0" max="1000" value="{st.session_state.car_pos}" disabled>
                <img src="data:image/png;base64,{flag_image_base64}" class="flag-image">
            </div>
        """, unsafe_allow_html=True)

        car2_placeholder.markdown(f"""
            <div class="slider-container">
                <img src="data:image/png;base64,{green_car_number_base64}" class="number-image" style="left:{st.session_state.car2_pos / 10 - 1.5}%">
                <img src="data:image/png;base64,{car2_image_base64}" class="car-image" style="left:{st.session_state.car2_pos / 10}%">
                <input type="range" min="0" max="1000" value="{st.session_state.car2_pos}" disabled>
                <img src="data:image/png;base64,{flag_image_base64}" class="flag-image">
            </div>
        """, unsafe_allow_html=True)

    st.markdown("""
        <style>
        .slider-container {
            position: relative;
            height: 150px;
            margin-bottom: 50px;
        }
        .slider-container.first {
            margin-top: 50px;
            margin-bottom: 40px;
        }
        .car-image {
            position: absolute;
            top: -80px;
            width: 150px;
        }
        .number-image {
            position: absolute;
            top: -50px; /* Posiziona il numero sopra l'auto */
            width: 20px; /* Dimensione delle immagini numeriche */
        }
        .flag-image {
            position: absolute;
            top: -100px;
            width: 150px;
            left: 96%;  /* Posiziona la bandierina a destra */
        }
        .slider-container input[type=range] {
            width: 100%;
        }
        </style>
        """, unsafe_allow_html=True)

    def run_race():
        # Crea un array vuoto per raccogliere i dati della gara
        race_data = []
        st.session_state.race_running = True
        percentile = 0.05
        while st.session_state.race_running:
            bits = get_random_bits_from_random_org(2500, api_key=api_key)

            # Controlla se la generazione di bit è fallita
            if not bits:
                st.error(error_message)
                break

            entropy = calculate_entropy(bits)
            chosen_bit_count = bits.count(bit_choice)
            other_bit_count = len(bits) - chosen_bit_count

            chosen_bit_prob = chosen_bit_count / len(bits)
            other_bit_prob = other_bit_count / len(bits)

            if entropy < percentile:
                if chosen_bit_prob > other_bit_prob:
                    st.session_state.car2_pos = move_car(st.session_state.car2_pos, move_multiplier * (1 + ((percentile - entropy) / percentile)))
                else:
                    st.session_state.car_pos = move_car(st.session_state.car_pos, move_multiplier * (1 + ((percentile - entropy) / percentile)))

            # Registra i dati della gara
            race_data.append([entropy, chosen_bit_prob, other_bit_prob, st.session_state.car_pos, st.session_state.car2_pos])

            display_cars()
            time.sleep(0.1)

            # Verifica se una delle macchine ha vinto
            if st.session_state.car_pos >= 900 or st.session_state.car2_pos >= 900:
                winning_car = "verde" if st.session_state.car2_pos >= 900 else "rossa"
                st.success(win_message.format(winning_car))
                break

        # Converte i dati della gara in un DataFrame di Pandas
        race_df = pd.DataFrame(race_data, columns=["Entropy", "Chosen Bit Probability", "Other Bit Probability", "Red Car Position", "Green Car Position"])

        # Funzione per scaricare i dati
        def convert_df(df):
            return df.to_csv(index=False).encode('utf-8')

        csv = convert_df(race_df)

        st.download_button(
            label=download_data_text,
            data=csv,
            file_name='race_data.csv',
            mime='text/csv',
        )

    start_button = st.button(start_race_text)
    stop_button = st.button(stop_race_text)
    reset_button = st.button(reset_game_text)

    if start_button:
        run_race()

    if stop_button:
        st.session_state.race_running = False

    if reset_button:
        st.session_state.car_pos = 0
        st.session_state.car2_pos = 0
        st.session_state.race_running = False
        st.success(reset_game_message)

    display_cars()

if __name__ == "__main__":
    main()
