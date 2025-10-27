#!/usr/bin/env python3
"""
Test script to verify channel loading from CSV without needing RTL-SDR hardware

MIT License - Copyright (c) 2025
"""

import sys
from halow_scanner import HaLowScanner

def test_channel_loading():
    """Test loading channels from CSV for different regions"""

    regions = ['US']  # Add more regions as they appear in your CSV

    for region in regions:
        print(f"\n{'='*60}")
        print(f"Testing channel loading for region: {region}")
        print(f"{'='*60}")

        try:
            # Create scanner without initializing SDR
            scanner = HaLowScanner(region=region, channels_csv='halow_channels.csv')

            print(f"\n✓ Successfully loaded {len(scanner.channels)} channels for {region}")
            print(f"\nChannel definitions:")
            print(f"{'Channel':<10} {'Freq (MHz)':<15} {'Bandwidths (MHz)'}")
            print(f"{'-'*50}")

            for channel_num in sorted(scanner.channels.keys()):
                center_freq, bandwidths = scanner.channels[channel_num]
                bw_str = ', '.join(map(str, bandwidths))
                print(f"{channel_num:<10} {center_freq:<15.1f} {bw_str}")

            # Test bandwidth availability
            print(f"\n{'='*60}")
            print(f"Bandwidth statistics for {region}:")
            print(f"{'='*60}")

            bw_counts = {1: 0, 2: 0, 4: 0, 8: 0}
            for channel_num, (center_freq, bandwidths) in scanner.channels.items():
                for bw in bandwidths:
                    if bw in bw_counts:
                        bw_counts[bw] += 1

            for bw in sorted(bw_counts.keys()):
                print(f"  {bw} MHz: {bw_counts[bw]} channels")

        except Exception as e:
            print(f"\n✗ Error loading channels for {region}: {e}")
            import traceback
            traceback.print_exc()
            return False

    return True

if __name__ == '__main__':
    success = test_channel_loading()
    sys.exit(0 if success else 1)
