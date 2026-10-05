#include "html_helper.h"

static const char *TAG = "html_helper";

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

/* Build the HTML page */
static uint8_t ledPW01 = 0;   // 0–100 %
static uint8_t ledPW02 = 0;   // 0–100 %

static void build_html(char *buf, size_t len)
{
    int used = snprintf(buf, len,
        "<!DOCTYPE html><html><head>"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
        "<style>"
        "html{font-family:Helvetica;text-align:center;}"
        ".slider{-webkit-appearance:none;width:80%%;height:25px;border-radius: 5px;background:#ddd;outline:none;}"
        ".slider::-webkit-slider-thumb{appearance:none;width:25px;height:25px;"
        "background:#4CAF50;cursor:pointer;}"
        ".button{margin-top:20px;padding:10px 30px;font-size:20px;"
        "background:#4CAF50;color:white;border:none;cursor:pointer;}");

    // Before the <body>, after <style>
    for (int i = 0; i < LED_CHANNEL_COUNT; ++i) {
        used += snprintf(buf + used, len - used,
            ".s%u::-webkit-slider-thumb { background: %s !important; }\n",
            g_led_channels[i].id, g_led_channels[i].website_slider_color);
    }
    used += snprintf(buf + used, len - used,
        "</style></head><body>"
        "<h1>SEMIS controller 001</h1>");

    for (int i = 0; i < LED_CHANNEL_COUNT && used < (int)len; ++i) {
        led_channel_t *ch = &g_led_channels[i];
        used += snprintf(buf + used, len - used,
            "<h3>%s (ID %u): <span id='v%u'>%.0f</span> %%</h3>"
            "<input type='range' min='0' max='100' value='%.0f' class='slider s%u' id='s%u' oninput='u%u(this.value)'><br>",
            ch->name, ch->id, ch->id, ch->power*100, ch->power*100, ch->id, ch->id, ch->id);
    }

    used += snprintf(buf + used, len - used,
        "<button class='button' onclick='applyAll()'>Set</button> "
        "<script>");

    for (int i = 0; i < LED_CHANNEL_COUNT && used < (int)len; ++i) {
        led_channel_t *ch = &g_led_channels[i];
        used += snprintf(buf + used, len - used,
            "var v%u=%.2f;"
            "function u%u(v){v%u=v;document.getElementById('v%u').innerHTML=v;}",
            ch->id, ch->power, ch->id, ch->id, ch->id);
    }

    used += snprintf(buf + used, len - used,
        "function applyAll(){"
        "  var q='';");

    for (int i = 0; i < LED_CHANNEL_COUNT && used < (int)len; ++i) {
        led_channel_t *ch = &g_led_channels[i];
        used += snprintf(buf + used, len - used,
            "q+=(q==''?'':'&')+'ch%u='+v%u;", ch->id, ch->id);
    }

    used += snprintf(buf + used, len - used,
        "  var x=new XMLHttpRequest();"
        "  x.open('GET','/set?'+q,true);"
        "  x.send();"
        "}"
        "</script></body></html>");
}

esp_err_t root_get_handler(httpd_req_t *req)
{
    // rough estimate: 2kB + 200B per channel
    size_t needed = 2048 + LED_CHANNEL_COUNT * 200;
    char *resp = malloc(needed);
    if (!resp) {
        httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Out of memory");
        return ESP_FAIL;
    }

    build_html(resp, needed);
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
        ESP_LOGI(TAG, "ch0 value: %d", v);
        ledPW01 = v;
        led_power_control(0, 100, ledPW01);
    }
    if (get_query_u8(req, "ch1", &v) == 0) {
        ESP_LOGI(TAG, "ch1 value: %d", v);
        ledPW02 = v;
        led_power_control(1, 100, ledPW02);
    }

    httpd_resp_sendstr(req, "OK");
    return ESP_OK;
}
