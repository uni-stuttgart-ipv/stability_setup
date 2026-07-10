#include <string.h>
#include "esp_log.h"
#include "nvs_flash.h"

#include "lwip/err.h"
#include "lwip/sys.h"

#include "esp_http_server.h"

#include "html_helper.h"
#include "power_control.h"

#include <max31865.h>

#include <stdio.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#define PIN_NUM_MISO 10
#define PIN_NUM_MOSI 7
#define PIN_NUM_CLK  6
#define PIN_NUM_CS   17

#define RREF      4300.0f
#define RNOMINAL  1000.0f

static const char *TAG = "main_controller";

static httpd_handle_t server = NULL;

// if esp32 is registered with server, it will send heartbeat every 30 seconds, otherwise it will try to register again every 30 seconds
// static bool is_registered = false;



void app_main(void)
{
    ESP_LOGI(TAG, "Start of main");

    // initiallize hw
    power_init();

    //Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
      ESP_ERROR_CHECK(nvs_flash_erase());
      ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // TODO: implement value saving to nvs, for example, save the current power state, so that it can be restored after reboot
    // // Open NVS handle
    // ESP_LOGI(TAG, "\nOpening Non-Volatile Storage (NVS) handle...");
    // nvs_handle_t my_handle;
    // ret = nvs_open("storage", NVS_READWRITE, &my_handle);
    // if (ret != ESP_OK) {
    //     ESP_LOGE(TAG, "Error (%s) opening NVS handle!", esp_err_to_name(ret));
    //     return;
    // }

    // // Read value: if not initialized, default is 0
    // int32_t read_counter = 0;
    // ESP_LOGI(TAG, "\nReading counter from NVS...");
    // ret = nvs_get_i32(my_handle, "counter", &read_counter);
    // switch (ret) {
    //     case ESP_OK:
    //         ESP_LOGI(TAG, "Read counter = %" PRIu32, read_counter);
    //         break;
    //     case ESP_ERR_NVS_NOT_FOUND:
    //         ESP_LOGW(TAG, "The value is not initialized yet!");
    //         break;
    //     default:
    //         ESP_LOGE(TAG, "Error (%s) reading!", esp_err_to_name(ret));
    // }
    //  // Store and read an integer value
    // read_counter += 1;
    // ESP_LOGI(TAG, "\nWriting counter to NVS...");
    // ret = nvs_set_i32(my_handle, "counter", read_counter);
    // if (ret != ESP_OK) {
    //     ESP_LOGE(TAG, "Failed to write counter!");
    // }
    // // Delete a key from NVS
    // ESP_LOGI(TAG, "\nDeleting key from NVS...");
    // ret = nvs_erase_key(my_handle, "counter");
    // if (ret != ESP_OK) {
    //     ESP_LOGE(TAG, "Failed to erase key!");
    // }

    // Close NVS handle
    
    // nvs_close(my_handle); // TODO implement value saving


    if (CONFIG_LOG_MAXIMUM_LEVEL > CONFIG_LOG_DEFAULT_LEVEL) {
        /* If you only want to open more logs in the wifi module, you need to make the max level greater than the default level,
         * and call esp_log_level_set() before esp_wifi_init() to improve the log level of the wifi module. */
        esp_log_level_set("wifi", CONFIG_LOG_MAXIMUM_LEVEL);
    }

    ESP_LOGI(TAG, "ESP_WIFI_MODE_STA");
    wifi_init_sta();


     // 2. Create the semaphore before starting the task
    xHeartbeatSemaphore = xSemaphoreCreateBinary();
    xInfluxSemaphore = xSemaphoreCreateBinary();

    // if(WIFI_CONNECTED_BIT) {
        // ESP_LOGI(TAG, "Registering with server");
        
        xTaskCreate(
        register_task,
        "register_task",
        4096,
        NULL,
        5,
        NULL
        );

    // }

    ESP_LOGI(TAG, "Now entering web server");

    //task to send heartbeat every 30 seconds after registration is complete
    xTaskCreate(
        heartbeat_task,
        "heartbeat_task",
        4096,
        NULL,
        5,
        NULL
    );

    //task to send data to influxdb every minute after registration is complete
    xTaskCreate(
        influxdb_task,
        "influxdb_task",
        4096,
        NULL,
        5,
        NULL
    );

    // no loop() needed; handlers run in esp-idf tasks
    server = start_webserver(); // Start HTTP server
}

// #include "driver/spi_master.h"



// void app_main(void)
// {
//     spi_bus_config_t buscfg = {
//         .miso_io_num = PIN_NUM_MISO,
//         .mosi_io_num = PIN_NUM_MOSI,
//         .sclk_io_num = PIN_NUM_CLK,
//         .quadwp_io_num = -1,
//         .quadhd_io_num = -1,
//         .max_transfer_sz = 0,
//     };

//     ESP_ERROR_CHECK(spi_bus_initialize(SPI2_HOST, &buscfg, SPI_DMA_CH_AUTO));

//     max31865_t dev = {
//         .rtd_nominal = RNOMINAL,
//         .r_ref = RREF,
//         .standard = MAX31865_ITS90,
//     };

//     ESP_ERROR_CHECK(max31865_init_desc(&dev, SPI2_HOST, MAX31865_MAX_CLOCK_SPEED_HZ, PIN_NUM_CS));

//     max31865_config_t cfg = {
//         .mode = MAX31865_MODE_SINGLE,
//         .connection = MAX31865_3WIRE,
//         .v_bias = true,
//         .filter = MAX31865_FILTER_50HZ,
//     };
//     ESP_ERROR_CHECK(max31865_set_config(&dev, &cfg));

//     while (1) {
//         float temp = 0.0f;
//         esp_err_t ret = max31865_measure(&dev, &temp);
//         if (ret == ESP_OK) {
//             printf("Temperature = %.2f C\n", temp);
//         } else {
//             ESP_LOGE(TAG, "MAX31865 measure failed: %s", esp_err_to_name(ret));
//         }

//         vTaskDelay(pdMS_TO_TICKS(1000));
//     }
// }


