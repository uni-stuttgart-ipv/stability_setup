#pragma once

#include "esp_log.h"
#include "MCP4802.h"

/* Define channel numbers */
#define WHITE_CHANNEL 0
#define RED_CHANNEL 1

#define LED_CHANNEL_COUNT 2
#define INVERT_LOGIC 0

#define LED_FLAG_ON INVERT_LOGIC ? 0 : 1
#define LED_FLAG_OFF LED_FLAG_ON == 1 ? 0 : 1

typedef struct {
    uint8_t id;                         // LED identifier
    const char *name;                   // LED name
    const char *website_slider_color;        // color of the slider in the web interface
    uint8_t channel;                    // channel identifier
    // const char *state_str;      // description of the state
    float     power;                    // power float: 0.0 to 1.0
    mcp4802_t *dac;                     // DAC instance
} led_channel_t;

extern led_channel_t g_led_channels[LED_CHANNEL_COUNT];

void led_power_control(uint8_t led_id, int8_t max_level, float power_level);
void power_init(void);


