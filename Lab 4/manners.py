"""Sweep a positional servo while a Qwiic proximity sensor detects an object.

Uses the hardware/libraries in Lab 4/windmill_coaster.py. Sleeping the HAT
disables PWM on ALL its channels; it does not disconnect servo supply power.
"""

import time

import pi_servo_hat
import qwiic_proximity


PROXIMITY_THRESHOLD = 100  # Raw reading, NOT centimeters; higher means closer.
SERVO_CH = 0
SERVO_MIN = 20
SERVO_MAX = 100
SERVO_STEP = 2
POLL_SECONDS = 0.02


def main():
    hat = pi_servo_hat.PiServoHat()
    try:
        hat.restart()
        hat.sleep()  # Start with motion disabled.

        sensor = qwiic_proximity.QwiicProximity()
        if not sensor.connected:
            raise RuntimeError("Qwiic proximity sensor not found. Check its cable.")
        if sensor.begin() is False:
            raise RuntimeError("Could not initialize the proximity sensor.")

        angle = 60
        direction = 1
        moving = False
        last_print = 0.0
        print("Ready. Bring an object close to move the servo. Ctrl+C stops.")

        while True:
            proximity = sensor.get_proximity()
            if proximity is None:
                raise RuntimeError("No proximity reading received.")
            nearby = proximity >= PROXIMITY_THRESHOLD

            if nearby:
                angle += SERVO_STEP * direction
                if angle >= SERVO_MAX:
                    angle = SERVO_MAX
                    direction = -1
                elif angle <= SERVO_MIN:
                    angle = SERVO_MIN
                    direction = 1

                hat.move_servo_position(SERVO_CH, angle)
                if not moving:
                    hat.wake()
                moving = True
            elif moving:
                hat.sleep()  # Stop sending pulses; do not return home.
                moving = False

            now = time.monotonic()
            if now - last_print >= 0.5:
                print(f"Proximity: {proximity} | {'MOVING' if moving else 'STOPPED'}")
                last_print = now
            time.sleep(POLL_SECONDS)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        hat.sleep()  # Disable motion on exit, including sensor read errors.


if __name__ == "__main__":
    main()

