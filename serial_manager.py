import serial
import threading
import time

PORT = '/dev/ttyACM0'
BAUDRATE = 9600

ser = None
is_running = False
latest_lines = []
threshold = 10

def init_serial():
    global ser
    try:
        ser = serial.Serial(PORT, BAUDRATE, timeout=1)
        time.sleep(2)
        print("Sériové spojenie nadviazané.")
        return True
    except serial.SerialException as e:
        print("Chyba pri otváraní portu:", e)
        return False

def set_threshold(value_cm):
    global threshold
    threshold = value_cm
    if ser:
        ser.write(f'T{value_cm}\n'.encode())
        print(f"Odoslaný nový threshold: {value_cm} cm")

def start_monitoring():
    global is_running
    if ser and not is_running:
        is_running = True
        threading.Thread(target=read_serial_data, daemon=True).start()
        ser.write(b'A')
        print("Spustené monitorovanie...")

def read_serial_data():
    global is_running
    while is_running:
        if ser.in_waiting:
            try:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print("Arduino:", line)
                    latest_lines.append(line)
                    if len(latest_lines) > 10:
                        latest_lines.pop(0)
            except Exception as e:
                print("Chyba pri čítaní:", e)
        time.sleep(0.1)

def get_latest_data():
    return latest_lines.copy()
