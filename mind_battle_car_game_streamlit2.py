import streamlit as st
import time
import numpy as np
import pandas as pd
from PIL import Image
from scipy.stats import mannwhitneyu, binomtest
import requests
import base64
import io
import serial
import serial.tools.list_ports
import platform
from pydub import AudioSegment
from pydub.playback import play

# Imposta il percorso completo di ffmpeg/ffplay
AudioSegment.converter = "C:\\Users\\Riccardo\\Desktop\\persuoni\\ffmpeg-7.0.1\\ffmpeg-tools-2022-01-01-git-d6b2357edd\\bin\\ffmpeg.exe"
AudioSegment.ffmpeg = "C:\\Users\\Riccardo\\Desktop\\persuoni\\ffmpeg-7.0.1\\ffmpeg-tools-2022-01-01-git-d6b2357edd\\bin\\ffmpeg.exe"
AudioSegment.ffprobe = "C:\\Users\\Riccardo\\Desktop\\persuoni\\ffmpeg-7.0.1\\ffmpeg-tools-2022-01-01-git-d6b2357edd\\bin\\ffprobe.exe"

def get_random_bits_from_trng(num_bits):
    ports = list(serial.tools.list_ports.comports())
    for port in ports:
        if "TrueRNG" in port.description:
            try:
                ser = serial.Serial(port.device, 9600, timeout=1)
                random_bits = []
                while len(random_bits) < num_bits:
                    byte = ser.read()
                    if byte:
                        random_bits.extend([int(bit) for bit in bin(ord(byte))[2:].zfill(8)])
                ser.close()
                return random_bits[:num_bits]
            except serial.SerialException as e:
                st.warning(f"Errore nella comunicazione con TrueRNG3: {e}")
                return None
    return None

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

def play_sound(sound_file):
    try:
        sound = AudioSegment.from_file(sound_file)
        play(sound)
    except Exception as e:
        st.warning(f"Errore durante la riproduzione del suono: {e}")

def main():
    st.set_page_config(page_title="Car Mind Race", layout="wide")
    st.title("Car Mind Race")

    st.markdown("""
        <style>
        .stSlider > div > div > div > div {
            display: none;
        }
        .stSlider > div > div > div > div > div {
            background: red;
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
            margin-bottom: 40px.
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
        In questa applicazione, due macchine da corsa competono tra loro basandosi su numeri casuali. 
        Ogni macchina si muove in base alla rarità dei numeri casuali generati. Più rara è la sequenza, 
        più lontano si muove la macchina. Puoi avviare la gara, fermarla, scaricare i dati generati e 
        visualizzare le statistiche.
        """)

    st.sidebar.title("Menu")
    start_button = st.sidebar.button("Avvia Gara")
    stop_button = st.sidebar.button("Blocca Gara")
    download_menu = st.sidebar.expander("Download")
    with download_menu:
        download_button = st.button("Scarica Dati")
    stats_button = st.sidebar.button("Mostra Analisi Statistiche")
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
        random_bits_1 = get_random_bits_from_trng(2500)
        if random_bits_1 is None:
            random_bits_1 = get_random_bits_from_random_org(2500)
        
        random_bits_2 = get_random_bits_from_trng(2500)
        if random_bits_2 is None:
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
        
        st.write(f"Random Bits 1: {random_bits_1[:10]}...")
        st.write(f"Random Bits 2: {random_bits_2[:10]}...")
        st.write(f"Entropy Score 1: {entropy_score_1}")
        st.write(f"Entropy Score 2: {entropy_score_2}")
        st.write(f"Percentile 5_1: {percentile_5_1}")
        st.write(f"Percentile 5_2: {percentile_5_2}")

        if entropy_score_1 < percentile_5_1:
            rarity_percentile = 1 - (entropy_score_1 / percentile_5_1)
            st.session_state.car_pos = move_car(st.session_state.car_pos, 6 * (1 + (10 * rarity_percentile)))
            st.session_state.car1_moves += 1
            play_sound("move_car.wav")
        
        if entropy_score_2 < percentile_5_2:
            rarity_percentile = 1 - (entropy_score_2 / percentile_5_2)
            st.session_state.car2_pos = move_car(st.session_state.car2_pos, 6 * (1 + (10 * rarity_percentile)))
            st.session_state.car2_moves += 1
            play_sound("move_car2.wav")
        
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

    if stats_button:
        if st.session_state.data_for_condition_1 and st.session_state.data_for_condition_2:
            u_stat, p_value = mannwhitneyu(st.session_state.data_for_condition_1, st.session_state.data_for_condition_2, alternative='two-sided')
            mann_whitney_text = f"Mann-Whitney U test: U-stat = {u_stat:.4f}, p-value = {p_value:.4f}"
        else:
            mann_whitney_text = "Mann-Whitney U test: Dati insufficienti"

        total_moves = st.session_state.car1_moves + st.session_state.car2_moves
        if total_moves > 0:
            binom_p_value_moves = binomtest(st.session_state.car1_moves, total_moves, alternative='two-sided').pvalue
            binom_text_moves = f"Test Binomiale (numero di spostamenti): p-value = {binom_p_value_moves:.4f}"
        else:
            binom_text_moves = "Test Binomiale (numero di spostamenti): Dati insufficienti"

        if st.session_state.random_numbers_1:
            binom_p_value_1 = binomtest(np.sum(st.session_state.random_numbers_1), len(st.session_state.random_numbers_1), alternative='two-sided').pvalue
            binom_text_1 = f"Test Binomiale (cifre auto verde): p-value = {binom_p_value_1:.4f}"
        else:
            binom_text_1 = "Test Binomiale (cifre auto verde): Dati insufficienti"

        if st.session_state.random_numbers_2:
            binom_p_value_2 = binomtest(np.sum(st.session_state.random_numbers_2), len(st.session_state.random_numbers_2), alternative='two-sided').pvalue
            binom_text_2 = f"Test Binomiale (cifre auto rossa): p-value = {binom_p_value_2:.4f}"
        else:
            binom_text_2 = "Test Binomiale (cifre auto rossa): Dati insufficienti"

        stats_text = mann_whitney_text + "\n" + binom_text_moves + "\n" + binom_text_1 + "\n" + binom_text_2
        st.write(stats_text)
    
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
