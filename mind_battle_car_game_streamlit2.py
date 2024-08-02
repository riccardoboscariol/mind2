import streamlit as st
import time
import numpy as np
import pandas as pd
from PIL import Image
import base64
import io
import os
from rdoclient import RandomOrgClient

# Constants
MAX_BATCH_SIZE = 1000  # Max batch size for requests to random.org
RETRY_LIMIT = 3  # Number of attempts for requests to random.org
REQUEST_INTERVAL = 0.5  # Interval between requests (in seconds)

def validate_api_key(api_key):
    """Verify if the API key is valid by making a test request to random.org."""
    try:
        client = RandomOrgClient(api_key.strip())
        client.generate_integers(1, 0, 1)  # Test request
        return True
    except Exception as e:
        return False

def get_random_bits_from_random_org(num_bits, api_key=None):
    random_bits = []
    attempts = 0
    success = False

    while num_bits > 0 and attempts < RETRY_LIMIT:
        batch_size = min(num_bits, MAX_BATCH_SIZE)

        if api_key:
            try:
                client = RandomOrgClient(api_key.strip())
                random_bits.extend(client.generate_integers(batch_size, 0, 1))
                num_bits -= batch_size
                success = True
            except Exception as e:
                attempts += 1
                if attempts >= RETRY_LIMIT:
                    st.warning(
                        "Problemi con il server di random.org: verrà utilizzato un metodo di generazione pseudorandomico locale."
                    )
                    random_bits.extend(get_local_random_bits(num_bits))
                    break
                time.sleep(2)  # Wait 2 seconds before retrying
        else:
            random_bits.extend(get_local_random_bits(num_bits))
            success = True
            break

    return random_bits, success

def get_local_random_bits(num_bits):
    """Generate pseudorandom bits locally."""
    return list(np.random.randint(0, 2, size=num_bits))

def calculate_entropy(bits):
    """Calculate the Shannon entropy of a list of bits."""
    n = len(bits)
    counts = np.bincount(bits, minlength=2)
    p = counts / n
    p = p[np.nonzero(p)]
    entropy = -np.sum(p * np.log2(p))
    return entropy

def move_car(car_pos, distance):
    """Move the car a certain distance, ensuring it does not exceed the track length."""
    car_pos += distance
    if car_pos > 900:  # Shorten the track to leave space for the flag
        car_pos = 900
    return car_pos

