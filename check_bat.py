#!/usr/bin/env python3
from smbus2 import SMBus

BAT_ADDRESS = 0x75

def read_battery_v():
    with SMBus(1) as bus:
        low = bus.read_byte_data(BAT_ADDRESS, 0xa2)
        high = bus.read_byte_data(BAT_ADDRESS, 0xa3)
        if high & 0x20:
            low = ~low & 0xff
            high = (~high) & 0x1f
            v = -(high * 256 + low + 1) * 0.26855 + 2600
        else:
            v = ((high & 0x1f) * 256 + low + 1) * 0.26855 + 2600
    return v

def get_battery_percent():
    batter_curve = [
        [4.16, 5.5, 100, 100],
        [4.05, 4.16, 87.5, 100],
        [4.00, 4.05, 75, 87.5],
        [3.92, 4.00, 62.5, 75],
        [3.86, 3.92, 50, 62.5],
        [3.79, 3.86, 37.5, 50],
        [3.66, 3.79, 25, 37.5],
        [3.52, 3.66, 12.5, 25],
        [3.49, 3.52, 6.2, 12.5],
        [3.1, 3.49, 0, 6.2],
        [0, 3.1, 0, 0],
    ]
    v = read_battery_v()
    batter_level = 0
    for range in batter_curve:
        if range[0] < v / 1000 <= range[1]:
            level_base = ((v / 1000 - range[0]) / (range[1] - range[0])) * (range[3] - range[2])
            batter_level = level_base + range[2]
    return batter_level

if __name__ == "__main__":
    print(get_battery_percent())
