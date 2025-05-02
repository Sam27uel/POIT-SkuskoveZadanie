import serial
import threading
import time
import MySQLdb
from datetime import datetime

PORT = '/dev/ttyACM0'
BAUDRATE = 9600

ser = None
is_running = False
latest_lines = []
threshold = 10

# DB logovanie - funkcie poskytnuté z app.py
recording_active_getter = None
record_id_getter = None

def set_recording_getters(active_fn, id_fn):
    global recording_active_getter, record_id_getter
    recording_active_getter = active_fn
    record_id_getter = id_fn

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

                    # 🔴 Ukladanie do DB ak je aktívne
                    if recording_active_getter and recording_active_getter():
                        record_id = record_id_getter()
                        save_line_to_db(line, record_id)

            except Exception as e:
                print("Chyba pri čítaní:", e)
        time.sleep(0.1)

def save_line_to_db(line, record_id):
    try:
        db = MySQLdb.connect(host='localhost', user='root', passwd='admin', db='poit')
        cursor = db.cursor()
        now = datetime.now()

        if "Vzdialenosť" in line:
            # extrahuj číselnú hodnotu
            import re
            match = re.search(r'Vzdialenosť:\s*([\d.]+)', line)
            if match:
                value = float(match.group(1))
                cursor.execute("INSERT INTO hodnoty (zaznam_id, timestamp, value) VALUES (%s, %s, %s)",
                               (record_id, now, value))
        else:
            # iný riadok – ulož ako príkaz
            cursor.execute("INSERT INTO prikazy (zaznam_id, timestamp, command) VALUES (%s, %s, %s)",
                           (record_id, now, line))

        db.commit()
        cursor.close()
        db.close()
    except Exception as e:
        print(f"Chyba pri ukladaní do DB: {e}")

def get_latest_data():
    return {
        "data": latest_lines[-15:],
        "running": is_running
    }
