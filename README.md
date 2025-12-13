# Salda Smarty Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Custom integration for **Salda Smarty XP/XV** ventilation units via Modbus TCP.

## Features

- Multi-slave support (multiple ventilation units on the same gateway)
- Serialized Modbus requests to avoid gateway conflicts
- Fan control with speed presets
- Sensors for temperature, humidity, and air quality
- Binary sensors for filter status and alarms
- Switches for boost mode and other functions
- Button entities for filter reset

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click on "Integrations"
3. Click the three dots in the top right corner
4. Select "Custom repositories"
5. Add this repository URL and select "Integration" as the category
6. Click "Add"
7. Search for "Salda Smarty" and install it
8. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/salda_smarty` folder to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Configuration

1. Go to **Settings** → **Devices & Services**
2. Click **Add Integration**
3. Search for "Salda Smarty"
4. Enter your Modbus gateway IP address and select the slave IDs for your ventilation units

## Requirements

- Salda Smarty XP or XV ventilation unit
- Modbus TCP gateway connected to the ventilation unit
- Home Assistant 2024.1.0 or newer

## License

This project is licensed under the MIT License.
