#ifndef POWER_CONTROL_H
#define POWER_CONTROL_H
#include "freertos/idf_additions.h"
#endif

#define SERVER_URL "http://10.27.234.22:8000"
#define DEVICE_ID "solar_simulator_02"
#define WIFI_CONNECTED_BIT BIT0
extern SemaphoreHandle_t xHeartbeatSemaphore;
extern SemaphoreHandle_t xInfluxSemaphore;


#include <stdint.h>
#include "esp_http_client.h"
#include "esp_http_server.h"
#include "freertos/event_groups.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "power_control.h"
#include "esp_netif.h"

// HTTP_handlers
esp_err_t led_on_handler(httpd_req_t *req);
esp_err_t led_off_handler(httpd_req_t *req);
esp_err_t root_get_handler(httpd_req_t *req);
esp_err_t temperature_get_handler(httpd_req_t *req);
httpd_handle_t start_webserver(void);
void wifi_init_sta(void);
void register_with_server(void);
void heartbeat_send(void);
void heartbeat_task(void *pvParameters);
void register_task(void *pvParameters);
void influxdb_task(void *pvParameters);
EventGroupHandle_t wifi_get_event_group(void);
static bool is_registered;