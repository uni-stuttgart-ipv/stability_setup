#include "MAX31865.H"
#include "driver/spi_master.h"
#include "esp_log.h"

// ============================================================================
// Logging Tag
// ============================================================================

static const char *TAG = "MAX31865_SPI";

// ============================================================================
// SPI Handle (Static - managed internally)
// ============================================================================

static spi_device_handle_t spi_device = NULL;

// ============================================================================
// SPI Initialization
// ============================================================================

bool MAX31865_SPI_Init(void)
{
    if (spi_device != NULL) {
        ESP_LOGW(TAG, "SPI already initialized");
        return true;
    }

    esp_err_t ret;

    // Configure SPI bus (SPI2)
    spi_bus_config_t bus_cfg = {
        .mosi_io_num = SPI_MOSI_PIN,
        .miso_io_num = SPI_MISO_PIN,
        .sclk_io_num = SPI_CLK_PIN,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 4096,
    };

    ret = spi_bus_initialize(SPI2_HOST, &bus_cfg, SPI_DMA_CH_AUTO);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize SPI bus: %s", esp_err_to_name(ret));
        return false;
    }

    // Configure SPI device
    spi_device_interface_config_t dev_cfg = {
        .mode = SPI_MODE,
        .clock_speed_hz = SPI_FREQUENCY,
        .spics_io_num = SPI_CS_PIN,
        .queue_size = 7,
        .flags = SPI_DEVICE_HALFDUPLEX,
    };

    ret = spi_bus_add_device(SPI2_HOST, &dev_cfg, &spi_device);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to add SPI device: %s", esp_err_to_name(ret));
        spi_bus_free(SPI2_HOST);
        return false;
    }

    ESP_LOGI(TAG, "SPI initialized successfully");
    return true;
}

// ============================================================================
// SPI Deinitialization
// ============================================================================

void MAX31865_SPI_Deinit(void)
{
    if (spi_device == NULL) {
        ESP_LOGW(TAG, "SPI not initialized");
        return;
    }

    spi_bus_remove_device(spi_device);
    spi_bus_free(SPI2_HOST);
    spi_device = NULL;

    ESP_LOGI(TAG, "SPI deinitialized");
}

// ============================================================================
// Single Byte Write
// ============================================================================

void MAX31865_SPI_WriteByte(uint8_t data)
{
    if (spi_device == NULL) {
        ESP_LOGE(TAG, "SPI not initialized");
        return;
    }

    spi_transaction_t t = {
        .length = 8,
        .tx_buffer = &data,
        .rx_buffer = NULL,
    };

    spi_device_transmit(spi_device, &t);
}

// ============================================================================
// Single Byte Read
// ============================================================================

uint8_t MAX31865_SPI_ReadByte(void)
{
    if (spi_device == NULL) {
        ESP_LOGE(TAG, "SPI not initialized");
        return 0;
    }

    uint8_t data = 0;
    spi_transaction_t t = {
        .length = 8,
        .tx_buffer = NULL,
        .rx_buffer = &data,
    };

    spi_device_transmit(spi_device, &t);
    return data;
}

// ============================================================================
// Multiple Bytes Write
// ============================================================================

void MAX31865_SPI_WriteBytes(const uint8_t *data, uint16_t length)
{
    if (spi_device == NULL) {
        ESP_LOGE(TAG, "SPI not initialized");
        return;
    }

    if (data == NULL || length == 0) {
        ESP_LOGW(TAG, "Invalid write parameters");
        return;
    }

    spi_transaction_t t = {
        .length = length * 8,
        .tx_buffer = data,
        .rx_buffer = NULL,
    };

    spi_device_transmit(spi_device, &t);
}

// ============================================================================
// Multiple Bytes Read
// ============================================================================

void MAX31865_SPI_ReadBytes(uint8_t *data, uint16_t length)
{
    if (spi_device == NULL) {
        ESP_LOGE(TAG, "SPI not initialized");
        return;
    }

    if (data == NULL || length == 0) {
        ESP_LOGW(TAG, "Invalid read parameters");
        return;
    }

    spi_transaction_t t = {
        .length = length * 8,
        .tx_buffer = NULL,
        .rx_buffer = data,
    };

    spi_device_transmit(spi_device, &t);
}

// ============================================================================
// Full-Duplex SPI Transfer (Write and Read simultaneously)
// ============================================================================

void MAX31865_SPI_TransferBytes(const uint8_t *write_data, uint8_t *read_data, uint16_t length)
{
    if (spi_device == NULL) {
        ESP_LOGE(TAG, "SPI not initialized");
        return;
    }

    if ((write_data == NULL && read_data == NULL) || length == 0) {
        ESP_LOGW(TAG, "Invalid transfer parameters");
        return;
    }

    spi_transaction_t t = {
        .length = length * 8,
        .tx_buffer = write_data,
        .rx_buffer = read_data,
    };

    spi_device_transmit(spi_device, &t);
}

// ============================================================================
// Chip Select Control
// ============================================================================

void MAX31865_SPI_CS_Assert(void)
{
    // CS is typically managed by the SPI driver (active low by default)
    // This function is a placeholder for manual CS control if needed
    ESP_LOGD(TAG, "CS asserted");
}

void MAX31865_SPI_CS_Deassert(void)
{
    // CS is typically managed by the SPI driver
    // This function is a placeholder for manual CS control if needed
    ESP_LOGD(TAG, "CS deasserted");
}

// ============================================================================
// Complete SPI Transaction with CS Control
// ============================================================================

void MAX31865_SPI_Transaction(const uint8_t *write_data, uint8_t *read_data, uint16_t length)
{
    if (spi_device == NULL) {
        ESP_LOGE(TAG, "SPI not initialized");
        return;
    }

    if ((write_data == NULL && read_data == NULL) || length == 0) {
        ESP_LOGW(TAG, "Invalid transaction parameters");
        return;
    }

    // Assert CS (optional - ESP-IDF typically manages this automatically)
    MAX31865_SPI_CS_Assert();

    // Perform full-duplex transfer
    MAX31865_SPI_TransferBytes(write_data, read_data, length);

    // Deassert CS (optional - ESP-IDF typically manages this automatically)
    MAX31865_SPI_CS_Deassert();
}
