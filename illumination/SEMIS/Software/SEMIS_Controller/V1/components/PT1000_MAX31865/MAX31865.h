#ifndef MAX31865_H
#define MAX31865_H

#include <stdint.h>
#include <stdbool.h>

// ============================================================================
// SPI Pin Definitions (Configure these with your pin assignments)
// ============================================================================

#define SPI_MOSI_PIN    7  // SPI Master Out Slave In pin
#define SPI_MISO_PIN    10  // SPI Master In Slave Out pin
#define SPI_CLK_PIN     6  // SPI Clock pin
#define SPI_CS_PIN      17  // SPI Chip Select pin

// ============================================================================
// SPI Configuration
// ============================================================================

#define SPI_FREQUENCY   2000000  // SPI clock frequency in Hz
#define SPI_MODE        1        // SPI mode (0-3)
#define SPI_BIT_ORDER   0        // 0: MSB first, 1: LSB first

// ============================================================================
// Register map
// ============================================================================

#define MAX31865_READ_REG_CONFIG       0x00
#define MAX31865_READ_REG_RTD_MSB      0x01
#define MAX31865_READ_REG_RTD_LSB      0x02
#define MAX31865_READ_REG_HFT_MSB      0x03
#define MAX31865_READ_REG_HFT_LSB      0x04
#define MAX31865_READ_REG_LFT_MSB      0x05
#define MAX31865_READ_REG_LFT_LSB      0x06
#define MAX31865_READ_REG_FAULT_STATUS 0x07

#define MAX31865_WRITE_REG_CONFIG      0x80
#define MAX31865_WRITE_REG_HFT_MSB     0x83
#define MAX31865_WRITE_REG_HFT_LSB     0x84
#define MAX31865_WRITE_REG_LFT_MSB     0x85
#define MAX31865_WRITE_REG_LFT_LSB     0x86

// ============================================================================
// Function Declarations
// ============================================================================

/**
 * @brief Initialize SPI communication with configured pins and settings
 * @return true if initialization successful, false otherwise
 */
bool MAX31865_SPI_Init(void);

/**
 * @brief Deinitialize SPI communication
 */
void MAX31865_SPI_Deinit(void);

/**
 * @brief Write a single byte to SPI bus
 * @param data Byte to write
 */
void MAX31865_SPI_WriteByte(uint8_t data);

/**
 * @brief Read a single byte from SPI bus
 * @return Byte read from SPI bus
 */
uint8_t MAX31865_SPI_ReadByte(void);

/**
 * @brief Write multiple bytes to SPI bus
 * @param data Pointer to data buffer to write
 * @param length Number of bytes to write
 */
void MAX31865_SPI_WriteBytes(const uint8_t *data, uint16_t length);

/**
 * @brief Read multiple bytes from SPI bus
 * @param data Pointer to buffer where data will be stored
 * @param length Number of bytes to read
 */
void MAX31865_SPI_ReadBytes(uint8_t *data, uint16_t length);

/**
 * @brief Write and read simultaneously (full-duplex SPI transaction)
 * @param write_data Pointer to data to write
 * @param read_data Pointer to buffer for data to read
 * @param length Number of bytes to transfer
 */
void MAX31865_SPI_TransferBytes(const uint8_t *write_data, uint8_t *read_data, uint16_t length);

/**
 * @brief Assert Chip Select (pull CS low)
 */
void MAX31865_SPI_CS_Assert(void);

/**
 * @brief Deassert Chip Select (pull CS high)
 */
void MAX31865_SPI_CS_Deassert(void);

/**
 * @brief Perform SPI transaction: Assert CS, write/read data, deassert CS
 * @param write_data Pointer to data to write
 * @param read_data Pointer to buffer for data to read
 * @param length Number of bytes to transfer
 */
void MAX31865_SPI_Transaction(const uint8_t *write_data, uint8_t *read_data, uint16_t length);

#endif // MAX31865_H
