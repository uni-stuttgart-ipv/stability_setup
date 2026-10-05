import pandas as pd

file_path = r"C:\Users\aleja\Documents\iPV\01-iPV_stability_repo\stability_setup\illumination\SEMIS\Characterization\sensor_characterization\photodiode_PROCESSED.csv"

df = pd.read_csv(file_path)

print(df.head())

THRESHOLD = 100000
time_col = df.columns[0]
value_col = "Meas1"

steps = []
in_step = False
start_time = None
values = []

for _, row in df.iterrows():
    value = row[value_col]
    if value > THRESHOLD:
        if not in_step:
            in_step = True
            start_time = row[time_col]
            values = []
        values.append(value)
        end_time = row[time_col]
    else:
        if in_step:
            steps.append({
                "start of step": start_time,
                "end of step": end_time,
                "average": sum(values) / len(values),
            })
            in_step = False

if in_step:
    steps.append({
        "start of step": start_time,
        "end of step": end_time,
        "average": sum(values) / len(values),
    })

steps_df = pd.DataFrame(steps, columns=["start of step", "end of step", "average"])
print(steps_df)

file_output_name = file_path.replace(".csv", "_steps.csv")

steps_df.to_csv(file_output_name, index=False)