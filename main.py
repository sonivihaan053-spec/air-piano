"""
Pico 2W — 8 Servo Piano Key Controller (Hold mode)
----------------------------------------------------
Receives commands from the laptop over USB serial:
  '0'–'7' → press that servo's key down and hold it
  'x'     → release whichever key is currently held

Servo channels on PCA9685:
  Channel 0 → C
  Channel 1 → D
  Channel 2 → E
  Channel 3 → F
  Channel 4 → G
  Channel 5 → A
  Channel 6 → B
  Channel 7 → C (high)

Wiring:
  Pico GPIO 4  →  PCA9685 SDA
  Pico GPIO 5  →  PCA9685 SCL
  Pico 3V3     →  PCA9685 VCC
  Pico GND     →  PCA9685 GND
  Pico VBUS    →  PCA9685 V+  (servo power rail)
  Servos       →  CH0 through CH7
"""

import machine
import sys
import time


# ═══════════════════════════════════════════════════════════════
#  PCA9685 DRIVER
# ═══════════════════════════════════════════════════════════════

class PCA9685:
    MODE1     = 0x00
    PRESCALE  = 0xFE
    LED0_ON_L = 0x06

    def __init__(self, i2c, address=0x40):
        self.i2c  = i2c
        self.addr = address
        self.i2c.writeto_mem(self.addr, self.MODE1, bytes([0x00]))
        time.sleep(0.01)

    def set_pwm_freq(self, freq_hz):
        prescale = int(25_000_000 / (4096 * freq_hz) + 0.5) - 1
        self.i2c.writeto_mem(self.addr, self.MODE1,    bytes([0x10]))
        self.i2c.writeto_mem(self.addr, self.PRESCALE, bytes([prescale]))
        self.i2c.writeto_mem(self.addr, self.MODE1,    bytes([0x00]))
        time.sleep(0.01)
        self.i2c.writeto_mem(self.addr, self.MODE1,    bytes([0xA0]))

    def set_pwm(self, channel, on, off):
        reg = self.LED0_ON_L + 4 * channel
        self.i2c.writeto_mem(self.addr, reg,
                             bytes([on & 0xFF, on >> 8,
                                    off & 0xFF, off >> 8]))


# ═══════════════════════════════════════════════════════════════
#  SERVO ANGLES
#  Adjust these to match your physical setup.
#  Use servo_test.py to find the right values.
#  REST_DEG  = arm lifted off the key
#  PRESS_DEG = arm pushing the key down
# ═══════════════════════════════════════════════════════════════

REST_DEG  = 90
PRESS_DEG = 120

SERVO_MIN_TICKS = 205
SERVO_MAX_TICKS = 410
NUM_SERVOS      = 8
NOTE_NAMES      = ['C', 'D', 'E', 'F', 'G', 'A', 'B', 'C2']


def angle_to_ticks(angle_deg):
    angle_deg = max(0, min(180, angle_deg))
    return int(SERVO_MIN_TICKS +
               (angle_deg / 180.0) * (SERVO_MAX_TICKS - SERVO_MIN_TICKS))


def move_servo(pca, channel, angle_deg):
    pca.set_pwm(channel, 0, angle_to_ticks(angle_deg))


def press_key(pca, channel):
    """Push the key down and hold it there."""
    move_servo(pca, channel, PRESS_DEG)
    print(f"  Pressing {NOTE_NAMES[channel]} (ch{channel}) at {PRESS_DEG}")


def release_key(pca, channel):
    """Lift the servo back to rest position."""
    move_servo(pca, channel, REST_DEG)
    print(f"  Released {NOTE_NAMES[channel]} (ch{channel})")


# ═══════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    i2c = machine.I2C(0,
                      sda=machine.Pin(4),
                      scl=machine.Pin(5),
                      freq=400_000)

    devices = i2c.scan()
    print("I2C devices found:", [hex(d) for d in devices])

    if 0x40 not in devices:
        print("ERROR: PCA9685 not found. Check wiring.")
        return

    pca = PCA9685(i2c)
    pca.set_pwm_freq(50)
    print("PCA9685 ready.")

    for ch in range(NUM_SERVOS):
        move_servo(pca, ch, REST_DEG)
    time.sleep(0.5)
    print("All servos at rest. Waiting for commands...")

    held_channel = -1

    while True:
        char = sys.stdin.read(1)

        if char in ('0', '1', '2', '3', '4', '5', '6', '7'):
            new_channel = int(char)
            if held_channel != -1 and held_channel != new_channel:
                release_key(pca, held_channel)
            if new_channel != held_channel:
                press_key(pca, new_channel)
                held_channel = new_channel

        elif char == 'x':
            if held_channel != -1:
                release_key(pca, held_channel)
                held_channel = -1


if __name__ == '__main__':
    main()