import pandas as pd
from pandas.api.types import is_numeric_dtype
import scipy.optimize as opt
import numpy as np
# from sqlalchemy import true

class Spectrum:
    def __init__(self, spectrum: dict):
        self.spectrum = spectrum
        self.optimal_scaling_factors = {name: 1 for name in spectrum.keys()}
        self.spectral_deviation = None
        self.spectral_coverage = None

class SpectralMatcher:
    def __init__(self, target_spectrum: pd.DataFrame, candidate_spectra: dict = None):
        self.candidate_spectra = {}
        self.optimal_scaling_factors = {}

        self.target_spectrum = self.check_spectrum_compatibility(target_spectrum)

        if candidate_spectra:
            for name, spectra in candidate_spectra.items():
                self.add_candidate(name, spectra)

    def check_spectrum_compatibility(self,  spectrum: pd.DataFrame):    
        if 'wavelength [nm]' not in spectrum.columns:
            raise ValueError("Spectrum is missing required column: 'wavelength [nm]'")
        elif not is_numeric_dtype(spectrum['wavelength [nm]']):
            try:
                spectrum['wavelength [nm]'] = pd.to_numeric(spectrum['wavelength [nm]'], errors='coerce')
            except Exception as e:
                raise ValueError(f"Failed to convert 'wavelength [nm]' to numeric: {e}")
        
        if 'power [W/m2]' in spectrum.columns:
            if not is_numeric_dtype(spectrum['power [W/m2]']):
                try:
                    spectrum['power [W/m2]'] = pd.to_numeric(spectrum['power [W/m2]'], errors='coerce')
                except Exception as e:
                    raise ValueError(f"Failed to convert 'power [W/m2]' to numeric: {e}")
            spectrum.insert(len(spectrum.columns), 'relative intensity [%]', np.nan)
            spectrum = self.normalize_spectrum(spectrum)
        elif 'relative intensity [%]' in spectrum.columns:
            if not is_numeric_dtype(spectrum['relative intensity [%]']):
                try:
                    spectrum['relative intensity [%]'] = pd.to_numeric(spectrum['relative intensity [%]'], errors='coerce')
                except Exception as e:
                    raise ValueError(f"Failed to convert 'relative intensity [%]' to numeric: {e}")
        return spectrum
    
    def normalize_spectrum(self, spectrum: pd.DataFrame) -> pd.DataFrame:
        max_intensity = spectrum['power [W/m2]'].max()
        if max_intensity > 0:
            spectrum['relative intensity [%]'] = spectrum['power [W/m2]'] / max_intensity
        return spectrum

    def add_candidate(self, name: str, spectral_combination: dict):
        try:
            temp_combination = {}
            for spectrum_name, spectrum in spectral_combination.items():
                temp_combination[spectrum_name] = self.check_spectrum_compatibility(spectrum)
        except ValueError as e:
            raise ValueError(f"Spectrum {spectrum_name} in combination '{name}' is incompatible: {e}")

        self.candidate_spectra[name] = temp_combination
        self.optimal_scaling_factors[name] = [1 for _ in temp_combination]

    def set_target_spectrum(self, target_spectrum: pd.DataFrame):
        self.target_spectrum = self.check_spectrum_compatibility(target_spectrum)

    def optimize_scaling_factors(self):
        if len(self.candidate_spectra) == 0:
            raise ValueError("No candidate spectra to optimize. Please add candidates using add_candidate() before optimization.")
        # Build a common wavelength axis and reference target
        x_ref = self.target_spectrum['wavelength [nm]'].to_numpy()
        y_ref = self.target_spectrum['power [W/m2]'].to_numpy()

        for name, spectra in self.candidate_spectra.items():
            # Interpolate all LED spectra onto the same wavelength axis
            led_files = list(spectra.keys())
            led_matrix = np.column_stack([
            np.interp(
                x_ref,
                spectra[file]['wavelength [nm]'].to_numpy(),
                spectra[file]['relative intensity [%]'].to_numpy()
                )
                for file in led_files
            ])

            # Objective: match spectral shape while constraining integrated irradiance
            def objective(scales):
                residual = led_matrix @ scales - y_ref
                return np.mean(residual ** 2)

            # Initial guess from current dictionary (fallback to 1.0 if all zeros)
            p0 = np.array(self.optimal_scaling_factors[name], dtype=float)
            if np.allclose(p0, 0):
                p0 = np.ones(len(led_files), dtype=float)

            # Scale initial guess to roughly match total irradiance for better convergence
            irradiance_target = np.trapezoid(y_ref, x_ref)
            led_irradiance_per_unit = np.trapezoid(led_matrix, x_ref, axis=0)
            init_irradiance = float(np.dot(led_irradiance_per_unit, p0))
            if init_irradiance > 0:
                p0 = p0 * (irradiance_target / init_irradiance)

            # Constrain integrated irradiance to be close to the target (±1%)
            irradiance_tolerance = 0.01 * irradiance_target

            constraints = [
                {
                    'type': 'ineq',
                    'fun': lambda s: (irradiance_target + irradiance_tolerance) - np.dot(led_irradiance_per_unit, s)
                },
                {
                    'type': 'ineq',
                    'fun': lambda s: np.dot(led_irradiance_per_unit, s) - (irradiance_target - irradiance_tolerance)
                }
            ]

            bounds = [(0, None)] * len(led_files)

            result = opt.minimize(
                objective,
                p0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000, 'ftol': 1e-12}
            )

            if not result.success:
                raise RuntimeError(f"Constrained optimization failed: {result.message}")

            popt = result.x

            self.optimal_scaling_factors[name] = popt.tolist()

            # Optional: fitted combined spectrum to plot
            # fitted_led_sum = led_matrix @ popt

