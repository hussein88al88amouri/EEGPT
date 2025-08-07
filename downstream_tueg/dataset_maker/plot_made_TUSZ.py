import streamlit as st
import os
import pickle
from pathlib import Path
import plotly.graph_objs as go
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

st.set_page_config(page_title="Signal Segment Viewer", layout="wide")

st.title("Signal Segment Viewer")

ROOT_DIR = st.text_input(
    "Enter Root Directory:",
    value="/home/hussein/WorSpace/LBW/TUSZEEG/edf/",  # Default example
    help="The base directory where signal files are stored. It should contain the follwoing subdirectories processed_train, processed_dev, and processed_eval."
)

SAMPLING_RATE = st.number_input(
    "Enter Sampling Rate (Hz):",
    min_value=1,
    max_value=5000,
    value=256,
    step=1,
    help="Sampling rate of the signals in Hz."
)

overlap_percentage = st.number_input(
    "Percentage of overlap:",
    min_value=0,
    max_value=100,
    value=33,
    step=1,
    help="Sampling rate of the signals in Hz."
)

@st.cache_data
def list_files_by_structure(root_dir):
    seen = set()
    files = []
    for root, _, file_list in os.walk(root_dir):
        for f in file_list:
            if f.endswith(".pkl") or f.endswith(".signal_csv"):
                base = f.replace(".pkl", "").replace(".signal_csv", "")
                full_path = os.path.join(root, base)
                rel_path = os.path.relpath(full_path, root_dir)
                if rel_path not in seen:
                    files.append(rel_path)
                    seen.add(rel_path)
    return sorted(files)

@st.cache_data
def load_signal(base_file_path):
    """
    Loads a signal and label from either:
    - Pickle file: base_file_path.pkl
    - CSV files: base_file_path.signal_csv and base_file_path.label_csv
    Returns: dict with keys "signal" and "label"
    """
    pkl_path = base_file_path + ".pkl"
    csv_signal_path = base_file_path + ".signal_csv"
    csv_label_path = base_file_path + ".label_csv"

    if os.path.exists(pkl_path):
        with open(pkl_path, "rb") as f:
            return pickle.load(f)
    elif os.path.exists(csv_signal_path) and os.path.exists(csv_label_path):
        signal = np.loadtxt(csv_signal_path, delimiter=",")
        if signal.ndim == 1:
            signal = signal[np.newaxis, :]  # Make it 2D if single channel
        with open(csv_label_path, 'r') as f:
            label = int(float(f.readline().strip()))
        return {"signal": signal, "label": label}
    else:
        raise FileNotFoundError(f"Could not find data for base: {base_file_path}")

@st.cache_data
def safe_segment_sort_key(segment):
    try:
        return int(segment)
    except:
        return float('inf')

def parse_parts(file_path):
    filename = Path(file_path).stem
    parts = filename.split('_')
    patient = parts[0]
    session = parts[1] if len(parts) > 1 else ""
    trim_seg = parts[2] if len(parts) > 2 else ""
    trim = trim_seg.split('-')[0] if '-' in trim_seg else trim_seg
    segment = trim_seg.split('-')[1].split('.')[0] if '-' in trim_seg else "0"
    return patient, session, trim, int(segment)

def order_list_of_files(listoffiles):
    def get_segment_number_key(filename):
        return parse_parts(filename)[3]
    return sorted(listoffiles, key=get_segment_number_key)

main_dirs = [d for d in os.listdir(ROOT_DIR) if os.path.isdir(os.path.join(ROOT_DIR, d))]
main_dir = st.selectbox("Select Main Directory:", main_dirs)

sub_options = ["processed_train", "processed_eval", "processed_dev"]
sub_dir = st.selectbox("Select Subdirectory:", sub_options)

selected_root = os.path.join(ROOT_DIR, main_dir, sub_dir)
all_files = list_files_by_structure(selected_root)

patients = sorted({parse_parts(f)[0] for f in all_files})
selected_patient = st.selectbox("Select Patient:", patients)

files_patient = [f for f in all_files if parse_parts(f)[0] == selected_patient]

sessions = sorted({parse_parts(f)[1] for f in files_patient})
selected_session = st.selectbox("Select Session:", sessions)

