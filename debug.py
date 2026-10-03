# debug.py
import pandas as pd

df = pd.read_csv('dramas.csv')

# Search for Han Jae-in
print("Searching for 'Han Jae-in' in cast column:")
for i, row in df.iterrows():
    if 'Han Jae' in str(row['cast']):
        print(f"Found: {row['title']} - Cast: {row['cast']}")