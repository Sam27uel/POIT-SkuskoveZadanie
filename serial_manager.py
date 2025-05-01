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
        time.sleep(2.0)
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        for _ in range(3):
            ser.write(b'P\n')
            time.sleep(0.2)
        print("Príkaz 'P' odoslaný Arduinu po OPEN.")
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

def stop_monitoring():
    global is_running
    is_running = False
    if ser:
        ser.write(b'S')
        print("Monitorovanie zastavené a príkaz 'S' odoslaný Arduinu.")

def close_serial():
    global is_running, ser
    is_running = False
    if ser and ser.is_open:
        try:
            ser.write(b'X')
            time.sleep(0.2)
            print("Príkaz X odoslaný Arduinu.")
        except Exception as e:
            print("Chyba pri odosielaní príkazu X:", e)
        return True
    return False

def read_serial_data():
    global is_running
    while is_running:
        if ser.in_waiting:
            try:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    print("Arduino:", line)
                    latest_lines.append(line)
                    if len(latest_lines) > 1200:
                        latest_lines.pop(0)
            except Exception as e:
                print("Chyba pri čítaní:", e)
        time.sleep(0.1)

def get_latest_data():
    return {
        "data": latest_lines[-15:],  # zoznam posledných výpisov
        "running": is_running         # stav monitorovania
    }