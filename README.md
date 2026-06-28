# Air Piano

A gesture-controlled piano that uses computer vision and a Raspberry Pi Pico 2W to physically press real piano keys using servo motors.

## Demo
*Add your demo video link here*

---

## How It Works

1. A laptop webcam feed is divided into **8 vertical zones**, one for each note: **C D E F G A B C**
2. **MediaPipe** (a pre-trained ML model by Google) detects your hand in real time
3. Hover your hand over a zone to aim at a note
4. **Close your fist** to press and hold that key
5. The laptop sends the zone number to the **Raspberry Pi Pico 2W** over USB serial
6. The Pico moves the corresponding **SG90 servo motor** via a **PCA9685 driver** to physically press the piano key
7. **Open your fist** to release the key
8. Sound comes from the real piano itself

---

## Hardware

| Component | Purpose |
|---|---|
| Raspberry Pi Pico 2W | Receives zone data and controls servos |
| PCA9685 16-channel servo driver | Controls up to 16 servos over I2C |
| 8x SG90 servo motors | Physically press the piano keys |
| Laptop with webcam | Runs hand detection and sends commands |
| USB cable | Connects laptop to Pico for serial communication |

### Wiring

| Pico 2W | PCA9685 |
|---|---|
| GP4 | SDA |
| GP5 | SCL |
| 3V3 | VCC |
| GND | GND |
| VBUS | V+ (servo power) |

Servos plug into PCA9685 channels 0-7 in order: C, D, E, F, G, A, B, C

---

## Software

### Laptop dependencies
```
pip install opencv-python mediapipe==0.10.9 numpy pyserial
```

### Pico
- MicroPython (installed via Thonny)
- No external libraries needed

---

## Files

| File | Runs on | Purpose |
|---|---|---|
| `air_piano.py` | Laptop | Camera feed, hand detection, zone logic, serial communication |
| `main.py` | Pico 2W | Receives zone number, controls servos via PCA9685 |
| `servo_test.py` | Pico 2W | Calibration tool for finding optimal rest/press angles |

---

## Setup and Running

### 1. Set up the Pico
1. Open **Thonny** and install MicroPython on the Pico 2W
2. Open `main.py` in Thonny and click **Run**
3. You should see `All servos at rest. Waiting for commands...`
4. **Close Thonny** to free up the serial port

### 2. Find your COM port
- **Windows** → Device Manager → Ports (COM & LPT) → note the COM number
- **Mac** → run `ls /dev/cu.*` in terminal

### 3. Run the laptop script
Open `air_piano.py` and set your port:
```python
PICO_PORT = 'COM7'   # change to your port
```
Then run:
```
python air_piano.py
```

### 4. Play
- A camera window opens showing 8 colored zones
- Hover your hand over a zone — it highlights and shows **READY**
- Close your fist — the servo presses the key and shows **HELD**
- Open your fist to release

---

## Calibration

Use `servo_test.py` in Thonny to find the right angles for your physical setup:

```python
sweep()          # see full range of motion
rest(90)         # test a rest angle
press(120)       # test a press angle
tap(90, 120)     # test a full tap
```

Once you find the right angles, update these in `main.py`:
```python
REST_DEG  = 90    # arm lifted off key
PRESS_DEG = 120   # arm pressing key down
```

---

## How Fist Detection Works

MediaPipe provides 21 landmark points on the hand. For each finger, the code compares the fingertip position to the middle knuckle (PIP joint). If the fingertip is below the knuckle in image coordinates, the finger is curled. All 4 fingers curled = fist detected = key pressed.

```
Index  → tip: 8,  PIP: 6
Middle → tip: 12, PIP: 10
Ring   → tip: 16, PIP: 14
Pinky  → tip: 20, PIP: 18
```

---

## Built With

- [OpenCV](https://opencv.org/) — camera access and frame drawing
- [MediaPipe](https://mediapipe.dev/) — real-time hand landmark detection
- [MicroPython](https://micropython.org/) — runs on the Raspberry Pi Pico 2W
- [PySerial](https://pyserial.readthedocs.io/) — USB serial communication

---

## Author

Vihaan — Electrical and Computer Engineering, The Ohio State University
