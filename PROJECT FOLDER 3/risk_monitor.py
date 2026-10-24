"""
Quantum Inspired Early Warning System for Structural Failure - risk monitor.

Reads FLEX / VIB readings from the Arduino over serial (or from a built-in
simulator), smooths them with a sliding window, fuses them into one weighted
risk index and classifies the structure as SAFE, WARNING or DANGER.

Quantum-inspired idea: strain and vibration are observed together, weighted
like probabilities (the weights sum to 1), and "collapsed" into one observable
risk state - an analogy to measurement of a superposition.
"""
import argparse
import csv
import math
import random
import time
from collections import deque

# ---------------- Configuration (tune these to your sensors) ----------------
WEIGHT_STRAIN = 0.6        # weight of the flexible-sensor (strain) component
WEIGHT_VIBRATION = 0.4     # weight of the vibration component (weights sum to 1)
WINDOW_SIZE = 10           # sliding-window length for noise reduction
CALIBRATION_SAMPLES = 20   # readings used to learn the "at rest" baseline
FLEX_RANGE = 200.0         # ADC change from baseline that counts as full strain
VIB_RANGE = 300.0          # ADC change from baseline that counts as full vibration
WARNING_THRESHOLD = 0.30   # risk >= this  -> WARNING
DANGER_THRESHOLD = 0.60    # risk >= this  -> DANGER

STATUS_COMMAND = {"SAFE": "S", "WARNING": "W", "DANGER": "D"}


class SlidingWindow:
    """Moving average over the last `size` readings."""

    def __init__(self, size=WINDOW_SIZE):
        self.values = deque(maxlen=size)

    def add(self, value):
        self.values.append(value)
        return sum(self.values) / len(self.values)


def parse_line(line):
    """Parse 'FLEX:512,VIB:130' into (512, 130). Return None if malformed."""
    try:
        flex_part, vib_part = line.strip().split(",")
        flex_key, flex_val = flex_part.split(":")
        vib_key, vib_val = vib_part.split(":")
        if flex_key != "FLEX" or vib_key != "VIB":
            return None
        flex, vib = int(flex_val), int(vib_val)
    except ValueError:
        return None
    if not (0 <= flex <= 1023 and 0 <= vib <= 1023):
        return None
    return flex, vib


def normalise(value, baseline, span):
    """Deviation from baseline scaled to 0..1."""
    return min(abs(value - baseline) / span, 1.0)


def compute_risk(flex_avg, vib_avg, flex_base, vib_base):
    """Weighted risk index in the range 0..1."""
    strain = normalise(flex_avg, flex_base, FLEX_RANGE)
    vibration = normalise(vib_avg, vib_base, VIB_RANGE)
    return WEIGHT_STRAIN * strain + WEIGHT_VIBRATION * vibration


def classify(risk):
    """Collapse the risk index into one of three structural states."""
    if risk >= DANGER_THRESHOLD:
        return "DANGER"
    if risk >= WARNING_THRESHOLD:
        return "WARNING"
    return "SAFE"


def simulated_readings(steps, seed=42):
    """Yield synthetic (flex, vib) readings: rest, rising stress, impact, recovery."""
    rng = random.Random(seed)
    for i in range(steps):
        t = i / steps
        if t < 0.25:                       # calm structure
            strain, vibration = 0, 0
        elif t < 0.55:                     # strain slowly accumulates
            strain, vibration = (t - 0.25) / 0.30 * 140, (t - 0.25) / 0.30 * 80
        elif t < 0.80:                     # severe stress with vibration burst
            strain, vibration = 170, 230
        else:                              # structure recovers
            strain, vibration = 20, 10
        flex = int(300 + strain + rng.gauss(0, 4))
        vib = int(40 + vibration + abs(rng.gauss(0, 6)))
        yield max(0, min(flex, 1023)), max(0, min(vib, 1023))


def serial_readings(port, baud):
    """Yield ((flex, vib), serial_link) for every valid line sent by the Arduino."""
    import serial  # pyserial - only needed for real hardware
    with serial.Serial(port, baud, timeout=1) as link:
        time.sleep(2)  # the Arduino resets when the port opens
        while True:
            raw = link.readline().decode(errors="ignore")
            reading = parse_line(raw)
            if reading:
                yield reading, link


def run(readings, send_command=None, log_path=None, delay=0.0):
    """Main loop shared by simulation and hardware modes."""
    flex_window, vib_window = SlidingWindow(), SlidingWindow()
    calibration = []
    flex_base = vib_base = None
    last_status = None
    log_file = writer = None

    if log_path:
        log_file = open(log_path, "w", newline="")
        writer = csv.writer(log_file)
        writer.writerow(["time_s", "flex", "vib", "risk", "status"])

    print(f"Calibrating for {CALIBRATION_SAMPLES} readings - keep the structure at rest...")
    start = time.time()
    try:
        for item in readings:
            flex, vib = item
            flex_avg = flex_window.add(flex)
            vib_avg = vib_window.add(vib)

            if flex_base is None:
                calibration.append((flex, vib))
                if len(calibration) == CALIBRATION_SAMPLES:
                    flex_base = sum(c[0] for c in calibration) / CALIBRATION_SAMPLES
                    vib_base = sum(c[1] for c in calibration) / CALIBRATION_SAMPLES
                    print(f"Baseline: FLEX={flex_base:.0f}  VIB={vib_base:.0f}\n")
                    print(f"{'Time(s)':>8} {'FLEX':>6} {'VIB':>5} {'Risk':>7}  Status")
                continue

            risk = compute_risk(flex_avg, vib_avg, flex_base, vib_base)
            status = classify(risk)
            elapsed = time.time() - start
            print(f"{elapsed:8.1f} {flex_avg:6.0f} {vib_avg:5.0f} {risk * 100:6.1f}%  {status}")
            if writer:
                writer.writerow([f"{elapsed:.1f}", flex, vib, f"{risk:.3f}", status])

            if status != last_status and send_command:
                send_command(STATUS_COMMAND[status])
            last_status = status
            if delay:
                time.sleep(delay)
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        if log_file:
            log_file.close()


def main():
    parser = argparse.ArgumentParser(description="Structural risk monitor")
    parser.add_argument("--port", help="serial port of the Arduino, e.g. COM3 or /dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=9600)
    parser.add_argument("--simulate", action="store_true", help="use simulated sensor data")
    parser.add_argument("--steps", type=int, default=120, help="simulation length")
    parser.add_argument("--fast", action="store_true", help="simulate without real-time delay")
    parser.add_argument("--log", help="write a CSV log to this file")
    args = parser.parse_args()

    if args.simulate:
        sim = simulated_readings(args.steps)
        run(sim, log_path=args.log, delay=0.0 if args.fast else 0.1)
    elif args.port:
        link_holder = {}

        def stream():
            for reading, link in serial_readings(args.port, args.baud):
                link_holder["link"] = link
                yield reading

        run(stream(), send_command=lambda c: link_holder["link"].write(c.encode()),
            log_path=args.log)
    else:
        parser.error("give --port <serial port> or use --simulate")


if __name__ == "__main__":
    main()
