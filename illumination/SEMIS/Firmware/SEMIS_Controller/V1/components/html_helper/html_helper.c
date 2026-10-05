#include "html_helper.h"
#include "esp_crt_bundle.h"

SemaphoreHandle_t xHeartbeatSemaphore = NULL;
SemaphoreHandle_t xInfluxSemaphore = NULL;

static const char *TAG = "html_helper";
static bool is_registered = false;

static const char* influx_token = INFLUX_TOKEN;
static const char* influx_url   = INFLUX_URL;

/* Forward declarations */
static esp_err_t set_power_handler(httpd_req_t *req);
static int get_query_u8(httpd_req_t *req, const char *key, uint8_t *out);

/* WiFi configuration can be set via project configuration menu

   If you'd rather not, just change the below entries to strings with
   the config you want - ie #define EXAMPLE_WIFI_SSID "mywifissid"
*/
// #define EXAMPLE_ESP_WIFI_SSID      CONFIG_ESP_WIFI_SSID
// #define EXAMPLE_ESP_WIFI_PASS      CONFIG_ESP_WIFI_PASSWORD
#define EXAMPLE_ESP_WIFI_SSID      "solar_simulator_sv"
#define EXAMPLE_ESP_WIFI_PASS      "password"
#define EXAMPLE_ESP_MAXIMUM_RETRY  CONFIG_ESP_MAXIMUM_RETRY

#if CONFIG_ESP_STATION_EXAMPLE_WPA3_SAE_PWE_HUNT_AND_PECK
#define ESP_WIFI_SAE_MODE WPA3_SAE_PWE_HUNT_AND_PECK
#define EXAMPLE_H2E_IDENTIFIER ""
#elif CONFIG_ESP_STATION_EXAMPLE_WPA3_SAE_PWE_HASH_TO_ELEMENT
#define ESP_WIFI_SAE_MODE WPA3_SAE_PWE_HASH_TO_ELEMENT
#define EXAMPLE_H2E_IDENTIFIER CONFIG_ESP_WIFI_PW_ID
#elif CONFIG_ESP_STATION_EXAMPLE_WPA3_SAE_PWE_BOTH
#define ESP_WIFI_SAE_MODE WPA3_SAE_PWE_BOTH
#define EXAMPLE_H2E_IDENTIFIER CONFIG_ESP_WIFI_PW_ID
#endif
#if CONFIG_ESP_WIFI_AUTH_OPEN
#define ESP_WIFI_SCAN_AUTH_MODE_THRESHOLD WIFI_AUTH_OPEN
#elif CONFIG_ESP_WIFI_AUTH_WEP
#define ESP_WIFI_SCAN_AUTH_MODE_THRESHOLD WIFI_AUTH_WEP
#elif CONFIG_ESP_WIFI_AUTH_WPA_PSK
#define ESP_WIFI_SCAN_AUTH_MODE_THRESHOLD WIFI_AUTH_WPA_PSK
#elif CONFIG_ESP_WIFI_AUTH_WPA2_PSK
#define ESP_WIFI_SCAN_AUTH_MODE_THRESHOLD WIFI_AUTH_WPA2_PSK
#elif CONFIG_ESP_WIFI_AUTH_WPA_WPA2_PSK
#define ESP_WIFI_SCAN_AUTH_MODE_THRESHOLD WIFI_AUTH_WPA_WPA2_PSK
#elif CONFIG_ESP_WIFI_AUTH_WPA3_PSK
#define ESP_WIFI_SCAN_AUTH_MODE_THRESHOLD WIFI_AUTH_WPA3_PSK
#elif CONFIG_ESP_WIFI_AUTH_WPA2_WPA3_PSK
#define ESP_WIFI_SCAN_AUTH_MODE_THRESHOLD WIFI_AUTH_WPA2_WPA3_PSK
#elif CONFIG_ESP_WIFI_AUTH_WAPI_PSK
#define ESP_WIFI_SCAN_AUTH_MODE_THRESHOLD WIFI_AUTH_WAPI_PSK
#endif

/* FreeRTOS event group to signal when we are connected*/
static EventGroupHandle_t s_wifi_event_group;

/* The event group allows multiple bits for each event, but we only care about two events:
 * - we are connected to the AP with an IP
 * - we failed to connect after the maximum amount of retries */
