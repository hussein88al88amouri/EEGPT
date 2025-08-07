import os
import pickle
import warnings
import argparse
from tqdm import tqdm

import mne
import numpy as np
import pandas as pd

from montage_maps import REQUIRED_CHANNELS_LE, REQUIRED_CHANNELS_REF, MONTAGE_MAP_LE, MONTAGE_MAP_REF, EKG_CHANNEL

# ---- Annotation ----
def parse_csv_annotations(csv_file):
    try:
        df = pd.read_csv(csv_file, sep=",", comment='#', skip_blank_lines=True)
        df.columns = ['channel', 'start_time', 'stop_time', 'label', 'confidence']
        df = df[['start_time', 'stop_time', 'label']]
        df = df[df['label'].isin(['seiz', 'bckg'])]
        df['label'] = df['label'].map({'seiz': 1, 'bckg': 0})
        return df.reset_index(drop=True)
    except (pd.errors.ParserError, ValueError) as e:
        print(f"Error parsing file {csv_file}: {e}")
        return pd.DataFrame()


# ---- Signal Preprocessing ----
def read_and_preprocess_raw(file_path, montage_type, fs):
    Rawdata = mne.io.read_raw_edf(file_path, preload=True)
    Rawdata = drop_and_reorder_channels(Rawdata, montage_type)
    Rawdata = filter_and_resample(Rawdata, fs)
    return Rawdata


def drop_and_reorder_channels(Rawdata, montage_type):
    if montage_type == 'ar':
        chOrder_standard = REQUIRED_CHANNELS_REF
    elif montage_type == 'le':
        chOrder_standard = REQUIRED_CHANNELS_LE
    elif montage_type == 'ecg':
        chOrder_standard = [EKG_CHANNEL]
        
    print(f'{"*"*10}\nWorking with the following channels\n{chOrder_standard}\n{"*"*10}')
    drop_channels = list(set(Rawdata.ch_names) - set(chOrder_standard))
    Rawdata.drop_channels(drop_channels)
    Rawdata.reorder_channels(chOrder_standard)
    if Rawdata.ch_names != chOrder_standard:
        raise ValueError("Channel order mismatch after reordering.")
    return Rawdata


def filter_and_resample(Rawdata, fs):
    with warnings.catch_warnings():
        warnings.filterwarnings("error", category=RuntimeWarning)
        Rawdata.filter(l_freq=0.1, h_freq=75.0)
        Rawdata.notch_filter(50.0)
        Rawdata.resample(fs, n_jobs=5)
    return Rawdata


def convert_signals(signals, Rawdata, montage_type):
    if montage_type == 'ecg':
        return signals
    elif montage_type == 'ar':
        montage_map = MONTAGE_MAP_REF
    elif montage_type == 'le':
        montage_map = MONTAGE_MAP_LE

    ch_names = Rawdata.info["ch_names"]
    signal_indices = {ch: idx for idx, ch in enumerate(ch_names)}

    new_signals = []
    for pair_name, (ch1, ch2) in montage_map.items():
        idx1, idx2 = signal_indices[ch1], signal_indices[ch2]
        new_signals.append(signals[idx1] - signals[idx2])

    return np.vstack(new_signals)


# ---- Event Processing ----
def generate_event_windows_generator(event_df, total_duration, windowInSec, overlap):
    """
    Generator that yields (start_time, end_time, label) for each window.
    total_duration: total recording duration in seconds (e.g., times[-1])
    """
    step = windowInSec * (1 - overlap)
    start = 0.0
    while start + windowInSec <= total_duration:
        end = start + windowInSec
        overlapping = event_df[(event_df['start_time'] < end) & (event_df['stop_time'] > start)]
        label = 1 if (overlapping['label'] == 1).any() else 0
        yield start, end, label
        start += step

def BuildEvents(signals, times, event_window_generator, fs):
    """
    Extracts continuous or overlapping windows from signals and labels them
    according to overlap with event_data, using a generator to save memory.
    """
    print('Building Events')

    features, labels = [], []
    total_samples = signals.shape[1]

    for start_time, end_time, label in event_window_generator:
        start_idx = int(start_time * fs)
        end_idx = int(end_time * fs)

        # Safety check: skip if window exceeds signal length
        if end_idx > total_samples:
            print(f"Skipping window from {start_time} to {end_time} (exceeds total samples)")
            continue

        window = signals[:, start_idx:end_idx]
        features.append(window)

        # print(f"Start Time (sec): {start_time:.2f}, End Time (sec): {end_time:.2f}, Label: {label}")
        # print(f"Start Time (actual): {times[start_idx]:.3f}, End Time (actual): {times[end_idx]:.3f}")

        labels.append(label)

    features = np.stack(features)
    labels = np.array(labels).reshape(-1, 1)
    offending_channels = np.zeros((features.shape[0], 1))
    return features, offending_channels, labels


