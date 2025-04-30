from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
import serial_manager

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

serial_opened = False

@app.route('/')
def index():
    return render_template('index.html', opened=serial_opened)

@app.route('/graph')
def graph():
    return render_template('graph.html')

@app.route('/gauge')
def gauge():
    return render_template('gauge.html')

@app.route('/open', methods=['POST'])
def open_serial():
    global serial_opened
    if not serial_opened:
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

@socketio.on('connect')
def handle_connect():
    emit('initial', {'data': serial_manager.get_latest_data()})

@socketio.on('request_data')
def send_latest_data():
    emit('serial_data', {'data': serial_manager.get_latest_data()})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
