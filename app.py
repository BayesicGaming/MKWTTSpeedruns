import streamlit as st
import tempfile
import pandas as pd
import numpy as np
from process_video import process_video, print_final_time

st.title("Mario Kart World Time Trial Speedrun Video Processor")

st.markdown("Upoad your full video (1080p for now) to extract final times automatically")

# Upload Video
video_file = st.file_uploader("Upload .mp4 video", type = ["mp4"])

if video_file:
    # Save uploaded file to a temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(video_file.read())
        tmp_path = tmp.name

    # Run the tool
    with st.spinner("Processing video... this may take a few minutes"):
        progress_bar = st.progress(0)
        log_placeholder = st.empty()

        def update_progress(pct, msg=None):
            progress_bar.progress(min(pct, 1.0))
            if msg:
                log_placeholder.text(msg)

        df = process_video(tmp_path, progress_callback=update_progress)
        progress_bar.empty()

    st.success=("Processing Copmlete!")

    # Show results
    st.subheader("Extracted Times")
    st.markdown("""
        Here is what each column represents:

        1. **Time** — The extracted time trial time.
        2. **Timestamp (s)** — The point in the video where that time appears.
        3. **Source**: What type of time trial was it (solo, race against ghost win / loss)
    """)
    st.dataframe(df)

    # Show total time
    st.subheader("Total Time")
    st.write(f"Total time of the run is {print_final_time(df)}")

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "times.csv", "text/csv")