#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT      BIT1

static int s_retry_num = 0;

/* Start HTTP server and register URIs */
httpd_handle_t start_webserver(void)
{
    httpd_config_t config = HTTPD_DEFAULT_CONFIG();
    config.server_port = 80;

    httpd_handle_t server = NULL;
    if (httpd_start(&server, &config) == ESP_OK) {

        httpd_uri_t root_uri = {
            .uri      = "/",
            .method   = HTTP_GET,
            .handler  = root_get_handler,
            .user_ctx = NULL
        };
        httpd_register_uri_handler(server, &root_uri);

        httpd_uri_t set_uri = {
            .uri      = "/set",
            .method   = HTTP_GET,
            .handler  = set_power_handler,
            .user_ctx = NULL
        };
        httpd_register_uri_handler(server, &set_uri);

        httpd_uri_t temp_uri = {
            .uri      = "/temperature",
            .method   = HTTP_GET,
            .handler  = temperature_get_handler,
            .user_ctx = NULL
        };
        httpd_register_uri_handler(server, &temp_uri);
        
        ESP_LOGI(TAG, "HTTP server started");
    }
    return server;
}
/////////////////

static void event_handler(void* arg, esp_event_base_t event_base,
                                int32_t event_id, void* event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        if (s_retry_num < EXAMPLE_ESP_MAXIMUM_RETRY) {
            esp_wifi_connect();
            s_retry_num++;
            ESP_LOGI(TAG, "retry to connect to the AP");
        } else {
            xEventGroupSetBits(s_wifi_event_group, WIFI_FAIL_BIT);
        }
        ESP_LOGI(TAG,"connect to the AP fail");
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        ESP_LOGI(TAG, "got ip:" IPSTR, IP2STR(&event->ip_info.ip));
        s_retry_num = 0;
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

void wifi_init_sta(void)
{
    s_wifi_event_group = xEventGroupCreate();

    ESP_ERROR_CHECK(esp_netif_init());

    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    esp_event_handler_instance_t instance_any_id;
    esp_event_handler_instance_t instance_got_ip;
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                        ESP_EVENT_ANY_ID,
                                                        &event_handler,
                                                        NULL,
                                                        &instance_any_id));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT,
                                                        IP_EVENT_STA_GOT_IP,
                                                        &event_handler,
                                                        NULL,
                                                        &instance_got_ip));

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = EXAMPLE_ESP_WIFI_SSID,
            .password = EXAMPLE_ESP_WIFI_PASS,
            /* Authmode threshold resets to WPA2 as default if password matches WPA2 standards (password len => 8).
             * If you want to connect the device to deprecated WEP/WPA networks, Please set the threshold value
             * to WIFI_AUTH_WEP/WIFI_AUTH_WPA_PSK and set the password with length and format matching to
             * WIFI_AUTH_WEP/WIFI_AUTH_WPA_PSK standards.
             */
            .threshold.authmode = ESP_WIFI_SCAN_AUTH_MODE_THRESHOLD,
            .sae_pwe_h2e = ESP_WIFI_SAE_MODE,
            .sae_h2e_identifier = EXAMPLE_H2E_IDENTIFIER,
        },
    };
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA) );
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config) );
    ESP_ERROR_CHECK(esp_wifi_start() );

    ESP_LOGI(TAG, "wifi_init_sta finished.");

    /* Waiting until either the connection is established (WIFI_CONNECTED_BIT) or connection failed for the maximum
     * number of re-tries (WIFI_FAIL_BIT). The bits are set by event_handler() (see above) */
    EventBits_t bits = xEventGroupWaitBits(s_wifi_event_group,
            WIFI_CONNECTED_BIT | WIFI_FAIL_BIT,
            pdFALSE,
            pdFALSE,
            portMAX_DELAY);

    /* xEventGroupWaitBits() returns the bits before the call returned, hence we can test which event actually
     * happened. */
    if (bits & WIFI_CONNECTED_BIT) {
        ESP_LOGI(TAG, "connected to ap SSID:%s password:%s",
                 EXAMPLE_ESP_WIFI_SSID, EXAMPLE_ESP_WIFI_PASS);
    } else if (bits & WIFI_FAIL_BIT) {
        ESP_LOGI(TAG, "Failed to connect to SSID:%s, password:%s",
                 EXAMPLE_ESP_WIFI_SSID, EXAMPLE_ESP_WIFI_PASS);
    } else {
        ESP_LOGE(TAG, "UNEXPECTED EVENT");
    }
}

