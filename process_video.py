import cv2
import pytesseract
import re
import pandas as pd
from datetime import timedelta

def extract_time(text):
    match = re.search(r"\d:\d{2}\.\d{3}", text)
    return match.group(0) if match else None


def is_blue_pixel(bgr):
    b, g, r = bgr
    return b > 150 and g < 100 and r < 100  # Rough threshold for blue

def time_str_to_seconds(time_str):
    mins, rest = time_str.split(":")
    secs, millis = rest.split(".")
    return int(mins) * 60 + int(secs) + int(millis) / 1000

def process_video(video_path, progress_callback=None):
    # When running the function, replace output_csv with a path to
    # output the results

    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    duration_sec = cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps

    # Makes sure that if the last time is the same as the
    # time the program just found, then it's a duplicate
    last_time = None
    results = []

    current_time_sec = 0
    step_if_no_time = 1
    step_if_time_found = 60.0

    # Base resolution for reference (full HD)
    BASE_WIDTH = 1920
    BASE_HEIGHT = 1080

    # If you are running solo, only one text box will appear
    # If you are racing a ghost, two text boxes will appear, with
    #   the top time being the faster time and the bottom time being
    #   the slower time
    roi_percent = {
        "top": (1252 / BASE_WIDTH, 360 / BASE_HEIGHT, 1575 / BASE_WIDTH, 438 / BASE_HEIGHT),
        "bottom": (1252 / BASE_WIDTH, 563 / BASE_HEIGHT, 1575 / BASE_WIDTH, 641 / BASE_HEIGHT),
        "solo": (1250 / BASE_WIDTH, 410 / BASE_HEIGHT, 1580 / BASE_WIDTH, 500 / BASE_HEIGHT)
    }

    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    roi_coords = {}
    for key, (x1p, y1p, x2p, y2p) in roi_percent.items():
        x1 = int(x1p * actual_width)
        y1 = int(y1p * actual_height)
        x2 = int(x2p * actual_width)
        y2 = int(y2p * actual_height)
        roi_coords[key] = (x1, y1, x2, y2)

    # The ghost will always have a blue border, and your current run
    #   will always have a yellow border
    border_pixel_coords = (
        int(1108 / BASE_WIDTH * actual_width), 
        int(436 * BASE_HEIGHT / actual_height)
    )     

    while current_time_sec < duration_sec:
        # Increments seconds and sets current frame to the respective time
        cap.set(cv2.CAP_PROP_POS_MSEC, current_time_sec * 1000)

        # If your current time is beyond the duration of the video, there is
        # no frame so ret will be False and frame will be None
        ret, frame = cap.read()
        if not ret:
            break

        timestamp_sec = round(current_time_sec, 2)
        if progress_callback:
            progress_callback(current_time_sec / duration_sec)

        # Extracts the portion of the frame corresponding to the top box region of interest, 
        #  bottom box region of interest, and solo box region of interest
        top_roi = frame[roi_coords["top"][1]:roi_coords["top"][3], roi_coords["top"][0]:roi_coords["top"][2]]
        bottom_roi = frame[roi_coords["bottom"][1]:roi_coords["bottom"][3], roi_coords["bottom"][0]:roi_coords["bottom"][2]]
        solo_roi = frame[roi_coords["solo"][1]:roi_coords["solo"][3], roi_coords["solo"][0]:roi_coords["solo"][2]]

        # If text is found in the ROI, then the image will be converted to text, otherwise will be None
        top_text = pytesseract.image_to_string(cv2.cvtColor(top_roi, cv2.COLOR_BGR2RGB), config='--psm 7')
        bottom_text = pytesseract.image_to_string(cv2.cvtColor(bottom_roi, cv2.COLOR_BGR2RGB), config='--psm 7')
        solo_text = pytesseract.image_to_string(cv2.cvtColor(solo_roi, cv2.COLOR_BGR2RGB), config='--psm 7')

        top_time = extract_time(top_text)
        bottom_time = extract_time(bottom_text)
        solo_time = extract_time(solo_text)

        player_time = None
        source = None

        # If both top and bottom times are populated, then you're racing a 
        #  ghost. Now need to check if the border color is blue or not
        if top_time and bottom_time:
            # If the border is blue, then use the bottom box, otherwise use
            #  the top box
            pixel_bgr = frame[border_pixel_coords[1], border_pixel_coords[0]]
            if is_blue_pixel(pixel_bgr):
                player_time = bottom_time
                source = "Race against ghost (lost)"
            else:
                player_time = top_time
                source = "Race against ghost (won)"
        elif solo_time:
            player_time = solo_time
            source = "Solo run (no ghost)"

        # If we found a time on the current frame and it's different from the last
        #  time we found, then add it to a dataframe
        if player_time and player_time != last_time:
            results.append({"Time": player_time, "Timestamp (s)": timestamp_sec, "Source": source})
            print(f"Detected time: {player_time} at {timestamp_sec} sec (source: {source})")
            last_time = player_time
            current_time_sec += step_if_time_found
        else:
            current_time_sec += step_if_no_time

    cap.release()

    df = pd.DataFrame(results)
    return df

def print_final_time(df):
    # Step 1: Convert all times to seconds
    df["Seconds"] = df["Time"].apply(time_str_to_seconds)

    # Step 2: Sum total time in seconds
    total_seconds = float(df["Seconds"].sum())

    # Step 3: Format as HH:MM:SS.xxx
    total_td = timedelta(seconds=total_seconds)
    hours, remainder = divmod(total_td.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = round((seconds % 1) * 1000)

    formatted_total = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}.{int(milliseconds):03}"
    return f"Total Time: {formatted_total}"