files_session = [f for f in files_patient if parse_parts(f)[1] == selected_session]

trims = sorted({parse_parts(f)[2] for f in files_session})
selected_trim = st.selectbox("Select Trim:", trims)

files_trim = [f for f in files_session if parse_parts(f)[2] == selected_trim]

segments = sorted({parse_parts(f)[3] for f in files_trim}, key=safe_segment_sort_key)

# --- Segment input
num_segments_to_plot = st.number_input("Choose or enter custom segment count:", min_value=1, value=9, step=1)

# --- Segment batching
segment_batches = [f"{i}-{i+num_segments_to_plot-1}" for i in range(0, len(segments), num_segments_to_plot)]
selected_batch = st.selectbox("Select Segment Batch:", segment_batches)
start_idx = int(selected_batch.split('-')[0])
end_idx = int(selected_batch.split('-')[1])
selected_segments = segments[start_idx:end_idx + 1]

final_files = [f for f in files_trim if parse_parts(f)[3] in selected_segments]
final_files = order_list_of_files(final_files)

st.markdown(f"### {len(final_files)} Segments Selected and Will Be Plotted")

if final_files:
    fig = go.Figure()
    cumulative_sec = 0
    seizure_regions = []
    summary = []
    segment_start_times = []

    should_save_plot = False

    for idx, rel_file in enumerate(final_files):
        full_path = os.path.join(selected_root, rel_file)
        data = load_signal(full_path)
        signal, label = data["signal"], int(data["label"])

        channels, samples = signal.shape
        duration_sec = samples / SAMPLING_RATE
        times = (np.arange(samples) / SAMPLING_RATE) + cumulative_sec

        # Plot check size
        if len(final_files) * channels * samples > 100_000_000:
            should_save_plot = True

        for ch in range(channels):
            fig.add_trace(go.Scattergl(
                x=times,
                y=signal[ch] + ch * 100,
                mode='lines',
                line=dict(color='blue', width=1),
                hoverinfo='skip',
                showlegend=False
            ))

        if label == 1:
            seizure_regions.append((cumulative_sec, cumulative_sec + duration_sec))

        segment_start_times.append((cumulative_sec, cumulative_sec + duration_sec))

        patient, session, trim, segment = parse_parts(rel_file)
        summary.append({
            "Patient": patient,
            "Session": session,
            "Trim": trim,
            "Segment": segment,
            "Channels": channels,
            "Samples": samples,
            "Duration (s)": duration_sec,
            "Label": label
        })

        overlap_sec = duration_sec * (overlap_percentage / 100)
        cumulative_sec += duration_sec - overlap_sec

    for start, end in seizure_regions:
        fig.add_vrect(x0=start, x1=end, fillcolor="red", opacity=0.2, line_width=0)

    for seg_start, seg_end in segment_start_times:
        fig.add_vline(x=seg_start, line=dict(color="green", width=1, dash="dash"))
        fig.add_vline(x=seg_end, line=dict(color="green", width=1, dash="dash"))

    fig.update_layout(
        height=700,
        dragmode='pan',
        hovermode=False,
        showlegend=False,
        xaxis_title="Time (seconds)",
        yaxis_title="Amplitude + Channel Offset (uV)",
        title=f"EEG from {main_dir}/{sub_dir} | {selected_patient}",
        uirevision=True
    )

    if should_save_plot or st.checkbox("Save plot as PDF (if too large for browser)?"):
        st.warning("Plot too large or user requested export. Saving as PDF...")
        pdf_path = os.path.join("/tmp", f"eeg_plot_{selected_patient}.pdf")
        plt.figure(figsize=(20, 10))
        for ch in range(signal.shape[0]):
            plt.plot(times, signal[ch] + ch * 100, linewidth=0.5)
        plt.xlabel("Time (s)")
        plt.ylabel("Amplitude (uV)")
        plt.tight_layout()
        plt.savefig(pdf_path)
        st.success(f"Plot saved as PDF at: {pdf_path}")
    else:
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Summary Table")
    st.dataframe(pd.DataFrame(summary))
else:
    st.info("No segments selected.")
