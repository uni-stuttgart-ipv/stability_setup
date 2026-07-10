import sys

import neopixel
import time
import os
from machine import ADC
from machine import Pin
from neopixel import NeoPixel

def setup_csv(column_list, csv_file_name):
    # create file with header once
    f = open(csv_file_name, 'w')
    f.write(','.join(column_list) + '\n')
    f.close()

def write_to_csv(timestamp, measurement):
    with open(CSV_FILE, 'a') as f:
        f.write(f"{timestamp},{measurement}\n")

def set_color(r, g, b):
    np[0] = (r, g, b)  # RGB values 0–255
    np.write()

if __name__ == "__main__":
    time.sleep(5)  # Wait for powerup

    LED_PIN = 8
    NUM_LEDS = 1

    np = neopixel.NeoPixel(Pin(LED_PIN, Pin.OUT), NUM_LEDS, 3)
    set_color(255, 0, 0)  # Red

    index = 0
    try:
        os.mkdir('log')
    except:
        pass
    CSV_FILE = f"log/data_log_{index}.csv"

    while True:
        try:
            with open(CSV_FILE, 'r') as f:
                pass
            index += 1
            CSV_FILE = f"log/data_log_{index}.csv"
        except:
            print(f"Creating new CSV file: {CSV_FILE}")
            break
    
    COLUMNS = ["timestamp [s]", "measurement [uV]"]
    
    # Time setup
    time_between_meas = 5 # in seconds
    total_meas_time = 40 * 24 * 3600 # twenty days in seconds
    start_time = time.time()
    last_meas_time = start_time

    print("Setting up CSV file...")
    setup_csv(COLUMNS, CSV_FILE)
    
    # Pin setup
    adc_pin = 0 # 0 to 6 available in ESP32 C6

    adc = ADC(adc_pin)

    set_color(0, 255, 0)  # Green

    meas_max = 2000000 # 2V in uV
        
    while time.time() - start_time < total_meas_time:
        set_color(0, 0, 10)  # Blue
        if time.time() - last_meas_time >= time_between_meas or last_meas_time == start_time:
            val = adc.read_uv() 
            set_color(int((val * 10) / meas_max), 10, 0)  # Green
            print(f"{time.time()} Measurement: {val} uV")
            write_to_csv(time.time(), val)
            last_meas_time = time.time()
            time.sleep(time_between_meas-0.5) 
    
    write_to_csv(time.time(), "Measurement finished")
    print("finish")
    
