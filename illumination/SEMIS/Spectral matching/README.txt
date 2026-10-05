The spectral matcher can assess the suitability of different light source combinations to simulate solar irradiance.

It takes as an input the normalized spectrum of a group of light sources, and it estimates the optimal scaling factors (with respect to the normalized irradiance) which minimize the deviation from the target spectrum (e.g., the solar spectrum).

IMPORTANT: the results depend strongly on the optimization algorithm, which is implemented inside the class SpectralMatcher, in the method "optimize_scaling_factors"

ADDITIONAL: The jupyter notebook "Spectrum_analysis of commercial_LEDs" includes an image processing tool to convert an spectral curve from an image to a CSV file.