def image_to_base64(image):
    """Convert an image to a base64 string."""
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def main():
    st.set_page_config(page_title="Car Mind Race", layout="wide")
    
    if "language" not in st.session_state:
        st.session_state.language = "Italiano"
    
    # Function to toggle the language
    def toggle_language():
        if st.session_state.language == "Italiano":
            st.session_state.language = "English"
        else:
            st.session_state.language = "Italiano"

    # Button to change the language
    st.sidebar.button("Change Language", on_click=toggle_language)

    # Set text based on the language selected
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

    # Load logo image
    logo_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "logo_A.png")
    logo = Image.open(logo_path)

    # Display logo at the top of the app
    st.image(logo, use_column_width=True)

    st.title(title_text)

    # Add custom CSS for styling
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
            top: -50px;
            width: 20px;
        }
        .flag-image {
            position: absolute;
            top: -100px;
            width: 150px;
            left: 96%;
        }
        .slider-container input[type=range] {
            width: 100%;
        }
        .selected {
            background-color: #4CAF50; /* Green */
            color: white;
        }
        </style>
        """, unsafe_allow_html=True)

    st.markdown(instruction_text)

    # Initialize session state variables if they do not exist
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

    st.sidebar.title("Menu")
    if st.session_state.player_choice is None:
        start_button = st.sidebar.button(start_race_text, key="start_button", disabled=True)
    else:
        start_button = st.sidebar.button(start_race_text, key="start_button")
    stop_button = st.sidebar.button(stop_race_text, key="stop_button")
    
    # Input for API key with conditional validation message
    api_key = st.sidebar.text_input(api_key_text, key="api_key", value="")

    # Validate API key only if it is not empty
    if api_key:
        if not validate_api_key(api_key):
            st.warning("Chiave API non valida o il server di random.org non è accessibile.")

    st.sidebar.markdown(api_description_text)

    download_menu = st.sidebar.expander("Download")
    with download_menu:
        download_button = st.button(download_data_text, key="download_button")
    reset_button = st.sidebar.button(reset_game_text, key="reset_button")

    move_multiplier = st.sidebar.slider(move_multiplier_text, min_value=1, max_value=100, value=20, key="move_multiplier")

    image_dir = os.path.abspath(os.path.dirname(__file__))
    car_image = Image.open(os.path.join(image_dir, "car.png")).resize((150, 150))  # Red car
    car2_image = Image.open(os.path.join(image_dir, "car2.png")).resize((150, 150))  # Green car
    flag_image = Image.open(os.path.join(image_dir, "bandierina.png")).resize((150, 150))  # Flag

    # Load number images and resize them to 20x20 pixels
    number_0_green_image = Image.open(os.path.join(image_dir, "0green.png")).resize((20, 20))
    number_1_green_image = Image.open(os.path.join(image_dir, "1green.png")).resize((20, 20))
    number_0_red_image = Image.open(os.path.join(image_dir, "0red.png")).resize((20, 20))
    number_1_red_image = Image.open(os.path.join(image_dir, "1red.png")).resize((20, 20))

    st.write(choose_bit_text)

    # Initialize the number images with default values
    green_car_number_image = number_0_green_image
    red_car_number_image = number_1_red_image

    # Create buttons for selecting bits and highlight the selected one
    col1, col2 = st.columns(2)
    with col1:
        button1_style = "selected" if st.session_state.player_choice == 1 else ""
        if st.button("Scegli 1", key="button1", help="Selects bit 1 for the green car", args=None):
            st.session_state.player_choice = 1
            st.session_state.green_car_number_image = number_1_green_image
            st.session_state.red_car_number_image = number_0_red_image
    with col2:
        button0_style = "selected" if st.session_state.player_choice == 0 else ""
        if st.button("Scegli 0", key="button0", help="Selects bit 0 for the green car", args=None):
            st.session_state.player_choice = 0
            st.session_state.green_car_number_image = number_0_green_image
            st.session_state.red_car_number_image = number_1_red_image

    # Apply button styles
    st.markdown(f"""
    <style>
        #button1 {{background-color: {"#4CAF50" if button1_style else "#f0f0f0"}; color: {"white" if button1_style else "black"};}}
        #button0 {{background-color: {"#4CAF50" if button0_style else "#f0f0f0"}; color: {"white" if button0_style else "black"};}}
    </style>
    """, unsafe_allow_html=True)

    # Assign the chosen images if a choice was made
    if st.session_state.player_choice is not None:
        green_car_number_image = st.session_state.green_car_number_image
        red_car_number_image = st.session_state.red_car_number_image

    # Convert images to base64 for display in HTML
    car_image_base64 = image_to_base64(car_image)
    car2_image_base64 = image_to_base64(car2_image)
    flag_image_base64 = image_to_base64(flag_image)
    red_car_number_base64 = image_to_base64(red_car_number_image)
    green_car_number_base64 = image_to_base64(green_car_number_image)

    car_placeholder = st.empty()
    car2_placeholder = st.empty()

    # Display cars with number images
    def display_cars():
        car_placeholder.markdown(f"""
            <div class="slider-container first">
                <img src="data:image/png;base64,{car_image_base64}" class="car-image" style="left:{st.session_state.car_pos / 10}%">
                <img src="data:image/png;base64,{red_car_number_base64}" class="number-image" style="left:{st.session_state.car_pos / 10 - 1.5}%">
                <input type="range" min="0" max="1000" value="{st.session_state.car_pos}" disabled>
                <img src="data:image/png;base64,{flag_image_base64}" class="flag-image">
            </div>
        """, unsafe_allow_html=True)

        car2_placeholder.markdown(f"""
            <div class="slider-container">
                <img src="data:image/png;base64,{car2_image_base64}" class="car-image" style="left:{st.session_state.car2_pos / 10}%">
                <img src="data:image/png;base64,{green_car_number_base64}" class="number-image" style="left:{st.session_state.car2_pos / 10 - 1.5}%">
                <input type="range" min="0" max="1000" value="{st.session_state.car2_pos}" disabled>
                <img src="data:image/png;base64,{flag_image_base64}" class="flag-image">
            </div>
        """, unsafe_allow_html=True)

    display_cars()

    def check_winner():
        """Check if there's a winner based on car positions."""
        if st.session_state.car_pos >= 900:  # Red car wins
            return "Rossa"
        elif st.session_state.car2_pos >= 900:  # Green car wins
            return "Verde"
        return None

    def end_race(winner):
        """End the race and announce the winner."""
        st.session_state.running = False
        st.session_state.show_end_buttons = True
        st.success(win_message.format(winner))
        show_end_buttons()

    def reset_game():
        """Reset the game to its initial state."""
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

    def show_end_buttons():
        """Show buttons for starting a new race or ending the game."""
        key_suffix = st.session_state.widget_key_counter
        col1, col2 = st.columns(2)
        with col1:
            if st.button(new_race_text, key=f"new_race_button_{key_suffix}"):
                reset_game()
        with col2:
            if st.button(end_game_text, key=f"end_game_button_{key_suffix}"):
                st.stop()

    if start_button and st.session_state.player_choice is not None:
        st.session_state.running = True
        st.session_state.car_start_time = time.time()
        st.session_state.show_end_buttons = False

    if stop_button:
        st.session_state.running = False

    try:
        while st.session_state.running:
            start_time = time.time()

            # Obtain random numbers from random.org
            random_bits_1, success1 = get_random_bits_from_random_org(1000, api_key)
            random_bits_2, success2 = get_random_bits_from_random_org(1000, api_key)

            if not (success1 and success2):
                st.session_state.running = False
                st.write(error_message)
                show_end_buttons()
                break

            # Append random numbers and data for Excel
            st.session_state.random_numbers_1.extend(random_bits_1)
            st.session_state.random_numbers_2.extend(random_bits_2)
            
            st.session_state.data_for_excel_1.append(random_bits_1)
            st.session_state.data_for_excel_2.append(random_bits_2)
            
            # Calculate entropy for each set of random numbers
            entropy_score_1 = calculate_entropy(random_bits_1)
            entropy_score_2 = calculate_entropy(random_bits_2)
            
            st.session_state.data_for_condition_1.append(entropy_score_1)
            st.session_state.data_for_condition_2.append(entropy_score_2)
            
            percentile_5_1 = np.percentile(st.session_state.data_for_condition_1, 5)
            percentile_5_2 = np.percentile(st.session_state.data_for_condition_2, 5)

            # Count occurrences of 1s and 0s
            count_1 = sum(random_bits_1)
            count_0 = len(random_bits_1) - count_1

            # Move the green car if the conditions are met
            if entropy_score_1 < percentile_5_1:
                if st.session_state.player_choice == 1 and count_1 > count_0:
                    st.session_state.car2_pos = move_car(st.session_state.car2_pos, move_multiplier * (1 + ((percentile_5_1 - entropy_score_1) / percentile_5_1)))
                    st.session_state.car1_moves += 1
                elif st.session_state.player_choice == 0 and count_0 > count_1:
                    st.session_state.car2_pos = move_car(st.session_state.car2_pos, move_multiplier * (1 + ((percentile_5_1 - entropy_score_1) / percentile_5_1)))
                    st.session_state.car1_moves += 1

            # Move the red car if the conditions are met
            if entropy_score_2 < percentile_5_2:
                if st.session_state.player_choice == 1 and count_0 > count_1:
                    st.session_state.car_pos = move_car(st.session_state.car_pos, move_multiplier * (1 + ((percentile_5_2 - entropy_score_2) / percentile_5_2)))
                    st.session_state.car2_moves += 1
                elif st.session_state.player_choice == 0 and count_1 > count_0:
                    st.session_state.car_pos = move_car(st.session_state.car_pos, move_multiplier * (1 + ((percentile_5_2 - entropy_score_2) / percentile_5_2)))
                    st.session_state.car2_moves += 1

            # Display cars and check for a winner
            display_cars()

            winner = check_winner()
            if winner:
                end_race(winner)
                break

            # Ensure the loop respects the request interval
            time_elapsed = time.time() - start_time
            time.sleep(max(REQUEST_INTERVAL - time_elapsed, 0))

        # Show end buttons if the race is finished
        if st.session_state.show_end_buttons:
            show_end_buttons()

    except Exception as e:
        st.error(f"Si è verificato un errore: {e}")

    # Handle download button click
    if download_button:
        # Create a DataFrame with columns "Macchina verde" and "Macchina rossa"
        df = pd.DataFrame({
            "Macchina verde": [''.join(map(str, row)) for row in st.session_state.data_for_excel_1],
            "Macchina rossa": [''.join(map(str, row)) for row in st.session_state.data_for_excel_2]
        })
        df.to_excel("random_numbers.xlsx", index=False)
        with open("random_numbers.xlsx", "rb") as file:
            st.download_button(
                label=download_data_text,
                data=file,
                file_name="random_numbers.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # Reset the game when reset button is clicked
    if reset_button:
        reset_game()

if __name__ == "__main__":
    main()

