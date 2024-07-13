import streamlit as st
import time
import numpy as np
import pandas as pd
from PIL import Image
from scipy.stats import mannwhitneyu, binomtest
import matplotlib.pyplot as plt
import io
import requests
import base64
import random

# Funzione per ottenere bit casuali da ANU Quantum Random Numbers
def get_random_bits_from_anu(num_bits, max_retries=5):
    url = "https://qrng.anu.edu.au/API/jsonI.php"
    bits_needed = num_bits
    random_bits = []

    while bits_needed > 0:
        params = {
            "length": min(bits_needed, 500),  # Richiedi al massimo 500 bit per volta
            "type": "uint8"
        }
        retries = 0
        while retries < max_retries:
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                if not data.get('success', False):
                    st.warning(f"Risposta JSON di ANU: {data}")
                    raise ValueError("La risposta JSON non indica successo.")
                if 'data' not in data or not isinstance(data['data'], list):
                    raise ValueError("La risposta JSON non contiene il campo 'data' o il campo non è una lista.")
                for number in data['data']:
                    random_bits.extend([int(bit) for bit in bin(number)[2:].zfill(8)])  # Converte in binario e zfill per ottenere 8 bit
                bits_needed -= min(bits_needed, 500)
                break
            except (requests.RequestException, ValueError) as e:
                retries += 1
                if retries == max_retries:
                    if not st.session_state.get('anu_warning_shown', False):
                        st.session_state['anu_warning_shown'] = True
                        st.warning(f"Errore durante l'accesso a ANU QRNG: {e}. Utilizzando la generazione locale.")
                    return get_random_bits(num_bits)
                time.sleep(2 ** retries + random.uniform(0, 1))  # Backoff esponenziale con jitter
    return random_bits[:num_bits]

# Funzione per ottenere bit casuali localmente
def get_random_bits(num_bits):
    return np.random.randint(0, 2, num_bits).tolist()

# Funzione per calcolare l'entropia
def calculate_entropy(bits):
    n = len(bits)
    counts = np.bincount(bits, minlength=2)
    p = counts / n
    p = p[np.nonzero(p)]
    entropy = -np.sum(p * np.log2(p))
    return entropy

# Funzione per spostare l'auto
def move_car(car_pos, distance):
    car_pos += distance
    if car_pos > 1000:  # Se l'auto esce dallo schermo, riportala all'inizio
        car_pos = 1000
    return car_pos

# Funzione per convertire l'immagine in base64
def image_to_base64(image):
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# Funzione principale
def main():
    st.title("Mind Battle Car Game")

    # CSS per personalizzare i colori degli slider e nascondere i numeri
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
            height: 120px; /* Aumentato per dare più spazio tra slider e scritte */
            margin-bottom: 50px; /* Aggiunto margine inferiore per slider con macchina rossa */
        }
        .slider-container.first {
            margin-top: 50px; /* Aggiunto margine superiore per distanziare dal pulsante resetta gioco */
            margin-bottom: 40px; /* Diminuire lo spazio tra i due slider, modifica questo valore */
        }
        .car-image {
            position: absolute;
            top: -80px; /* Aumentato per ingrandire le immagini e lasciare spazio tra slider e scritte */
            width: 150px; /* Ingrandito di tre volte */
        }
        .slider-container input[type=range] {
            width: 100%;
        }
        </style>
        """, unsafe_allow_html=True)

    start_button = st.button("Avvia Generazione", key="start")
    stop_button = st.button("Blocca Generazione", key="stop")
    download_button = st.button("Scarica Dati", key="download_data")
    download_graph_button = st.button("Scarica Grafico", key="download_graph")
    stats_button = st.button("Mostra Analisi Statistiche", key="stats")
    reset_button = st.button("Resetta Gioco", key="reset")
    
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
        # Priorità: ANU QRNG > Generazione locale
        random_bits_1 = get_random_bits_from_anu(500)
        random_bits_2 = get_random_bits_from_anu(500)

        if random_bits_1 is None:
            random_bits_1 = get_random_bits(500)
        if random_bits_2 is None:
            random_bits_2 = get_random_bits(500)
        
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
        
        st.session_state.widget_key_counter += 1  # Incrementa il contatore per ogni iterazione
        
        car_placeholder.markdown(f"""
            <div class="slider-container first" style="margin-bottom: 40px;">
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

        time.sleep(0.1)

    if download_button:
        df = pd.DataFrame({
            "Condizione 1": [''.join(map(str, row)) for row in st.session_state.data_for_excel_1],
            "Condizione 2": [''.join(map(str, row)) for row in st.session_state.data_for_excel_2]
        })
        try:
            df.to_excel("random_numbers.xlsx", index=False)
            with open("random_numbers.xlsx", "rb") as file:
                st.download_button(
                    label="Scarica Dati",
                    data=file,
                    file_name="random_numbers.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except ImportError:
            st.error("openpyxl non è installato. Installa openpyxl per scaricare i dati in formato Excel.")

    if download_graph_button:
        fig, ax = plt.subplots(figsize=(8, 4))
        if st.session_state.data_for_condition_1:
            ax.hist(st.session_state.data_for_condition_1, bins=30, alpha=0.5, color='red', edgecolor='k')
        if st.session_state.data_for_condition_2:
            ax.hist(st.session_state.data_for_condition_2, bins=30, alpha=0.5, color='green', edgecolor='k')
        ax.set_title('Distribuzione della Rarità degli Slot')
        ax.set_xlabel('Rarità')
        ax.set_ylabel('Frequenza')
        buf = io.BytesIO()
        fig.savefig(buf, format='png')
        buf.seek(0)
        st.download_button(label="Scarica Grafico", data=buf, file_name="rarity_distribution.png", mime="image/png")
    
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
        st.session_state.widget_key_counter = 0  # Reset del contatore di chiavi
        st.write("Gioco resettato!")
        st.session_state['random_org_warning_shown'] = False  # Reset dell'avviso di errore per random.org

if __name__ == "__main__":
    main()