EventGroupHandle_t wifi_get_event_group(void)
{
    return s_wifi_event_group;
}

/* Build the HTML page */
static uint8_t ledPW01 = 0;   // 0–100 %
static uint8_t ledPW02 = 0;   // 0–100 %
static float set_light_intensity = 0.0f;   // commanded intensity, average of ledPW01/ledPW02 (0-100 %)

// static void build_html(char *buf, size_t len)
// {
//     int used = snprintf(buf, len,
//         "<!DOCTYPE html><html><head>"
//         "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
//         "<style>"
//         "html{font-family:Helvetica;text-align:center;}"
//         ".slider{-webkit-appearance:none;width:80%%;height:25px;border-radius: 5px;background:#ddd;outline:none;}"
//         ".slider::-webkit-slider-thumb{appearance:none;width:25px;height:25px;"
//         "background:#4CAF50;cursor:pointer;}"
//         ".button{margin-top:20px;padding:10px 30px;font-size:20px;"
//         "background:#4CAF50;color:white;border:none;cursor:pointer;}");

//     // Before the <body>, after <style>
//     for (int i = 0; i < LED_CHANNEL_COUNT; ++i) {
//         used += snprintf(buf + used, len - used,
//             ".s%u::-webkit-slider-thumb { background: %s !important; }\n",
//             g_led_channels[i].id, g_led_channels[i].website_slider_color);
//     }
//     used += snprintf(buf + used, len - used,
//         "</style></head><body>"
//         "<h1>SEMIS controller 001</h1>");

//     for (int i = 0; i < LED_CHANNEL_COUNT && used < (int)len; ++i) {
//         led_channel_t *ch = &g_led_channels[i];
//         used += snprintf(buf + used, len - used,
//             "<h3>%s (ID %u): <span id='v%u'>%.0f</span> %%</h3>"
//             "<input type='range' min='0' max='100' value='%.0f' class='slider s%u' id='s%u' oninput='u%u(this.value)'><br>",
//             ch->name, ch->id, ch->id, ch->power*100, ch->power*100, ch->id, ch->id, ch->id);
//     }

//     used += snprintf(buf + used, len - used,
//         "<button class='button' onclick='applyAll()'>Set</button> "
//         "<script>");

//     for (int i = 0; i < LED_CHANNEL_COUNT && used < (int)len; ++i) {
//         led_channel_t *ch = &g_led_channels[i];
//         used += snprintf(buf + used, len - used,
//             "var v%u=%.2f;"
//             "function u%u(v){v%u=v;document.getElementById('v%u').innerHTML=v;}",
//             ch->id, ch->power, ch->id, ch->id, ch->id);
//     }

//     used += snprintf(buf + used, len - used,
//         "function applyAll(){"
//         "  var q='';");

//     for (int i = 0; i < LED_CHANNEL_COUNT && used < (int)len; ++i) {
//         led_channel_t *ch = &g_led_channels[i];
//         used += snprintf(buf + used, len - used,
//             "q+=(q==''?'':'&')+'ch%u='+v%u;", ch->id, ch->id);
//     }

//     used += snprintf(buf + used, len - used,
//         "  var x=new XMLHttpRequest();"
//         "  x.open('GET','/set?'+q,true);"
//         "  x.send();"
//         "}"
//         "</script></body></html>");
// }

esp_err_t root_get_handler(httpd_req_t *req)
{
    // rough estimate: 2kB + 200B per channel
    size_t needed = 2048 + LED_CHANNEL_COUNT * 200;
    char *resp = malloc(needed);
    if (!resp) {
        httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Out of memory");
        return ESP_FAIL;
    }

    // build_html(resp, needed);
    httpd_resp_set_type(req, "text/html");
    httpd_resp_send(req, resp, HTTPD_RESP_USE_STRLEN);
    free(resp);
    return ESP_OK;
}

