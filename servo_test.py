"""
Servo Calibration Tool
-----------------------
Run this in Thonny to find the perfect REST and PRESS angles
for your servo setup before using the full piano code.

How to use:
  1. Run this script in Thonny
  2. In the Thonny console (>>> prompt), type commands to test
  3. Note down the angles that feel right
  4. Copy those values into main.py

Available commands to type in the console:
  rest(angle)      → move servo to that angle (test rest position)
  press(angle)     → move servo to that angle (test press position)
  tap(rest, press) → do a full tap between two angles
  sweep()          → slowly sweep 0 to 180 so you can see full range
  center()         → move to 90 (safe starting point)
"""

import machine
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
#  SETUP
# ═══════════════════════════════════════════════════════════════

SERVO_MIN_TICKS = 205
SERVO_MAX_TICKS = 410

# Change this to whichever servo channel you are testing (0-7)
TEST_CHANNEL = 0

i2c = machine.I2C(0, sda=machine.Pin(4), scl=machine.Pin(5), freq=400_000)
devices = i2c.scan()
print("I2C devices:", [hex(d) for d in devices])

if 0x40 not in devices:
    print("ERROR: PCA9685 not found. Check wiring.")
else:
    pca = PCA9685(i2c)
    pca.set_pwm_freq(50)
    print(f"Ready. Testing channel {TEST_CHANNEL}.")
    print()
    print("Commands:")
    print("  rest(90)         move to angle 90")
    print("  press(120)       move to angle 120")
    print("  tap(90, 120)     full tap: press then return to rest")
    print("  sweep()          sweep from 0 to 180 slowly")
    print("  center()         move to 90 safe center")
    print()


# ═══════════════════════════════════════════════════════════════
#  HELPER FUNCTIONS — type these in the Thonny console
# ═══════════════════════════════════════════════════════════════

def angle_to_ticks(angle_deg):
    angle_deg = max(0, min(180, angle_deg))
    return int(SERVO_MIN_TICKS +
               (angle_deg / 180.0) * (SERVO_MAX_TICKS - SERVO_MIN_TICKS))

def move(angle_deg):
    pca.set_pwm(TEST_CHANNEL, 0, angle_to_ticks(angle_deg))
    print(f"  Moved to {angle_deg}")

def rest(angle_deg):
    move(angle_deg)
    print(f"  REST candidate: {angle_deg}")
    print("  Is the arm lifted cleanly off the key?")

def press(angle_deg):
    move(angle_deg)
    print(f"  PRESS candidate: {angle_deg}")
    print("  Did the key trigger a note?")

def tap(rest_deg, press_deg, hold_ms=80):
    print(f"  Tapping: rest={rest_deg} press={press_deg}")
    pca.set_pwm(TEST_CHANNEL, 0, angle_to_ticks(press_deg))
    time.sleep(hold_ms / 1000)
    pca.set_pwm(TEST_CHANNEL, 0, angle_to_ticks(rest_deg))
    print("  Done. Did the note play cleanly?")

def sweep():
    print("  Sweeping 0 to 180 to 0 ...")
    for angle in range(0, 181, 5):
        move(angle)
        time.sleep(0.05)
    for angle in range(180, -1, -5):
        move(angle)
        time.sleep(0.05)
    print("  Sweep done.")

def center():
    move(90)
    print("  Centered at 90.")