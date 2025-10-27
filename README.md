# 802.11ah HaLow Channel Scanner

A Python script that uses an RTL-SDR USB dongle to scan 802.11ah (WiFi HaLow) channels in the sub-GHz spectrum and determine which channel has the least noise/interference.

## Features

- 🔍 Scans all 802.11ah HaLow channels in the US 902-928 MHz band
- 📊 Supports multiple channel bandwidths: 1, 2, 4, and 8 MHz
- 📡 Uses RTL-SDR for spectrum analysis
- 🎯 Identifies the cleanest channel with lowest noise floor
- 📈 Provides detailed power spectrum measurements
- ⚡ Fast scanning with averaging for accuracy

## Requirements

### Hardware
- RTL-SDR USB dongle (RTL2832U-based)
  - Must support sub-GHz frequencies (some RTL-SDR dongles don't go below 24 MHz)
  - Consider using an upconverter if your RTL-SDR doesn't support sub-GHz
  - Recommended: RTL-SDR Blog V3 or similar with direct sampling mode

### Software
- Python 3.7+
- pyrtlsdr library
- numpy

## Installation

1. **Install RTL-SDR drivers**

   On Ubuntu/Debian:
   ```bash
   sudo apt-get update
   sudo apt-get install rtl-sdr librtlsdr-dev
   ```

   On macOS:
   ```bash
   brew install librtlsdr
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure RTL-SDR access** (Linux only)

   Create udev rules to allow non-root access:
   ```bash
   sudo bash -c 'cat > /etc/udev/rules.d/20-rtlsdr.rules << EOF
   SUBSYSTEM=="usb", ATTRS{idVendor}=="0bda", ATTRS{idProduct}=="2838", MODE="0666"
   EOF'

   sudo udevadm control --reload-rules
   sudo udevadm trigger
   ```

4. **Test RTL-SDR connection**
   ```bash
   rtl_test
   ```

## Usage

### Basic Usage

Scan all channels with 2 MHz bandwidth:
```bash
python halow_scanner.py
```

### Advanced Options

Scan with 4 MHz bandwidth:
```bash
python halow_scanner.py -b 4
```

Scan all available bandwidths:
```bash
python halow_scanner.py --all-bandwidths
```

Less verbose output:
```bash
python halow_scanner.py -b 2 -q
```

Custom sample rate (2.4 MHz):
```bash
python halow_scanner.py -s 2.4
```

### Command Line Arguments

```
  -h, --help            Show help message
  -b, --bandwidth       Channel bandwidth in MHz: 1, 2, 4, or 8 (default: 2)
  -r, --region          Regulatory region: US (default: US)
  -s, --sample-rate     SDR sample rate in MHz (default: 2.4)
  -q, --quiet           Less verbose output
  --all-bandwidths      Scan all available bandwidths
```

## Output Example

```
============================================================
Scanning 802.11ah HaLow Channels (US region)
Bandwidth: 2 MHz
============================================================

  Scanning channel 1 @ 906 MHz (BW: 2 MHz)...
    Noise floor: -45.23 dB
    Avg power:   -42.15 dB

  Scanning channel 2 @ 908 MHz (BW: 2 MHz)...
    Noise floor: -48.67 dB
    Avg power:   -44.32 dB

[...]

============================================================
SCAN RESULTS (Sorted by cleanest channel)
============================================================
Rank   Ch   Freq(MHz)    BW(MHz)   Noise(dB)   AvgPwr(dB)
------------------------------------------------------------
★1     6    916.0        2.0       -51.23      -47.45
 2     5    914.0        2.0       -49.87      -46.12
 3     2    908.0        2.0       -48.67      -44.32
[...]

============================================================
★ CLEANEST CHANNEL: Channel 6 @ 916.0 MHz (Noise: -51.23 dB)
============================================================
```

## 802.11ah Channel Information

### US 902-928 MHz Band

| Channel | Center Freq (MHz) | Available Bandwidths |
|---------|-------------------|---------------------|
| 1       | 906               | 1, 2 MHz            |
| 2       | 908               | 1, 2 MHz            |
| 3       | 910               | 1, 2 MHz            |
| 4       | 912               | 1, 2, 4 MHz         |
| 5       | 914               | 1, 2, 4 MHz         |
| 6       | 916               | 1, 2, 4 MHz         |
| 7       | 918               | 1, 2, 4 MHz         |
| 8       | 920               | 1, 2, 4 MHz         |
| 9       | 922               | 1, 2, 4 MHz         |
| 10      | 924               | 1, 2, 4, 8 MHz      |

## How It Works

1. **Initialization**: Configures the RTL-SDR dongle with specified sample rate
2. **Tuning**: Centers the SDR on each channel's frequency
3. **Sampling**: Collects IQ samples from the SDR
4. **FFT Analysis**: Performs Fast Fourier Transform to get frequency spectrum
5. **Power Calculation**: Converts to power spectral density in dB
6. **Noise Estimation**: Uses 10th percentile of power to estimate noise floor
7. **Ranking**: Sorts channels by noise level to find the cleanest

## Important Notes

⚠️ **RTL-SDR Sub-GHz Limitations**
- Most RTL-SDR dongles don't support frequencies below 24 MHz natively
- For 902-928 MHz (HaLow), you need:
  - An RTL-SDR with direct sampling mode (e.g., RTL-SDR Blog V3)
  - Or an upconverter to shift the frequency range
  - Or a specialized SDR like HackRF One, LimeSDR, or USRP

⚠️ **Regulatory Compliance**
- Ensure you have proper authorization to transmit on HaLow frequencies
- This scanner only receives and does not transmit
- Check local regulations for sub-GHz ISM band usage

⚠️ **Antenna Considerations**
- Use an appropriate antenna for 900 MHz band
- Quarter-wave antenna length: ~8.2 cm
- Antenna placement affects measurements significantly

## Troubleshooting

**Error: "Failed to initialize RTL-SDR"**
- Check if RTL-SDR is connected: `lsusb | grep RTL`
- Verify drivers: `rtl_test`
- Check permissions (see Installation step 3)

**No devices found**
- Make sure no other software is using the RTL-SDR (SDR#, GQRX, etc.)
- Try unplugging and reconnecting the dongle

**Poor sensitivity / High noise floor**
- Check antenna connection
- Try different gain settings
- Move away from interference sources (computers, monitors)
- Use a battery-powered laptop for cleaner power

## Future Enhancements

- [ ] Support for EU, China, Japan, Korea frequency allocations
- [ ] GUI interface for real-time visualization
- [ ] Save scan results to file (CSV, JSON)
- [ ] Waterfall display of spectrum over time
- [ ] Support for other SDR hardware (HackRF, LimeSDR, etc.)
- [ ] Interference source identification

## License

MIT License - Feel free to use and modify

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

## References

- [IEEE 802.11ah Standard](https://standards.ieee.org/standard/802_11ah-2016.html)
- [RTL-SDR](https://www.rtl-sdr.com/)
- [pyrtlsdr Documentation](https://pyrtlsdr.readthedocs.io/)
