# Quantum Inspired Early Warning System for Structural Failure

A low-cost structural health monitoring prototype. An Arduino UNO reads a flexible (strain) sensor and an SW420 vibration sensor, a Python program fuses the two readings into a single weighted risk index, and the structure is classified as **SAFE**, **WARNING** or **DANGER** with traffic-light LED and buzzer feedback.

**Quantum-inspired idea:** strain and vibration are observed together, weighted like probabilities (the weights sum to 1), and "collapsed" into one observable risk state, in analogy with the measurement of a quantum superposition. This is a conceptual metaphor for sensor fusion, not a quantum computation.

## How it works

1. The Arduino sends readings 10 times per second as `FLEX:<0-1023>,VIB:<0-1023>`.
2. `risk_monitor.py` calibrates a baseline from the first 20 readings (structure at rest).
3. Each reading goes through a sliding-window average (10 samples) to reduce noise.
4. Risk index = 0.6 x strain + 0.4 x vibration, where each term is the deviation from its baseline scaled to 0-1.
5. The risk is classified and a one-letter command (`S`, `W` or `D`) is sent back to the Arduino.

| Risk index | Status | Green LED | Yellow LED | Red LED | Buzzer |
|---|---|---|---|---|---|
| below 0.30 | SAFE | on | off | off | off |
| 0.30 to 0.59 | WARNING | off | on | off | short beep every second |
| 0.60 and above | DANGER | off | off | on | continuous |

The weights, window size, sensor ranges and thresholds are constants at the top of `risk_monitor.py`. The values above are defaults; tune them to your sensors and make sure they match the thresholds in your report.

## Hardware

- Arduino UNO
- Flexible (bend/strain) sensor with a fixed resistor as a voltage divider
- SW420 vibration sensor module
- Traffic light LED module (red, yellow, green)
- 5V active buzzer
- Breadboard and jumper wires

### Pin connections

| Component | Arduino pin |
|---|---|
| Flexible sensor (divider output) | A0 |
| SW420 vibration sensor (output) | A1 |
| Traffic light: green | D8 |
| Traffic light: yellow | D9 |
| Traffic light: red | D10 |
| Buzzer (+) | D11 |
| Sensors VCC / GND, LED module GND, buzzer (-) | 5V / GND |

If your SW420 module only has a digital output, connect it to A1 as well. It will read near 0 or 1023, and the sliding-window average still gives a usable vibration level.

## Project structure

```
structural_monitor.ino    Arduino firmware
risk_monitor.py           Risk monitor (hardware or simulation)
test_risk_monitor.py      Unit tests
requirements.txt          Python dependency (pyserial)
sample_log.csv            Log from a simulated run
```

## Setup and run

1. Open `structural_monitor.ino` in the Arduino IDE (it will offer to put it in a folder named `structural_monitor`; accept), select **Arduino UNO** and your port, and upload.
2. Close the Arduino Serial Monitor, since only one program can use the port at a time.
3. Install the dependency and run the monitor:

```bash
pip install -r requirements.txt
python risk_monitor.py --port COM3        # Windows example
python risk_monitor.py --port /dev/ttyUSB0  # Linux example
```

Add `--log run.csv` to save a CSV log. Keep the structure at rest while the baseline is calibrated.

### Try it without hardware

```bash
python risk_monitor.py --simulate
```

Sample output from a simulated run (rest, rising stress, severe vibration, recovery):

```
Calibrating for 20 readings - keep the structure at rest...
Baseline: FLEX=300  VIB=44

 Time(s)   FLEX   VIB    Risk  Status
     0.0    300    44    0.1%  SAFE
     1.1    300    45    0.2%  SAFE
     2.2    328    61   10.6%  SAFE
     3.3    374    84   27.8%  SAFE
     4.4    416   110   43.7%  WARNING
     5.5    470   274   81.9%  DANGER
     6.6    470   274   81.8%  DANGER
     7.7    439   230   66.5%  DANGER
     8.8    320    54    7.4%  SAFE
     9.9    319    53    7.1%  SAFE
```

### Run the tests

```bash
python -m unittest
```

## Concepts used

Embedded systems (Arduino, analog sensing, digital outputs), serial communication, sliding-window noise reduction, weighted sensor fusion, threshold classification, and unit testing.

## Future scope

Wireless communication (ESP32/Wi-Fi), IoT cloud dashboard, additional sensors such as an accelerometer, and machine-learning-based anomaly detection.

## Author

Arunachalapriyan S
