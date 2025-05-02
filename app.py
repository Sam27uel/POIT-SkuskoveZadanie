from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import serial_manager
import configparser
import MySQLdb
from datetime import datetime

# --- Načítanie konfigurácie z config.cfg ---
config = configparser.ConfigParser()
config.read('config.cfg')

myhost = config.get('mysqlDB', 'host')
myuser = config.get('mysqlDB', 'user')
mypasswd = config.get('mysqlDB', 'passwd')
mydb = config.get('mysqlDB', 'db')

# --- Flask a SocketIO ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

# --- Stavové premenné ---
serial_opened = False
recording_active = False
current_record_id = None

# --- ROUTES ---
@app.route('/')
def index():
    return render_template('index.html', opened=serial_opened)

@app.route('/graph')
def graph():
    return render_template('graph.html')

@app.route('/gauge')
def gauge():
    return render_template('gauge.html')

@app.route('/database')
def database_page():
    return render_template('database.html')

@app.route('/open', methods=['POST'])
def open_serial():
    global serial_opened
    serial_opened = serial_manager.init_serial()
    return jsonify({"success": serial_opened})

@app.route('/set_threshold', methods=['POST'])
def set_threshold():
    value = int(request.form.get('threshold', 30))
    serial_manager.set_threshold(value)
    return jsonify({"status": "OK", "threshold": value})

@app.route('/start', methods=['POST'])
def start_monitoring():
    serial_manager.start_monitoring()
    return jsonify({"status": "started"})

@app.route('/stop', methods=['POST'])
def stop_monitoring():
    serial_manager.stop_monitoring()
    return jsonify({"status": "stopped"})

@app.route('/close', methods=['POST'])
def close_serial():
    success = serial_manager.close_serial()
    return jsonify({"status": "closed", "success": success})

@app.route('/toggle_db_logging', methods=['POST'])
def toggle_db_logging():
    global recording_active, current_record_id
    if not recording_active:
        try:
            db = MySQLdb.connect(host=myhost, user=myuser, passwd=mypasswd, db=mydb)
            cursor = db.cursor()
            cursor.execute("INSERT INTO zaznamy (start_time) VALUES (%s)", (datetime.now(),))
            db.commit()
            current_record_id = cursor.lastrowid
            cursor.close()
            db.close()
            recording_active = True
            print(f"🟢 Záznam ID {current_record_id} spustený.")
        except Exception as e:
            print(f"Chyba pri spúšťaní záznamu: {e}")
            return jsonify({"recording": False, "error": str(e)}), 500
    else:
        try:
            db = MySQLdb.connect(host=myhost, user=myuser, passwd=mypasswd, db=mydb)
            cursor = db.cursor()
            cursor.execute("UPDATE zaznamy SET end_time = %s WHERE id = %s", (datetime.now(), current_record_id))
            db.commit()
            cursor.close()
            db.close()
            print(f"🔴 Záznam ID {current_record_id} ukončený.")
            recording_active = False
            current_record_id = None
        except Exception as e:
            print(f"Chyba pri ukončovaní záznamu: {e}")
            return jsonify({"recording": True, "error": str(e)}), 500

    return jsonify({"recording": recording_active})

@app.route('/get_records')
def get_records():
    try:
        db = MySQLdb.connect(host=myhost, user=myuser, passwd=mypasswd, db=mydb)
        cursor = db.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT id, start_time, end_time FROM zaznamy ORDER BY id DESC")
        records = []
        for row in cursor.fetchall():
            records.append({
                "id": row["id"],
                "start": row["start_time"].strftime("%Y-%m-%d %H:%M:%S"),
                "end": row["end_time"].strftime("%Y-%m-%d %H:%M:%S") if row["end_time"] else None
            })
        cursor.close()
        db.close()
        return jsonify(records)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_record_data/<int:zaznam_id>')
def get_record_data(zaznam_id):
    try:
        db = MySQLdb.connect(host=myhost, user=myuser, passwd=mypasswd, db=mydb)
        cursor = db.cursor(MySQLdb.cursors.DictCursor)

        cursor.execute("SELECT timestamp, value FROM hodnoty WHERE zaznam_id = %s ORDER BY timestamp ASC", (zaznam_id,))
        values = [{"timestamp": r["timestamp"].strftime("%Y-%m-%d %H:%M:%S"), "value": r["value"]} for r in cursor.fetchall()]

        cursor.execute("SELECT timestamp, command FROM prikazy WHERE zaznam_id = %s ORDER BY timestamp ASC", (zaznam_id,))
        commands = [{"timestamp": r["timestamp"].strftime("%Y-%m-%d %H:%M:%S"), "command": r["command"]} for r in cursor.fetchall()]

        cursor.close()
        db.close()

        return jsonify({"values": values, "commands": commands})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Socket.IO udalosti ---
@socketio.on('connect')
def handle_connect():
    emit('initial', {'data': serial_manager.get_latest_data()})

@socketio.on('request_data')
def send_latest_data():
    emit('serial_data', serial_manager.get_latest_data())

# --- Getter funkcie pre serial_manager.py ---
def is_logging_active():
    return recording_active

def get_current_record_id():
    return current_record_id

serial_manager.set_recording_getters(is_logging_active, get_current_record_id)

# --- Štart servera ---
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
