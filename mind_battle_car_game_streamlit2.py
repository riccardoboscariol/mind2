import streamlit as st
import time
import numpy as np
import pandas as pd
from PIL import Image
from scipy.stats import mannwhitneyu, binomtest
import requests
import base64
import io

def get_random_bits_from_random_org(num_bits):
    url = "https://www.random.org/integers/"
    params = {
        "num": num_bits,
        "min": 0,
        "max": 1,
        "col": 1,
        "base": 10,
        "format": "plain",
        "rnd": "new"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        random_bits = list(map(int, response.text.strip().split()))
        return random_bits
    except (requests.RequestException, ValueError) as e:
        st.warning(f"Errore durante l'accesso a random.org: {e}")
        return None

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
        Ogni 0.1 secondi vengono generati 5000 bit casuali per ciascuno slot.
        Il programma utilizza random.org.
        L'entropia è calcolata usando la formula di Shannon. La macchina si muove se l'entropia è inferiore al 5° percentile e la cifra scelta è più frequente.
        La distanza di movimento è calcolata con la formula: Distanza = 6 × (1 + ((percentile - entropia) / percentile)).
        """)

    st.sidebar.title("Menu")
    start_button = st.sidebar.button("Avvia Gara")
    stop_button = st.sidebar.button("Blocca Gara")
    download_menu = st.sidebar.expander("Download")
    with download_menu:
        download_button = st.button("Scarica Dati")
    reset_button = st.sidebar.button("Resetta Gioco")

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

    car_image = Image.open("car.png").resize((150, 150))
    car2_image = Image.open("car2.png").resize((150, 150))
    car_image_base64 = image_to_base64(car_image)
    car2_image_base64 = image_to_base64(car2_image)

    if start_button:
        st.session_state.running = True
        st.session_state.car_start_time = time.time()

    if stop_button:
        st.session_state.running = False

    car_placeholder = st.empty()
    car2_placeholder = st.empty()

    while st.session_state.running:
        random_bits_1 = get_random_bits_from_random_org(2500)
        random_bits_2 = get_random_bits_from_random_org(2500)

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

        if entropy_score_1 < percentile_5_1:
            rarity_percentile = 1 - (entropy_score_1 / percentile_5_1)
            st.session_state.car_pos = move_car(st.session_state.car_pos, 6 * (1 + (10 * rarity_percentile)))
            st.session_state.car1_moves += 1
        
        if entropy_score_2 < percentile_5_2:
            rarity_percentile = 1 - (entropy_score_2 / percentile_5_2)
            st.session_state.car2_pos = move_car(st.session_state.car2_pos, 6 * (1 + (10 * rarity_percentile)))
            st.session_state.car2_moves += 1
        
        st.session_state.widget_key_counter += 1
        
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

        time.sleep(0.2)

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
        st.write("Gioco resettato!")

if __name__ == "__main__":
    main()
