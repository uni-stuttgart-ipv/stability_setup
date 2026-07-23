from machine import Pin
import neopixel
import time

# Built-in LED pin (common for ESP32-C6)
LED_PIN = 8
NUM_LEDS = 1

np = neopixel.NeoPixel(Pin(LED_PIN, Pin.OUT), NUM_LEDS, 3)

def set_color(r, g, b):
    np[0] = (r, g, b)  # RGB values 0–255
    np.write()

while True:
    set_color(255, 0, 0)   # Red
    time.sleep(1)

    set_color(0, 255, 0)   # Green
    time.sleep(1)

    set_color(0, 0, 255)   # Blue
    time.sleep(1)

    set_color(255, 255, 255)  # White
    time.sleep(1)

    set_color(0, 0, 0)  # Off
    time.sleep(1)