def process_single_file(file_path, out_dir, windowInSec, fs, overlap, save_ecg_only=False, save_csv=False):

    print('-.-'*20)
    print(f'Laoding file: {file_path}')

    base_name = os.path.basename(file_path).split(".")[0]
    if save_ecg_only:
        montage_type = 'ecg'
    elif 'tcp_ar' in file_path:
        montage_type = 'ar'
    elif 'tcp_le' in file_path:
        montage_type = 'le'
    print(f'Montage type {montage_type}')

    Rawdata = read_and_preprocess_raw(file_path, montage_type, fs)
    signals, times = Rawdata.get_data(units='uV'), Rawdata.times
    signals = convert_signals(signals, Rawdata, montage_type)
    total_duration = times[-1]

    event_df = parse_csv_annotations(file_path.replace(".edf", ".csv_bi"))

    event_window_generator = generate_event_windows_generator(
        event_df, total_duration, windowInSec, overlap
    )

    features, offending_channels, labels = BuildEvents(
        signals, times, event_window_generator, fs
    )

    for idx, (feature, offending_channel, label) in enumerate(zip(features, offending_channels, labels)):
        sample = {"signal": feature, "offending_channel": offending_channel, "label": label}
        save(sample, out_dir, base_name, idx, save_csv)

    print(f"Processed {file_path}: {features.shape[0]} samples")
    print('-.-'*20)


# ---- Directory Walk ----
def load_up_objects(BaseDir, OutDir, windowInSec, fs, overlap, save_ecg_only=True, save_csv=False):

    # For tracking faild loading of patients edf files
    print()
    print('Preprocessing is starting: ...')
    print(f'Failed processing will be saved to {OutDir}/faild_paitents_log.txt')
    open(f'{OutDir}/faild_paitents_log.txt', 'w').close()
    print('---'*20)

    for dirName, subdirList, fileList in tqdm(os.walk(BaseDir)):
        if 'tcp_le' not in dirName:
            print(f"Found directory: {dirName}")
            for fname in fileList:
                if fname.endswith(".edf"):
                    file_path = os.path.join(dirName, fname)
                    try:
                        process_single_file(file_path, OutDir, windowInSec, fs, overlap, save_ecg_only=save_ecg_only, save_csv=save_csv)
                    except Exception as e:
                        print(f"Failed processing {file_path}: {e}")
                        record_id = os.path.basename(file_path).split(".")[0]
                        with open(f'{OutDir}/faild_paitents_log.txt', 'a') as f:
                            f.write(f"{record_id}, {e}\n")


# ---- Save Utility ----
def save(obj, out_dir, base_name, idx, save_csv):
    filename = os.path.join(out_dir, f"{base_name}-{idx}")
    if not save_csv:
         save_pickle(obj, filename)
    else:
         save_csv(obj, filename)


def save_pickle(obj, filename):
    with open(f"{filename}.pkl", "wb") as f:
        pickle.dump(obj, f)


def save_csv(obj, filename):
    signal = obj.get("signal")
    label = obj.get("label")

    np.savetxt(f"{filename}.signal_csv", signal, delimiter=",")

    if isinstance(label, np.ndarray) and label.ndim > 0:
        label = label[0]
        with open(f"{filename}.label_csv", 'w') as f:
            f.write(f"{label}\n")    


# ---- Main Routine ----
def main(args):
    root = args.root_dir
    processed_dir = os.path.join(root, args.processed_name)
    
    # Create output folders
    os.makedirs(os.path.join(processed_dir, "processed_train"), exist_ok=True)
    os.makedirs(os.path.join(processed_dir, "processed_eval"), exist_ok=True)
    os.makedirs(os.path.join(processed_dir, "processed_dev"), exist_ok=True)

    fs = args.fs
    windowInSec = args.window
    overlap = args.overlap
    save_ecg_only = args.save_ecg_only
    save_csv = args.save_csv

    load_up_objects(os.path.join(root, "train"), os.path.join(processed_dir, "processed_train"), windowInSec, fs, overlap, save_ecg_only, save_csv)
    load_up_objects(os.path.join(root, "eval"), os.path.join(processed_dir, "processed_eval"), windowInSec, fs, overlap, save_ecg_only, save_csv)
    load_up_objects(os.path.join(root, "dev"), os.path.join(processed_dir, "processed_dev"), windowInSec, fs, overlap, save_ecg_only, save_csv)

def get_args():
    Flag = False # For debugging on my workstation. It should be True as every argument is required.

    parser = argparse.ArgumentParser(description="Preprocess EEG/ECG data with windowing and overlap.")
    
    parser.add_argument(
        "--root_dir", type=str, default="/home/hussein/WorSpace/LBW/TUSZEEG/edf/", required=Flag,
        help="Root directory containing the train/eval/dev folders."
    )
    parser.add_argument(
        "--processed_name", type=str, default="processed_eeg_2_np", required=Flag,
        help="Name of the processed output directory to be created inside the root_dir."
    )
    parser.add_argument(
        "--fs", type=int, default=256, required=Flag,
        help="Sampling frequency of the signal."
    )
    parser.add_argument(
        "--window", type=int, default=10, required=Flag,
        help="Window size in seconds."
    )
    parser.add_argument(
        "--overlap", type=float, default=0.2, required=Flag,
        help="Overlap between windows (as a float between 0 and 1)."
    )
    parser.add_argument(
        "--save_csv", required=Flag, default=True, action='store_false',
        help="If False a dict like file is saved using pickle. The dict is {'signal':, 'offending_channel':, 'label':} (compatible with EEGPT).\
        \nIf True the signal segment is saved in .signal_csv and label is saved in .label_csv."
    )
    parser.add_argument(
        "--save_ecg_only", required=Flag, default=False, action='store_true',
        help="Save only the ECG channel if True, else save the EEG montage only according to LE or AR system."
    )
    
    return parser.parse_args()

if __name__ == "__main__":
    args = get_args()
    main(args)
