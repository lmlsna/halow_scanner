#!/usr/bin/env python3
"""
802.11ah (HaLow) Channel Scanner using RTL-SDR
Scans sub-GHz WiFi HaLow channels to find the cleanest one with least noise.

MIT License - Copyright (c) 2025
"""

import numpy as np
from rtlsdr import RtlSdr
import time
import argparse
import csv
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class ChannelInfo:
    """Information about a WiFi HaLow channel"""
    number: int
    center_freq_mhz: float
    bandwidth_mhz: float
    noise_floor_db: float = 0.0
    avg_power_db: float = 0.0


class HaLowScanner:
    """Scanner for 802.11ah HaLow channels using RTL-SDR"""

    def __init__(self, region: str = 'US', sample_rate: int = 2_400_000,
                 channels_csv: str = 'halow_channels.csv'):
        """
        Initialize the HaLow scanner

        Args:
            region: Region code (e.g., 'US', 'EU', 'CN', 'JP', 'KR')
            sample_rate: SDR sample rate in Hz (default 2.4 MHz)
            channels_csv: Path to CSV file with channel definitions
        """
        self.region = region
        self.sample_rate = sample_rate
        self.sdr = None
        self.channels = self._load_channels_from_csv(channels_csv, region)

        if not self.channels:
            raise ValueError(f"No channels found for region {region} in {channels_csv}")

    def _load_channels_from_csv(self, csv_path: str, region: str) -> Dict[int, Tuple[float, List[float]]]:
        """
        Load channel definitions from CSV file

        Args:
            csv_path: Path to the CSV file
            region: Region code to filter by

        Returns:
            Dictionary mapping channel number to (center_freq_MHz, available_bandwidths_MHz)
        """
        channels = {}
        csv_file = Path(csv_path)

        if not csv_file.exists():
            # Try relative to script directory
            script_dir = Path(__file__).parent
            csv_file = script_dir / csv_path

        if not csv_file.exists():
            raise FileNotFoundError(f"Channel CSV file not found: {csv_path}")

        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Skip empty rows
                if not row or 'country_code' not in row or not row['country_code']:
                    continue

                if row['country_code'].strip() == region:
                    channel_num = int(row['s1g_chan'])
                    center_freq = float(row['centre_freq_mhz'])
                    bandwidth = float(row['bw'])

                    if channel_num not in channels:
                        channels[channel_num] = (center_freq, [])

                    # Add bandwidth if not already present
                    if bandwidth not in channels[channel_num][1]:
                        channels[channel_num][1].append(bandwidth)

        # Sort bandwidths for each channel
        for channel_num in channels:
            center_freq, bandwidths = channels[channel_num]
            channels[channel_num] = (center_freq, sorted(bandwidths))

        return channels

    def initialize_sdr(self) -> bool:
        """Initialize the RTL-SDR device"""
        try:
            self.sdr = RtlSdr()
            self.sdr.sample_rate = self.sample_rate
            self.sdr.gain = 'auto'  # Use automatic gain control
            print(f"✓ RTL-SDR initialized successfully")
            print(f"  Sample rate: {self.sample_rate / 1e6:.2f} MHz")
            return True
        except Exception as e:
            print(f"✗ Failed to initialize RTL-SDR: {e}")
            print("  Make sure your RTL-SDR dongle is connected")
            return False

    def close_sdr(self):
        """Close the RTL-SDR device"""
        if self.sdr:
            self.sdr.close()
            self.sdr = None

    def measure_power_spectrum(self, center_freq_hz: float,
                               num_samples: int = 256*1024,
                               num_iterations: int = 3) -> Tuple[np.ndarray, np.ndarray]:
        """
        Measure power spectrum at a given frequency

        Args:
            center_freq_hz: Center frequency in Hz
            num_samples: Number of samples to collect
            num_iterations: Number of measurements to average

        Returns:
            Tuple of (frequencies, power_spectrum_db)
        """
        self.sdr.center_freq = center_freq_hz

        # Allow SDR to settle
        time.sleep(0.1)

        # Collect and average multiple measurements
        power_accumulator = None

        for i in range(num_iterations):
            samples = self.sdr.read_samples(num_samples)

            # Compute FFT
            fft = np.fft.fftshift(np.fft.fft(samples))

            # Convert to power (magnitude squared)
            power = np.abs(fft) ** 2

            if power_accumulator is None:
                power_accumulator = power
            else:
                power_accumulator += power

        # Average the power
        power_avg = power_accumulator / num_iterations

        # Convert to dB
        power_db = 10 * np.log10(power_avg + 1e-10)  # Add small value to avoid log(0)

        # Generate frequency axis
        freq_step = self.sample_rate / num_samples
        frequencies = np.arange(-self.sample_rate/2, self.sample_rate/2, freq_step)
        frequencies = frequencies[:len(power_db)]  # Ensure same length

        return frequencies, power_db

    def analyze_channel(self, channel_num: int, bandwidth_mhz: float,
                       verbose: bool = False) -> ChannelInfo:
        """
        Analyze a specific channel to measure noise and interference

        Args:
            channel_num: Channel number
            bandwidth_mhz: Bandwidth to analyze (1, 2, 4, or 8 MHz)
            verbose: Print detailed information

        Returns:
            ChannelInfo object with measurement results
        """
        if channel_num not in self.channels:
            raise ValueError(f"Invalid channel number: {channel_num}")

        center_freq_mhz, available_bw = self.channels[channel_num]

        if bandwidth_mhz not in available_bw:
            raise ValueError(f"Bandwidth {bandwidth_mhz} MHz not available for channel {channel_num}")

        center_freq_hz = center_freq_mhz * 1e6

        if verbose:
            print(f"\n  Scanning channel {channel_num} @ {center_freq_mhz} MHz "
                  f"(BW: {bandwidth_mhz} MHz)...")

        # Measure power spectrum
        frequencies, power_db = self.measure_power_spectrum(center_freq_hz)

        # Analyze only the relevant bandwidth
        bandwidth_hz = bandwidth_mhz * 1e6
        freq_mask = np.abs(frequencies) <= bandwidth_hz / 2
        channel_power = power_db[freq_mask]

        # Calculate noise floor (use lower percentile to estimate noise)
        noise_floor = np.percentile(channel_power, 10)

        # Calculate average power
        avg_power = np.mean(channel_power)

        channel_info = ChannelInfo(
            number=channel_num,
            center_freq_mhz=center_freq_mhz,
            bandwidth_mhz=bandwidth_mhz,
            noise_floor_db=noise_floor,
            avg_power_db=avg_power
        )

        if verbose:
            print(f"    Noise floor: {noise_floor:.2f} dB")
            print(f"    Avg power:   {avg_power:.2f} dB")

        return channel_info

    def scan_all_channels(self, bandwidth_mhz: float = 2,
                          verbose: bool = True) -> List[ChannelInfo]:
        """
        Scan all available channels for the specified bandwidth

        Args:
            bandwidth_mhz: Bandwidth to scan (1, 2, 4, or 8 MHz)
            verbose: Print detailed information

        Returns:
            List of ChannelInfo objects sorted by noise level (cleanest first)
        """
        if not self.sdr:
            raise RuntimeError("SDR not initialized. Call initialize_sdr() first.")

        print(f"\n{'='*60}")
        print(f"Scanning 802.11ah HaLow Channels ({self.region} region)")
        print(f"Bandwidth: {bandwidth_mhz} MHz")
        print(f"{'='*60}")

        results = []

        for channel_num in sorted(self.channels.keys()):
            center_freq, available_bw = self.channels[channel_num]

            # Skip channels that don't support this bandwidth
            if bandwidth_mhz not in available_bw:
                continue

            try:
                channel_info = self.analyze_channel(channel_num, bandwidth_mhz, verbose)
                results.append(channel_info)
            except Exception as e:
                print(f"  Error scanning channel {channel_num}: {e}")

        # Sort by noise floor (lower is better)
        results.sort(key=lambda x: x.noise_floor_db)

        return results

    def print_results(self, results: List[ChannelInfo]):
        """Print scan results in a formatted table"""
        print(f"\n{'='*60}")
        print("SCAN RESULTS (Sorted by cleanest channel)")
        print(f"{'='*60}")
        print(f"{'Rank':<6} {'Ch':<4} {'Freq(MHz)':<12} {'BW(MHz)':<9} "
              f"{'Noise(dB)':<11} {'AvgPwr(dB)':<11}")
        print(f"{'-'*60}")

        for rank, channel in enumerate(results, 1):
            marker = "★" if rank == 1 else " "
            print(f"{marker}{rank:<5} {channel.number:<4} "
                  f"{channel.center_freq_mhz:<12.1f} {channel.bandwidth_mhz:<9.1f} "
                  f"{channel.noise_floor_db:<11.2f} {channel.avg_power_db:<11.2f}")

        if results:
            print(f"\n{'='*60}")
            best = results[0]
            print(f"★ CLEANEST CHANNEL: Channel {best.number} "
                  f"@ {best.center_freq_mhz} MHz "
                  f"(Noise: {best.noise_floor_db:.2f} dB)")
            print(f"{'='*60}\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Scan 802.11ah HaLow channels using RTL-SDR to find the cleanest channel',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan all channels with 2 MHz bandwidth
  python halow_scanner.py -b 2

  # Scan with 4 MHz bandwidth, less verbose
  python halow_scanner.py -b 4 -q

  # Scan all available bandwidths
  python halow_scanner.py --all-bandwidths
        """
    )

    parser.add_argument('-b', '--bandwidth', type=float, default=2,
                       choices=[1, 2, 4, 8],
                       help='Channel bandwidth in MHz (default: 2)')

    parser.add_argument('-r', '--region', type=str, default='US',
                       help='Regulatory region code (e.g., US, EU, CN, JP, KR) (default: US)')

    parser.add_argument('-s', '--sample-rate', type=float, default=2.4,
                       help='SDR sample rate in MHz (default: 2.4)')

    parser.add_argument('-q', '--quiet', action='store_true',
                       help='Less verbose output')

    parser.add_argument('--all-bandwidths', action='store_true',
                       help='Scan all available bandwidths')

    parser.add_argument('--channels-csv', type=str, default='halow_channels.csv',
                       help='Path to channel definitions CSV file (default: halow_channels.csv)')

    args = parser.parse_args()

    # Create scanner
    try:
        scanner = HaLowScanner(
            region=args.region,
            sample_rate=int(args.sample_rate * 1e6),
            channels_csv=args.channels_csv
        )
    except (FileNotFoundError, ValueError) as e:
        print(f"Error loading channel definitions: {e}")
        return 1

    # Initialize SDR
    if not scanner.initialize_sdr():
        return 1

    try:
        if args.all_bandwidths:
            # Scan all bandwidths
            for bw in [1, 2, 4, 8]:
                results = scanner.scan_all_channels(bw, verbose=not args.quiet)
                scanner.print_results(results)
                time.sleep(0.5)  # Brief pause between scans
        else:
            # Scan single bandwidth
            results = scanner.scan_all_channels(args.bandwidth, verbose=not args.quiet)
            scanner.print_results(results)

    except KeyboardInterrupt:
        print("\n\nScan interrupted by user")
    except Exception as e:
        print(f"\nError during scan: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        scanner.close_sdr()
        print("RTL-SDR closed")

    return 0


if __name__ == '__main__':
    exit(main())
