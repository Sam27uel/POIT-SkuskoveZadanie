import serial
import threading
import time
import os
import json
import MySQLdb
from datetime import datetime

PORT = '/dev/ttyACM0'
BAUDRATE = 9600

ser = None
is_running = False
latest_lines = []
threshold = 10

recording_active_getter = None
record_id_getter = None

def set_recording_getters(active_fn, id_fn):
    global recording_active_getter, record_id_getter
    recording_active_getter = active_fn
    record_id_getter = id_fn

# ===== JSON FILE LOGGING =====
file_logging = False
current_log_path = None
json_log_data = {
    "threshold": None,
    "values": [],
    "commands": []
}

def generate_next_log_filename(logs_dir="logs"):
    os.makedirs(logs_dir, exist_ok=True)
    existing = [
        fname for fname in os.listdir(logs_dir)
        if fname.startswith("zaznam_") and fname.endswith(".json")
    ]

    ids = []
    for name in existing:
        try:
            parts = name.split("_")
            if len(parts) >= 2 and parts[0] == "zaznam":
                ids.append(int(parts[1]))
        except:
            continue

    next_id = max(ids, default=0) + 1
    now = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"zaznam_{next_id:03d}_{now}.json"
    return os.path.join(logs_dir, filename)

def set_file_logging(active: bool, threshold_value=None):
    global file_logging, current_log_path, json_log_data

    if active:
        current_log_path = generate_next_log_filename()
        json_log_data = {
            "threshold": threshold_value,
            "values": [],
            "commands": []
        }
        _write_json_log()
        file_logging = True
        print(f"📝 Záznam do súboru spustený: {current_log_path}")
    else:
        _write_json_log()
        file_logging = False
        current_log_path = None

def _write_json_log():
    if current_log_path and json_log_data:
        try:
            with open(current_log_path, "w", encoding="utf-8") as f:
                json.dump(json_log_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Chyba pri ukladaní JSON logu: {e}")

def get_logged_files():
    logs = []
    if os.path.exists("logs"):
        for f in os.listdir("logs"):
            if f.endswith(".json"):
                logs.append(f)
    return sorted(logs, reverse=True)

# ===== SERIAL SETUP =====

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

# ===== READ LOOP =====

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

                    # Ukladanie do DB
                    if recording_active_getter and recording_active_getter():
                        record_id = record_id_getter()
                        save_line_to_db(line, record_id)

                    # Ukladanie do súboru
                    if file_logging:
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        if "Vzdialenosť" in line:
                            import re
                            match = re.search(r'Vzdialenosť:\s*([\d.]+)', line)
                            if match:
                                value = float(match.group(1))
                                json_log_data["values"].append({
                                    "timestamp": now_str,
                                    "value": value
                                })
                        else:
                            json_log_data["commands"].append({
                                "timestamp": now_str,
                                "command": line
                            })
                        _write_json_log()

            except Exception as e:
                print("Chyba pri čítaní:", e)
        time.sleep(0.1)

# ===== DB LOGGING =====

def save_line_to_db(line, record_id):
    try:
        db = MySQLdb.connect(host='localhost', user='root', passwd='admin', db='poit')
        cursor = db.cursor()
        now = datetime.now()

        if "Vzdialenosť" in line:
            import re
            match = re.search(r'Vzdialenosť:\s*([\d.]+)', line)
            if match:
                value = float(match.group(1))
                cursor.execute("INSERT INTO hodnoty (zaznam_id, timestamp, value) VALUES (%s, %s, %s)",
                               (record_id, now, value))
        else:
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