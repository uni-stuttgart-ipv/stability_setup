import pandas as pd
import json

file_path = r"C:\Users\aleja\Documents\iPV\01-iPV_stability_repo\stability_setup\illumination\SEMIS\Characterization\Current stability study\current_with_intensity_control\current_with_control.csv"
sensor_type_options = ["photodiode", "mini_solar_cell"]
sensor_type = sensor_type_options[int(input("Choose sensor type: [0] photodiode, [1] mini solar cell    "))]  # Set 
convert_to_percentage = True  # Set to True to convert average values to percentage of AM1.5 using the fitted function

if convert_to_percentage:
    if sensor_type == "photodiode":
        sensor_file_path = r"C:\Users\aleja\Documents\iPV\01-iPV_stability_repo\stability_setup\illumination\SEMIS\Characterization\sensor_characterization\photodiode_PROCESSED_steps_cubic_fit.json"
    elif sensor_type == "mini_solar_cell":
        sensor_file_path = r"C:\Users\aleja\Documents\iPV\01-iPV_stability_repo\stability_setup\illumination\SEMIS\Characterization\sensor_characterization\mini_solar_cell_PROCESSED_steps_cubic_fit.json"
    else:
        raise ValueError("Invalid sensor type. Choose either 'photodiode' or 'mini_solar_cell'.")

    with open(sensor_file_path, "r") as f:
        sensor_params = json.load(f)

    a = sensor_params["a"]
    b = sensor_params["b"]
    c = sensor_params["c"]
    if sensor_params["fit_type"] == "cubic":
        d = sensor_params["d"]

df = pd.read_csv(file_path, skiprows=1, header=None, names=['Time', 'Meas1', 'Meas2', 'Meas3', 'Meas4', 'Meas5'])

df['average'] = df[['Meas1', 'Meas2', 'Meas3', 'Meas4', 'Meas5']].mean(axis=1)

# df = pd.read_csv(file_path)

if convert_to_percentage:
    df["percentage of AM1.5"] = df[list(df.columns)[-1]].apply(lambda x: a * x**3 + b * x**2 + c * x + d if sensor_params["fit_type"] == "cubic" else a * x**2 + b * x + c)
    df["percentage of AM1.5"] = df["percentage of AM1.5"].clip(lower=0)  # Ensure values are between 0 and 100

print(df.head())

df.to_csv(file_path.replace(".csv", f"_PROCESSED_{sensor_type}.csv"), index=False)