static int get_query_u8(httpd_req_t *req, const char *key, uint8_t *out)
{
    ESP_LOGI(TAG, "get_query_u8 called");

    char query[2048];
    char buf[16];

    if (httpd_req_get_url_query_str(req, query, sizeof(query)) != ESP_OK)
        return -1;
    if (httpd_query_key_value(query, key, buf, sizeof(buf)) != ESP_OK)
        return -1;

    int v = atoi(buf);
    if (v < 0) v = 0;
    if (v > 100) v = 100;
    *out = (uint8_t)v;
    return 0;
}

static esp_err_t set_power_handler(httpd_req_t *req)
{
    ESP_LOGI(TAG, "set_power_handler called");
    uint8_t v;

    if (get_query_u8(req, "ch0", &v) == 0) {
        
        ledPW01 = v;
        led_power_control(0, 100, ledPW01);
        ESP_LOGI(TAG, "ch0 value: %d", v);
    }
    vTaskDelay(pdMS_TO_TICKS(1000)); // Delay for 1 second to allow the first LED to stabilize
    if (get_query_u8(req, "ch1", &v) == 0) {
        ledPW02 = v;
        led_power_control(1, 100, ledPW02);
        ESP_LOGI(TAG, "ch1 value: %d", v);
    }

    set_light_intensity = (ledPW01 + ledPW02) / 2.0f;
    ESP_LOGI(TAG, "set_light_intensity updated: %.2f", set_light_intensity);

    httpd_resp_sendstr(req, "OK");
    return ESP_OK;
}

esp_err_t temperature_get_handler(httpd_req_t *req)
{
    // float temp = get_temperature();
    char resp[32];
    snprintf(resp, sizeof(resp), "%.2f", 25.0); // TODO: replace with actual temperature
    httpd_resp_sendstr(req, resp);
    return ESP_OK;
}

typedef struct {
    char *buffer;
    int buffer_len;
    int written;
} http_response_t;

static esp_err_t http_event_handler(esp_http_client_event_t *evt)
{
    http_response_t *resp = (http_response_t *)evt->user_data;

    switch (evt->event_id) {
    case HTTP_EVENT_ON_DATA:
        if (!esp_http_client_is_chunked_response(evt->client)) {
            int copy_len = evt->data_len;

            if (resp->written + copy_len >= resp->buffer_len) {
                copy_len = resp->buffer_len - resp->written - 1;
            }

            if (copy_len > 0) {
                memcpy(resp->buffer + resp->written, evt->data, copy_len);
                resp->written += copy_len;
                resp->buffer[resp->written] = '\0';
            }
        }
        break;

    default:
        break;
    }

    return ESP_OK;
}


void register_with_server()
{
    esp_netif_ip_info_t ip_info;
    esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    esp_netif_get_ip_info(netif, &ip_info);
    
    char payload[256];

    char output_buffer[2048] = {0};


    sprintf(
    payload,
    "{\"device_id\":\"" DEVICE_ID "\",\"ip\":\"" IPSTR "\"}",
    IP2STR(&ip_info.ip)
    );

    char response_buffer[256] = {0};

    http_response_t response = {
    .buffer = response_buffer,
    .buffer_len = sizeof(response_buffer),
    .written = 0,
    };

    esp_http_client_config_t config = {
        .url = SERVER_URL "/register",
        .event_handler = http_event_handler, // can be used to track request state if needed
        .user_data = &response,
        .buffer_size_tx = 1024,
    };

    esp_http_client_handle_t client =
        esp_http_client_init(&config);

    esp_http_client_set_method(
        client,
        HTTP_METHOD_POST
    );

    esp_http_client_set_header(
        client,
        "Content-Type",
        "application/json"
    );

    esp_http_client_set_post_field(
        client,
        payload,
        strlen(payload)
    );

    esp_err_t res = esp_http_client_perform(client);

    if(res == ESP_OK) {
            int status = esp_http_client_get_status_code(client);
    int content_length = esp_http_client_get_content_length(client);

    ESP_LOGI(TAG, "HTTP status: %d", status);
    ESP_LOGI(TAG, "Content length: %d", content_length);
    ESP_LOGI(TAG, "Response body: %s", response_buffer);

    if (status == 200 && strstr(response_buffer, "ok")) {
        is_registered = true;
        printf("set is_registered to true\n");
        xSemaphoreGive(xHeartbeatSemaphore);
        xSemaphoreGive(xInfluxSemaphore);
    }
    } else {
        ESP_LOGE(TAG, "Failed to register with server: %s", esp_err_to_name(res));   
    }

    esp_http_client_cleanup(client);

}