# Example usage
if __name__ == "__main__":
    AM1_5G_path = r""
    if not AM1_5G_path:
        raise ValueError("Please provide the path to the AM1.5G spectrum file.")

    df_AM1_5G = pd.read_excel(AM1_5G_path, skiprows=1, names=["wavelength [nm]", "Etr [W/m2]", "global tilt [W/m2]", "direct+circumsolar [W/m2]"], sheet_name=0)

    # Group by every 2 rows and sum, keeping the first wavelength value
    Solar_spectrum_binned = pd.DataFrame()
    Solar_spectrum_binned = df_AM1_5G.iloc[::1].reset_index(drop=True).copy()
    Solar_spectrum_binned['global tilt [W/m2]'] += df_AM1_5G.iloc[0::1]['global tilt [W/m2]'].values

    Solar_spectrum_binned['global tilt [W/m2]'] = Solar_spectrum_binned['global tilt [W/m2]']/2

    lambda_min, lambda_max = 400, 800

    solar_spectrum_filtered = Solar_spectrum_binned [(Solar_spectrum_binned['wavelength [nm]'] >= lambda_min) & (Solar_spectrum_binned['wavelength [nm]'] <= lambda_max)].reset_index(drop=True)

    df_AM1_5G_filtered = solar_spectrum_filtered[['wavelength [nm]']].copy()
    df_AM1_5G_filtered['power [W/m2]'] = solar_spectrum_filtered['global tilt [W/m2]']

    target_spectrum = df_AM1_5G_filtered.copy()

    LED_spectra = {}

    for file in ['Resources/red_740_LED.csv', 'Resources/660nm_red_LED.csv', 'Resources/white_5700K_30W.csv']:
        LED_spectra[file] = pd.read_csv(file)
        normalized_intensity = LED_spectra[file]['relative intensity [%]'] / LED_spectra[file]['relative intensity [%]'].max()
        LED_spectra[file]['relative intensity [%]'] = normalized_intensity

    candidate_spectra = {
        'Combination 1': {
            'red_740_LED.csv': LED_spectra['Resources/red_740_LED.csv'],
            'white_5700K_30W.csv': LED_spectra['Resources/white_5700K_30W.csv']
        },
        'Combination 2': {
            '660nm_red_LED.csv': LED_spectra['Resources/660nm_red_LED.csv'],
            'white_5700K_30W.csv': LED_spectra['Resources/white_5700K_30W.csv']
        },
        'Combination 3': {
            'red_740_LED.csv': LED_spectra['Resources/red_740_LED.csv'],
            '660nm_red_LED.csv': LED_spectra['Resources/660nm_red_LED.csv'],
            'white_5700K_30W.csv': LED_spectra['Resources/white_5700K_30W.csv']
        }
    }

    matcher = SpectralMatcher(target_spectrum, candidate_spectra)
    matcher.optimize_scaling_factors()
    print(matcher.optimal_scaling_factors)