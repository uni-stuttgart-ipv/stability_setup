import pandas as pd

from scipy.optimize import curve_fit
import numpy as np
import plotly.graph_objects as go

import json

file_path = r"C:\Users\aleja\Documents\iPV\01-iPV_stability_repo\stability_setup\illumination\SEMIS\Characterization\sensor_characterization\photodiode_PROCESSED_steps.csv"

df = pd.read_csv(file_path)

def quadratic(x, a, b, c):
	return a * x**2 + b * x + c


def quadratic_vertex_origin(x, a):
	return a * x**2


def cubic(x, a, b, c, d):
	return a * x**3 + b * x**2 + c * x + d


def cubic_vertex_origin(x, a):
	return a * x**3


# Specify your columns here
x_col = "average"
y_col = "percentage of AM1.5"
fit_type = "cubic"  # options: "quadratic", "cubic"
force_vertex_origin = False

x = pd.to_numeric(df[x_col], errors="coerce")
y = pd.to_numeric(df[y_col], errors="coerce")

mask = x.notna() & y.notna()
x_data = x[mask].to_numpy(dtype=float)
y_data = y[mask].to_numpy(dtype=float)

if fit_type == "cubic":
	if force_vertex_origin:
		params, _ = curve_fit(cubic_vertex_origin, x_data, y_data)
		a = params[0]
		b = 0.0
		c = 0.0
		d = 0.0
	else:
		params, _ = curve_fit(cubic, x_data, y_data)
		a, b, c, d = params

	def fit_func(x):
		return cubic(x, a, b, c, d)

	fit_label = f"y = {a:.6g}*x^3 + {b:.6g}*x^2 + {c:.6g}*x + {d:.6g}"
elif fit_type == "quadratic":
	if force_vertex_origin:
		params, _ = curve_fit(quadratic_vertex_origin, x_data, y_data)
		a = params[0]
		b = 0.0
		c = 0.0
	else:
		params, _ = curve_fit(quadratic, x_data, y_data)
		a, b, c = params

	def fit_func(x):
		return quadratic(x, a, b, c)

	fit_label = f"y = {a:.6g}*x^2 + {b:.6g}*x + {c:.6g}"
else:
	raise ValueError(f"Unknown fit_type: {fit_type}")

y_fit = fit_func(x_data)
mse = np.mean((y_data - y_fit) ** 2)

print(f"{fit_type.capitalize()} fit for {y_col} vs {x_col}:")
print(fit_label)
print(f"MSE: {mse:.6g}")


x_fit = np.linspace(0, np.max(x_data), 500)
y_fit_curve = fit_func(x_fit)

fig = go.Figure()
fig.add_trace(
	go.Scatter(
		x=x_data,
		y=y_data,
		mode="markers",
		name="Original data",
	)
)
fig.add_trace(
	go.Scatter(
		x=x_fit,
		y=y_fit_curve,
		mode="lines",
		name=f"{fit_type.capitalize()} fit",
	)
)
fig.update_layout(
	title=f"{y_col} vs {x_col} with {fit_type.capitalize()} Fit",
	xaxis_title=x_col,
	yaxis_title=y_col,
	template="plotly_white",
)

fig.show()

if cubic:
	params_dict = {
		"fit_type": fit_type,
		"a": a,
		"b": b,
		"c": c,
		"d": d,
		"MSE": mse,
	}
elif quadratic:
	params_dict = {
		"fit_type": fit_type,
		"a": a,
		"b": b,
		"c": c,
		"MSE": mse,
	}

with open(file_path.replace(".csv", f"_{fit_type}_fit.json"), "w") as f:
	json.dump(params_dict, f)
