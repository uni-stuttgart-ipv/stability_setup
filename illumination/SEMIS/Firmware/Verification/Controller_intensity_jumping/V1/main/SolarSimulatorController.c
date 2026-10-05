#include <string.h>
#include "esp_log.h"
// #include "nvs_flash.h"

#include "lwip/err.h"
#include "lwip/sys.h"

#include "esp_http_server.h"

// #include "html_helper.h"
#include "power_control.h"

#include <stdio.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

static const char *TAG = "main_controller";

void app_main(void)
{
    ESP_LOGI(TAG, "Starting Solar Simulator Controller");
    // initiallize hw
    power_init();

    int8_t state = 0;
    bool direction = true; // true for increasing, false for decreasing
    while (1) {
        led_power_control(0, 100, 10*state);
        vTaskDelay(pdMS_TO_TICKS(1000)); 
        led_power_control(1, 100, 10*state);
        if (direction == true){
            if (state >= 10) {
                direction = false;
            }
        } else {
            if (state <= 0) {
                direction = true;
            }
        }
        if (direction) {
            state += 1;
        } else {
            state -= 1;
        }
        // vTaskDelay(pdMS_TO_TICKS(5000));
        vTaskDelay(pdMS_TO_TICKS(1000*5 - 1000)); // sleep for one hour
    }
}
