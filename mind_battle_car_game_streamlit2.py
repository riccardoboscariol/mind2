import streamlit as st
import time
import numpy as np
import pandas as pd
from PIL import Image
import requests
import base64
import io

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
            headers["Random-Org-API-Key"] = api_key
        try:
            response = requests.get(url, params=params, headers=headers, timeout=5)
            response.raise_for_status()
            random_bits.extend(list(map(int, response.text.strip().split())))
            num_bits -= batch_size
        except (requests.RequestException, ValueError) as e:
            attempts += 1
            if attempts >= RETRY_LIMIT:
                st.warning(f"Errore durante l'accesso a random.org: {e}. Utilizzo numeri casuali locali.")
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
    if car_pos > 1000:
        car_pos = 1000
    return car_pos

def image_to_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def main():
    st.set_page_config(page_title="Car Mind Race", layout="wide")
    st.title("Car Mind Race")

    st.markdown("""
        <style>
        .stSlider > div > div > div > div {
            background: white;
        }
        .stSlider > div > div > div {
            background: white;
        }
        .stSlider > div > div > div > div > div {
            background: white;
            border-radius: 50%;
            height: 14px;
            width: 14px;
        }
        .slider-container {
            position: relative;
            height: 120px;
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
        .slider-container input[type=range] {
            width: 100%;
        }
        </style>
        """, unsafe_allow_html=True)

    st.markdown("""
        Il primo giocatore sceglie la macchina verde e la cifra che vuole influenzare.
        L'altro giocatore (o il PC) avrà la macchina rossa e l'altra cifra.
        La macchina verde si muove quando l'entropia è a favore del suo bit scelto e inferiore al 5%.
        La macchina rossa si muove quando l'entropia è a favore dell'altro bit e inferiore al 5%.
        Ogni 0.1 secondi vengono generati 2500 bit casuali per ciascuno slot.
        Il programma utilizza random.org.
        L'entropia è calcolata usando la formula di Shannon. La macchina si muove se l'entropia è inferiore al 5° percentile e la cifra scelta è più frequente.
        La distanza di movimento è calcolata con la formula: Distanza = 15 × (1 + ((percentile - entropia) / percentile)).
        """)

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

    st.sidebar.title("Menu")
    if st.session_state.player_choice is None:
        start_button = st.sidebar.button("Avvia Gara", disabled=True)
    else:
        start_button = st.sidebar.button("Avvia Gara")
    stop_button = st.sidebar.button("Blocca Gara")
    api_key = st.sidebar.text_input("Inserisci API Key per random.org")
    
    # Aggiunta della descrizione sotto l'inserimento della chiave API
    st.sidebar.markdown(
        "Per garantire il corretto utilizzo, è consigliabile acquistare un piano per l'inserimento della chiave API da questo sito: [https://api.random.org/pricing](https://api.random.org/pricing)."
    )

    download_menu = st.sidebar.expander("Download")
    with download_menu:
        download_button = st.button("Scarica Dati")
    reset_button = st.sidebar.button("Resetta Gioco")

    move_multiplier = st.sidebar.slider("Moltiplicatore di Movimento", min_value=1, max_value=100, value=15)

    car_image = Image.open("car.png").resize((150, 150))
    car2_image = Image.open("car2.png").resize((150, 150))
    car_image_base64 = image_to_base64(car_image)
    car2_image_base64 = image_to_base64(car2_image)

    st.write("Scegli il tuo bit per la macchina verde:")
    if st.button("Scegli 1"):
        st.session_state.player_choice = 1
    if st.button("Scegli 0"):
        st.session_state.player_choice = 0

    car_placeholder = st.empty()
    car2_placeholder = st.empty()

    def display_cars():
        car_placeholder.markdown(f"""
            <div class="slider-container first">
                <img src="data:image/png;base64,{car_image_base64}" class="car-image" style="left:{st.session_state.car_pos / 10}%">
                <input type="range" min="0" max="1000" value="{st.session_state.car_pos}" disabled>
            </div>
        """, unsafe_allow_html=True)
        
        car2_placeholder.markdown(f"""
            <div class="slider-container">
                <img src="data:image/png;base64,{car2_image_base64}" class="car-image" style="left:{st.session_state.car2_pos / 10}%">
                <input type="range" min="0" max="1000" value="{st.session_state.car2_pos}" disabled>
            </div>
        """, unsafe_allow_html=True)

    display_cars()

    def check_winner():
        if st.session_state.car_pos >= 1000:
            return "Verde"
        elif st.session_state.car2_pos >= 1000:
            return "Rossa"
        return None

    def end_race(winner):
        st.session_state.running = False
        st.success(f"Vince l'auto {winner}, complimenti!")
        st.session_state.show_end_buttons = True

    def reset_game():
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
        st.session_state.widget_key_counter = 0
        st.session_state.player_choice = None
        st.session_state.running = False
        st.session_state.show_end_buttons = False
        st.write("Gioco resettato!")
        display_cars()

    if start_button and st.session_state.player_choice is not None:
        st.session_state.running = True
        st.session_state.car_start_time = time.time()
        st.session_state.show_end_buttons = False

    if stop_button:
        st.session_state.running = False

    if "show_end_buttons" not in st.session_state:
        st.session_state.show_end_buttons = False

    if st.session_state.show_end_buttons:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Nuova Gara"):
                reset_game()
        with col2:
            if st.button("Termina Gioco"):
                st.stop()

    while st.session_state.running:
        start_time = time.time()

        # Ottieni numeri casuali da random.org
        random_bits_1 = get_random_bits_from_random_org(2500, api_key)
        random_bits_2 = get_random_bits_from_random_org(2500, api_key)

        if random_bits_1 is None or random_bits_2 is None:
            st.session_state.running = False
            st.write("Errore nella generazione dei bit casuali. Fermato il gioco.")
            break

        st.session_state.random_numbers_1.extend(random_bits_1)
        st.session_state.random_numbers_2.extend(random_bits_2)
        
        st.session_state.data_for_excel_1.append(random_bits_1)
        st.session_state.data_for_excel_2.append(random_bits_2)
        
        entropy_score_1 = calculate_entropy(random_bits_1)
        entropy_score_2 = calculate_entropy(random_bits_2)
        
        st.session_state.data_for_condition_1.append(entropy_score_1)
        st.session_state.data_for_condition_2.append(entropy_score_2)
        
        percentile_5_1 = np.percentile(st.session_state.data_for_condition_1, 5)
        percentile_5_2 = np.percentile(st.session_state.data_for_condition_2, 5)

        count_1 = sum(random_bits_1)
        count_0 = len(random_bits_1) - count_1

        if entropy_score_1 < percentile_5_1:
            if st.session_state.player_choice == 1 and count_1 > count_0:
                st.session_state.car_pos = move_car(st.session_state.car_pos, move_multiplier * (1 + ((percentile_5_1 - entropy_score_1) / percentile_5_1)))
                st.session_state.car1_moves += 1
            elif st.session_state.player_choice == 0 and count_0 > count_1:
                st.session_state.car_pos = move_car(st.session_state.car_pos, move_multiplier * (1 + ((percentile_5_1 - entropy_score_1) / percentile_5_1)))
                st.session_state.car1_moves += 1

        if entropy_score_2 < percentile_5_2:
            if st.session_state.player_choice == 1 and count_0 > count_1:
                st.session_state.car2_pos = move_car(st.session_state.car2_pos, move_multiplier * (1 + ((percentile_5_2 - entropy_score_2) / percentile_5_2)))
                st.session_state.car2_moves += 1
            elif st.session_state.player_choice == 0 and count_1 > count_0:
                st.session_state.car2_pos = move_car(st.session_state.car2_pos, move_multiplier * (1 + ((percentile_5_2 - entropy_score_2) / percentile_5_2)))
                st.session_state.car2_moves += 1

        display_cars()

        winner = check_winner()
        if winner:
            end_race(winner)
            break

        time_elapsed = time.time() - start_time
        time.sleep(max(0.1 - time_elapsed, 0))

    if download_button:
        df = pd.DataFrame({
            "Condizione 1": [''.join(map(str, row)) for row in st.session_state.data_for_excel_1],
            "Condizione 2": [''.join(map(str, row)) for row in st.session_state.data_for_excel_2]
        })
        df.to_excel("random_numbers.xlsx", index=False)
        with open("random_numbers.xlsx", "rb") as file:
            st.download_button(
                label="Scarica Dati",
                data=file,
                file_name="random_numbers.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    if reset_button:
        reset_game()

if __name__ == "__main__":
    main()

