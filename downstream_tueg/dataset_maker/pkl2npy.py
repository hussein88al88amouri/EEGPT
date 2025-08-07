import os
import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from tqdm import tqdm
from collections import defaultdict

# Path where your .pkl files are stored
ROOT_DIR = "/home/hussein/WorSpace/LBW/TUSZEEG/edf"

# Output directory
OUTPUT_DIR = os.path.join(ROOT_DIR, "processed", "npyfile")
os.makedirs(OUTPUT_DIR, exist_ok=True)

all_eegs = {}
records = []

idx = 0
MAX_PATIENTS = 20  # limit to 30 patients

main_dirs = ["processed", "processed_ecg"]
sub_dirs = ["processed_train", "processed_eval", "processed_dev"]

# Step 1: Group files by patient ID
patient_files = defaultdict(list)

for main_dir in main_dirs:
    for subdir in sub_dirs:
        target_dir = os.path.join(ROOT_DIR, main_dir, subdir)
        print(f'Target directory: {target_dir}')
        if not os.path.exists(target_dir):
            print(f"Skipping non-existent directory: {target_dir}")
            continue

        pkl_files = [f for f in os.listdir(target_dir) if f.endswith(".pkl")]
        print(f"Found {len(pkl_files)} files in {main_dir}/{subdir}")

        for file in pkl_files:
            # Extract patient id (before _s)
            patient_id = file.split('_')[0]
            patient_files[(main_dir, subdir, patient_id)].append(os.path.join(target_dir, file))

print(f"Total unique patients found: {len(patient_files)}")

# Step 2: Select first MAX_PATIENTS unique patients
selected_patients = set()
selected_files = []

for (main_dir, subdir, patient_id), files in patient_files.items():
    if len(selected_patients) >= MAX_PATIENTS:
        break
    if patient_id not in selected_patients:
        selected_patients.add(patient_id)
        selected_files.extend([(main_dir, subdir, file_path) for file_path in files])

print(f"Selected {len(selected_patients)} patients, {len(selected_files)} files total.")

# Step 3: Process the selected files
for main_dir, subdir, file_path in tqdm(selected_files, desc="Processing patient files"):
    file = os.path.basename(file_path)
    try:
        with open(file_path, "rb") as f:
            data = pickle.load(f)
            signal = data["signal"].astype(np.float32)
            label = int(data["label"].item() if hasattr(data["label"], 'item') else data["label"])
    except Exception as e:
        print(f"Failed loading {file_path}: {e}")
        continue

    id_name = f"{main_dir}_{subdir}_{Path(file).stem}_{idx}"
    all_eegs[id_name] = signal
    records.append({
        "id": id_name,
        "file": file,
        "directory": subdir,
        "source": main_dir,
        "class_code": label
    })
    idx += 1

print(f"Saving {len(all_eegs)} EEGs to npy file")
np.save(os.path.join(OUTPUT_DIR, "eegs.npy"), all_eegs)

df = pd.DataFrame(records)
csv_path = os.path.join(OUTPUT_DIR, "seizures.csv")
df.to_csv(csv_path, index=False)

print(f"Saved metadata CSV to {csv_path}")
print(f"Total signals saved: {len(all_eegs)}")