void heartbeat_send()
{
    esp_netif_ip_info_t ip_info;
    esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
    esp_netif_get_ip_info(netif, &ip_info);
    
    char payload[256];

    sprintf(
    payload,
    "{\"device_id\":\"" DEVICE_ID "\",\"ip\":\"" IPSTR "\"}",
    IP2STR(&ip_info.ip)
    );

    esp_http_client_config_t config = {
        .url = SERVER_URL "/heartbeat"
    };

    esp_http_client_handle_t client =
        esp_http_client_init(&config);

    esp_http_client_set_method(
        client,
        HTTP_METHOD_POST
    );

    esp_http_client_set_header(
        client,
        "Content-Type",
        "application/json"
    );

    esp_http_client_set_post_field(
        client,
        payload,
        strlen(payload)
    );

    esp_http_client_perform(client);

    esp_http_client_cleanup(client);

    ESP_LOGI(TAG, "Sent heartbeat to server at " SERVER_URL);
}

void heartbeat_task(void *pvParameters)
{
    if (xSemaphoreTake(xHeartbeatSemaphore, portMAX_DELAY) == pdTRUE) {
    while (1)
    {
        // The task completely pauses here indefinitely until the semaphore is "given"
            // This code ONLY runs when triggered
            printf("Trigger received! Performing task...\n");

            heartbeat_send();

            // wait 30 seconds
            vTaskDelay(pdMS_TO_TICKS(30000));
    }
        }

}

void register_task(void *pvParameters)
{
    while (1)
    {
        if (!is_registered) {
            register_with_server();
        } else {
            vTaskDelete(NULL);   // registration is complete, stop this task
        }

        vTaskDelay(pdMS_TO_TICKS(30000));
    }
}

void send_to_influx(float temperature, float voltage, float current, float set_intensity, float measured_light_intensity)
{
    //checl influx_url and influx_token
    ESP_LOGI(TAG, "influx_url: %s", influx_url);
    ESP_LOGI(TAG, "influx_token: %s", influx_token);

    if (influx_url == NULL || influx_url[0] == '\0' ||
        influx_token == NULL || influx_token[0] == '\0') {
        ESP_LOGE(TAG, "Influx URL/token not configured, skipping send");
        return;
    }

    char post_data[256];

    // InfluxDB Line Protocol
    snprintf(post_data, sizeof(post_data),
             "simulator_data,sensor=" DEVICE_ID
             " temperature=%.2f,voltage=%.2f,current=%.2f,set_light_intensity=%.2f,measured_light_intensity=%.2f",
             temperature, voltage, current, set_intensity, measured_light_intensity);

    esp_http_client_config_t config = {
        .url = influx_url,
        .method = HTTP_METHOD_POST,
        .event_handler = http_event_handler,
        .crt_bundle_attach = esp_crt_bundle_attach,
    };

    esp_http_client_handle_t client = esp_http_client_init(&config);
    if (client == NULL) {
        ESP_LOGE(TAG, "Failed to init HTTP client for Influx (invalid URL?)");
        return;
    }

    char auth_header[128];
    snprintf(auth_header, sizeof(auth_header), "Token %s", influx_token);

    esp_http_client_set_header(client, "Authorization", auth_header);
    esp_http_client_set_header(client, "Content-Type", "text/plain");

    esp_http_client_set_post_field(client, post_data, strlen(post_data));

    esp_err_t err = esp_http_client_perform(client);

    if (err == ESP_OK) {
        int status = esp_http_client_get_status_code(client);
        printf("Influx response code: %d\n", status);
    } else {
        printf("HTTP request failed\n");
    }

    esp_http_client_cleanup(client);
}

void influxdb_task(void *pvParameters)
{
    if (xSemaphoreTake(xInfluxSemaphore, portMAX_DELAY) == pdTRUE) {
    while (1)
    {
        // The task completely pauses here indefinitely until the semaphore is "given"
            // This code ONLY runs when triggered
            printf("Trigger received! Performing task...\n");

            // TODO: replace temperature, voltage, current and measured_light_intensity with actual sensor readings
            send_to_influx(25.0, 0.0, 0.0, set_light_intensity, 100.0);

            // wait 1 minute
            vTaskDelay(pdMS_TO_TICKS(60000));
    }
        }
}