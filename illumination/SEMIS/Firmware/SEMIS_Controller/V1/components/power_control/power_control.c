#include "power_control.h"

static const char *TAG = "power_control";

led_channel_t *get_led_by_id(uint8_t id);

static mcp4802_t dac = {
    .pin_cs = 0,  // your CS pin
    .channel[0] = { // channel A
        .gainSelect = GAIN_SELECTION, // constant defined in MCP4802.h
        .active = true, // active mode
    },
    .channel[1] = { // channel B
        .gainSelect = GAIN_SELECTION, // constant defined in MCP4802.h
        .active = true, // active mode
    }
};

led_channel_t g_led_channels[LED_CHANNEL_COUNT] = { // LED ids are sequencial. It is important to keep the LED id same as index in this array.
    { .id = 0, .name = "White", .power = 0, .channel = WHITE_CHANNEL, .dac = &dac, .website_slider_color = "#fab905"},
    { .id = 1, .name = "Red", .power = 0, .channel = RED_CHANNEL, .dac = &dac, .website_slider_color = "#e74c3c"},
};

void power_init(void)
{
    ESP_LOGI(TAG, "Start of power init");
    esp_err_t err = mcp4802_init(&dac);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize MCP4802 DAC");
        return;
    }
    ESP_LOGI(TAG, "MCP4802 DAC initialized");

    vTaskDelay(pdMS_TO_TICKS(1000)); // small delay to ensure DAC is ready before sending commands

    // Initialize all LEDs to off
    for (int i = 0; i < LED_CHANNEL_COUNT; i++) {
        led_power_control(g_led_channels[i].id, 1, LED_FLAG_OFF);
    }
    ESP_LOGI(TAG, "End of power init");
}

void led_power_control(uint8_t led_id, int8_t max_level, float power_level)
{
    led_channel_t *led = get_led_by_id(led_id);
    if (led == NULL) {
        ESP_LOGE(TAG, "Invalid LED ID: %d", led_id);
        return;
    }

    int8_t min_level = 0;

    // Normalize power_level to [min_level, max_level] range, then to convert to range [0.0, 1.0]
    if (power_level < min_level) {
        power_level = min_level;
    } else if (power_level > max_level) {
        power_level = max_level;
    }
    power_level = (power_level - min_level) / (max_level - min_level);
    if (INVERT_LOGIC) {
        power_level = 1.0f - power_level;
    }
    led->power = power_level;

    uint8_t dac_value = (uint8_t)(power_level * 255.0f);
    ESP_LOGI(TAG, "Setting LED channel %d to power level %.2f (DAC value: %d)", 
             led->channel, led->power, dac_value);

    mcp4802_write_reg(led->dac, dac_value, led->channel);
}

led_channel_t *get_led_by_id(uint8_t id)
{
    for (int i = 0; i < LED_CHANNEL_COUNT; i++) {
        if (g_led_channels[i].id == id) {
            return &g_led_channels[i];
        }
    }
    return NULL; // Not found
}