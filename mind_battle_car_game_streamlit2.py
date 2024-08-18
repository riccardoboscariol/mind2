import streamlit as st
import time
import numpy as np
import pandas as pd
from PIL import Image
import base64
import io
import os
from rdoclient import RandomOrgClient
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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

def configure_google_sheets(sheet_name):
    """Configure Google Sheets using credentials from Streamlit Secrets."""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials_info = json.loads(st.secrets["google_sheets"]["credentials_json"])
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_info, scope)
    client = gspread.authorize(credentials)
    sheet = client.open(sheet_name)
    sheet1 = sheet.sheet1  # First sheet
    return sheet1

def save_race_data(sheet, race_data):
    """Save race data to Google Sheets."""
    try:
        sheet.append_row(race_data)
    except Exception as e:
        st.error(f"Error saving data to Google Sheets: {e}")

def main():
    st.set_page_config(page_title="Car Mind Race", layout="wide")

    if "language" not in st.session_state:
        st.session_state.language = "Italiano"

    if "api_key" not in st.session_state:
        st.session_state.api_key = ""

    if "warned_random_org" not in st.session_state:
        st.session_state.warned_random_org = False

    if "consent_given" not in st.session_state:
        st.session_state.consent_given = False

    # Pulsanti per cambiare lingua
    col1, col2 = st.sidebar.columns(2)
    if col1.button("Italiano"):
        st.session_state.language = "Italiano"
    if col2.button("English"):
        st.session_state.language = "English"

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
        retry_text = "Voglio riprovare"
        reset_game_message = "Gioco resettato!"
        error_message = "Errore nella generazione dei bit casuali. Fermato il gioco."
        win_message = "Vince l'auto {}, complimenti!"
        save_data_text = "Vuoi inviare i dati per motivi di ricerca?"
        save_data_info = "I dati saranno utilizzati solo per scopi di ricerca scientifica nel rispetto delle leggi vigenti sulla privacy."
        yes_option = "Sì"
        no_option = "No"
        move_multiplier_text = "Moltiplicatore di Movimento"
        email_ref_text = "Riferimento Email: riccardoboscariol97@gmail.com"
        api_description_text = "Per garantire il corretto utilizzo, è consigliabile acquistare un piano per l'inserimento della chiave API da questo sito: [https://api.random.org/pricing](https://api.random.org/pricing)."
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
        retry_text = "I want to retry"
        reset_game_message = "Game reset!"
        error_message = "Error generating random bits. Game stopped."
        win_message = "The {} car wins, congratulations!"
        save_data_text = "Do you want to send the data for research purposes?"
        save_data_info = "The data will be used solely for scientific research purposes in compliance with applicable privacy laws."
        yes_option = "Yes"
        no_option = "No"
        move_multiplier_text = "Movement Multiplier"
        email_ref_text = "Email Referee: riccardoboscariol97@gmail.com"
        api_description_text = "To ensure proper use, it is advisable to purchase a plan for entering the API key from this site: [https://api.random.org/pricing](https://api.random.org/pricing)."

    # Mantieni il titolo con dimensioni maggiori
    st.markdown(f"<h1 style='font-size: 48px;'>{title_text}</h1>", unsafe_allow_html=True)

    st.markdown(instruction_text)

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
    if "show_retry_popup" not in st.session_state:
        st.session_state.show_retry_popup = False

    st.sidebar.title("Menu")
    start_button = st.sidebar.button(
        start_race_text, key="start_button", disabled=st.session_state.player_choice is None or st.session_state.running
    )
    stop_button = st.sidebar.button(stop_race_text, key="stop_button")

    # Persist API key in session state
    st.session_state.api_key = st.sidebar.text_input(
        api_key_text, key="api_key_input", value=st.session_state.api_key, type="password"
    )

    client = None
    if st.session_state.api_key:
        client = configure_random_org(st.session_state.api_key)

    st.sidebar.markdown(api_description_text)

    download_menu = st.sidebar.expander("Download")
    with download_menu:
        download_button = st.button(download_data_text, key="download_button")
    reset_button = st.sidebar.button(reset_game_text, key="reset_button")

    # Default move multiplier set to 50 instead of 20
    move_multiplier = st.sidebar.slider(
        move_multiplier_text, min_value=1, max_value=100, value=50, key="move_multiplier"
    )

    # Add email reference at the bottom of the sidebar
    st.sidebar.markdown(f"### {email_ref_text}")

    image_dir = os.path.abspath(os.path.dirname(__file__))
    car_image = Image.open(os.path.join(image_dir, "car.png")).resize((150, 150))  # Red car
    car2_image = Image.open(os.path.join(image_dir, "car2.png")).resize((150, 150))  # Green car
    flag_image = Image.open(os.path.join(image_dir, "bandierina.png")).resize(
        (150, 150)
    )  # Flag of the same size as the cars

    # Load images for numbers and resize further to 120x120 pixels
    number_0_green_image = Image.open(os.path.join(image_dir, "0green.png")).resize(
        (120, 120)
    )  # Slightly larger
    number_1_green_image = Image.open(os.path.join(image_dir, "1green.png")).resize(
        (120, 120)
    )  # Slightly larger
    number_0_red_image = Image.open(os.path.join(image_dir, "0red.png")).resize(
        (120, 120)
    )  # Slightly larger
    number_1_red_image = Image.open(os.path.join(image_dir, "1red.png")).resize(
        (120, 120)
    )  # Slightly larger

    st.write(choose_bit_text)

    # Initialize number images with default values
    green_car_number_image = number_0_green_image
    red_car_number_image = number_1_red_image

    # Determine which number image to display for each car
    col1, col2 = st.columns([1, 1])
    with col1:
        button1 = st.button(
            "Scegli 1" if st.session_state.language == "Italiano" else "Choose 1", 
            key="button1", 
            use_container_width=True, 
            help="Scegli il bit 1" if st.session_state.language == "Italiano" else "Choose bit 1"
        )
    with col2:
        button0 = st.button(
            "Scegli 0" if st.session_state.language == "Italiano" else "Choose 0", 
            key="button0", 
            use_container_width=True, 
            help="Scegli il bit 0" if st.session_state.language == "Italiano" else "Choose bit 0"
        )

    if button1:
        st.session_state.player_choice = 1
        st.session_state.green_car_number_image = number_1_green_image
        st.session_state.red_car_number_image = number_0_red_image
        st.session_state.button1_active = True
        st.session_state.button0_active = False

    if button0:
        st.session_state.player_choice = 0
        st.session_state.green_car_number_image = number_0_green_image
        st.session_state.red_car_number_image = number_1_red_image
        st.session_state.button0_active = True
        st.session_state.button1_active = False

    # Assign the chosen images if a choice has been made
    if st.session_state.player_choice is not None:
        green_car_number_image = st.session_state.green_car_number_image
        red_car_number_image = st.session_state.red_car_number_image

    # Active button style
    active_button_style = """
    <style>
    div.stButton > button[title="Scegli il bit 1"] { background-color: #90EE90; }
    div.stButton > button[title="Scegli il bit 0"] { background-color: #FFB6C1; }
    .number-image.show {
        display: block;
    }
    </style>
    """
    if st.session_state.player_choice == 1 or st.session_state.player_choice == 0:
        st.markdown(active_button_style, unsafe_allow_html=True)

    car_image_base64 = image_to_base64(car_image)
    car2_image_base64 = image_to_base64(car2_image)
    flag_image_base64 = image_to_base64(flag_image)
    red_car_number_base64 = image_to_base64(red_car_number_image)
    green_car_number_base64 = image_to_base64(green_car_number_image)

    car_placeholder = st.empty()
    car2_placeholder = st.empty()

    def display_cars():
        """Display the cars and the images of the selected numbers."""
        car_placeholder.markdown(
            f"""
            <div class="slider-container first">
                <!-- Car image and position -->
                <img src="data:image/png;base64,{car_image_base64}" class="car-image" style="left:calc(-71px + {st.session_state.car_pos / 10}%)">
                <!-- Red car number image -->
                <img src="data:image/png;base64,{red_car_number_base64}" class="number-image show" 
                     style="left:calc(-43px + {st.session_state.car_pos / 10}%); top: 34px; z-index: 10;">
                <input type="range" min="0" max="1000" value="{st.session_state.car_pos}" disabled>
                <img src="data:image/png;base64,{flag_image_base64}" class="flag-image">
            </div>
        """,
            unsafe_allow_html=True,
        )

        car2_placeholder.markdown(
            f"""
            <div class="slider-container">
                <!-- Green car image and position -->
                <img src="data:image/png;base64,{car2_image_base64}" class="car-image" style="left:calc(-71px + {st.session_state.car2_pos / 10}%)">
                <!-- Green car number image -->
                <img src="data:image/png;base64,{green_car_number_base64}" class="number-image show" 
                     style="left:calc(-43px + {st.session_state.car2_pos / 10}%); top: 34px; z-index: 10;">
                <input type="range" min="0" max="1000" value="{st.session_state.car2_pos}" disabled>
                <img src="data:image/png;base64,{flag_image_base64}" class="flag-image">
            </div>
        """,
            unsafe_allow_html=True,
        )

    display_cars()

    def check_winner():
        """Check if there is a winner."""
        if st.session_state.car_pos >= 900:  # Shorten the track to leave room for the flag
            return "Rossa" if st.session_state.language == "Italiano" else "Red"
        elif st.session_state.car2_pos >= 900:  # Shorten the track to leave room for the flag
            return "Verde" if st.session_state.language == "Italiano" else "Green"
        return None

    def end_race(winner):
        """End the race and show the winner."""
        st.session_state.running = False
        st.session_state.show_retry_popup = True
        st.success(win_message.format(winner))
        show_retry_popup()

        # Calculate the sums for red and green car
        red_car_0s = st.session_state.random_numbers_1.count(0)
        red_car_1s = st.session_state.random_numbers_1.count(1)
        green_car_0s = st.session_state.random_numbers_2.count(0)
        green_car_1s = st.session_state.random_numbers_2.count(1)

        # Calculate the total race time and car speeds
        total_time = time.time() - st.session_state.car_start_time
        red_car_speed = st.session_state.car_pos / total_time
        green_car_speed = st.session_state.car2_pos / total_time

        # Ask the user if they want to save the race data
        save_data = st.radio(save_data_text, (no_option, yes_option), index=0)
        st.write(save_data_info)

        if save_data == yes_option:
            # Save race data to Google Sheets
            race_data = [
                "Italian" if st.session_state.language == "Italiano" else "English",
                st.session_state.player_choice,
                st.session_state.car_pos,
                st.session_state.car2_pos,
                winner,
                total_time,
                st.session_state.api_key != "",
                st.session_state.move_multiplier,  # Save the movement multiplier value
                red_car_0s,
                red_car_1s,
                green_car_0s,
                green_car_1s,
                st.session_state.car1_moves,  # Number of moves by red car
                st.session_state.car2_moves,  # Number of moves by green car
                red_car_speed,  # Speed of the red car
                green_car_speed  # Speed of the green car
            ]
            save_race_data(sheet1, race_data)

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
        st.session_state.show_retry_popup = False
        st.write(reset_game_message)
        display_cars()

    def show_retry_popup():
        """Show popup asking if the user wants to retry."""
        if st.session_state.show_retry_popup:
            try:
                if st.button(retry_text, key=f"retry_button_{st.session_state.widget_key_counter}"):
                    reset_game()
            except Exception:
                pass  # Silence the duplicate widget key exception

    # Connect to Google Sheets
    sheet1 = configure_google_sheets("test")

    if start_button and st.session_state.player_choice is not None:
        st.session_state.running = True
        st.session_state.car_start_time = time.time()
        st.session_state.show_retry_popup = False

    if stop_button:
        st.session_state.running = False

    try:
        while st.session_state.running:
            start_time = time.time()

            # Get random numbers from random.org
            random_bits_1, random_org_success_1 = get_random_bits_from_random_org(
                1000, client
            )
            random_bits_2, random_org_success_2 = get_random_bits_from_random_org(
                1000, client
            )

            if not random_org_success_1 and not random_org_success_2:
                # Only show warning once if random.org fails
                if not st.session_state.warned_random_org:
                    st.session_state.warned_random_org = True

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
                    st.session_state.car2_pos = move_car(
                        st.session_state.car2_pos,
                        st.session_state.move_multiplier
                        * (1 + ((percentile_5_1 - entropy_score_1) / percentile_5_1)),
                    )
                    st.session_state.car1_moves += 1
                elif st.session_state.player_choice == 0 and count_0 > count_1:
                    st.session_state.car2_pos = move_car(
                        st.session_state.car2_pos,
                        st.session_state.move_multiplier
                        * (1 + ((percentile_5_1 - entropy_score_1) / percentile_5_1)),
                    )
                    st.session_state.car1_moves += 1

            if entropy_score_2 < percentile_5_2:
                if st.session_state.player_choice == 1 and count_0 > count_1:
                    st.session_state.car_pos = move_car(
                        st.session_state.car_pos,
                        st.session_state.move_multiplier
                        * (1 + ((percentile_5_2 - entropy_score_2) / percentile_5_2)),
                    )
                    st.session_state.car2_moves += 1
                elif st.session_state.player_choice == 0 and count_1 > count_0:
                    st.session_state.car_pos = move_car(
                        st.session_state.car_pos,
                        st.session_state.move_multiplier
                        * (1 + ((percentile_5_2 - entropy_score_2) / percentile_5_2)),
                    )
                    st.session_state.car2_moves += 1

            display_cars()

            winner = check_winner()
            if winner:
                end_race(winner)
                break

            time_elapsed = time.time() - start_time
            time.sleep(max(REQUEST_INTERVAL - time_elapsed, 0))

        if st.session_state.show_retry_popup:
            show_retry_popup()

    except Exception as e:
        pass  # Silence any other errors

    if download_button:
        # Create DataFrame with "Green Car" and "Red Car" columns and include the chosen bits
        df = pd.DataFrame(
            {
                "Green Car": [
                    "".join(map(str, row))
                    for row in st.session_state.data_for_excel_2
                ],
                "Red Car": [
                    "".join(map(str, row))
                    for row in st.session_state.data_for_excel_1
                ],
                "Green Car Bit Chosen": [st.session_state.player_choice] * len(st.session_state.data_for_excel_2),
                "Red Car Bit Chosen": [1 - st.session_state.player_choice] * len(st.session_state.data_for_excel_1)
            }
        )
        df.to_excel("random_numbers.xlsx", index=False)
        with open("random_numbers.xlsx", "rb") as file:
            st.download_button(
                label=download_data_text,
                data=file,
                file_name="random_numbers.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

    if reset_button:
        reset_game()

if __name__ == "__main__":
    main()

