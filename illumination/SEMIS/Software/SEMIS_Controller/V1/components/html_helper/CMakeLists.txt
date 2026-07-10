idf_component_register(
    SRCS "html_helper.c"
    PRIV_REQUIRES esp_wifi esp_http_server mbedtls
    INCLUDE_DIRS "."
    REQUIRES power_control esp_http_client
)

target_compile_definitions(${COMPONENT_LIB} PRIVATE
    INFLUX_TOKEN="${INFLUX_TOKEN}"
    INFLUX_URL="${INFLUX_URL}"
)