import pandas as pd
from pathlib import Path

data_dir = Path("data/clean")
parquet_files = list(data_dir.glob("*.parquet"))
latest_file = sorted(parquet_files)[-1]
print(f"Loading {latest_file}")

df = pd.read_parquet(latest_file)

# Search for the event
title = "Mozart, l'œuvre sacrée : Vêpres solennelles d’un confesseur"
event = df[df["title"] == title]

if not event.empty:
    print("Event found:")
    start_dt = event.iloc[0]["start_datetime"]
    print(f"Type of start_datetime: {type(start_dt)}")
    print(f"Value: {start_dt}")
else:
    print("Event not found")
