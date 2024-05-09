import json
from flask import Flask, jsonify
import random
import time
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, create_engine, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from config import DB_TYPE
from plot import plot_heart_rate
import numpy as np
from config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
from sqlalchemy.orm import sessionmaker
import boto3
from aws_integrations import *
from azure.iot.device import IoTHubDeviceClient, Message

RECEIVED_MESSAGES = 0

def iothub_client_init():
    CONNECTION_STRING = "HostName=iot-hub-heart-rate-electric-pulse.azure-devices.net;DeviceId=sensor-heart-rate-electric-pulse;SharedAccessKey=I770fE1rCdRMnwpC1vPaWqeNuW2VPNbYDAIoTNnLIf0="
    client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
    return client

def handle_message(message):
    global RECEIVED_MESSAGES
    RECEIVED_MESSAGES += 1
    print("Message received:")
    for property in vars(message).items():
        print("    {}".format(property))
    print("Total calls received: {}".format(RECEIVED_MESSAGES))

app = Flask(__name__)

Base = declarative_base()

class HeartRateData(Base):
    __tablename__ = 'HeartRateData'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    heart_rate = Column(Integer)
    animal = Column(String)
    sensor_id = Column(Integer)

class ElectricalPulseData(Base):
   __tablename__ = 'ElectricalPulseData'

   id = Column(Integer, primary_key=True)
   timestamp = Column(DateTime)
   peak_voltage = Column(Float)
   pulse_width = Column(Integer)
   animal = Column(String(50))
   sensor_id = Column(Integer)

def connect_to_database(database_type):
    try:
        if database_type == "mysql":
            engine = create_engine(f'mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DATABASE}')
        elif database_type == "azure":
            engine = create_engine(f'mssql+pyodbc://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DATABASE}?driver=ODBC+Driver+18+for+SQL+Server')
        
        Session = sessionmaker(bind=engine)
        Base.metadata.create_all(engine)
        return Session()
    except Exception as e:
        print("Erro ao conectar ao banco de dados:", e)
        return None

def insert_data(session, timestamp, heart_rate, animal, sensor_id):
    try:
        data = HeartRateData(timestamp=timestamp, heart_rate=heart_rate, animal=animal, sensor_id=sensor_id)
        session.add(data)
        session.commit()
    except SQLAlchemyError as e:
        print("Erro ao inserir dados no banco de dados:", e)
        session.rollback()

def average_heart_rate(lim, av):
    client = iothub_client_init()
    offset = 2  # Offset máximo permitido
    inicio = time.time()

    while time.time() - inicio < lim:
        current_timestamp = datetime.now().replace(microsecond=0)
        timestamp_str = current_timestamp.strftime('%Y-%m-%d %H:%M:%S')
        heart_rate = random.randint(av - offset, av + offset)
        heart_rate = max(av - offset, min(heart_rate, av + offset))
        json_value = {
            'publisher': 'luisfeitosa-127_1_0_0',
            'tag': 'electrical-pulse_heart-rate',
            'type': 'critico',
            'data': {
                'sensor_id': 21,
                'heart-rate': heart_rate
            },
            'timestamp': timestamp_str
        }
        yield heart_rate
        try:
            send_json_to_s3(json_value, f"heart-rate-sensor_{current_timestamp}.json")
            print(json_value)
            json_str = json.dumps(json_value)
            mensagem = Message(json_str, content_encoding='utf-8', content_type='application/json')
            client.send_message(mensagem)
        except Exception as e:
            print("Ocorreu um erro:", e)
        time.sleep(10)
    client.disconnect()

def sigmoid(x, midpoint, slope):
    return 1 / (1 + np.exp(-slope * (x - midpoint)))

def simulate_running(session, min_value, max_value, run_duration):
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=run_duration)

    midpoint = run_duration / 2
    slope = 0.1
    timestamps = []
    heart_rates = []

    # Adiciona um ruído inicial aleatório
    initial_offset = random.uniform(0, 10)

    # Define o fator de suavização para diferentes estágios da simulação
    initial_smoothing_factor = 0.1  # Para suavizar as variações iniciais
    stable_smoothing_factor = 0.05  # Para manter a estabilidade após a fase inicial

    while datetime.now() < end_time:
        timestamp = datetime.now().replace(microsecond=0)
        try:
            timestamp = datetime.now()
            timestamp = timestamp.replace(microsecond=0)
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
            progress = (timestamp - start_time).total_seconds()
            
            # Adiciona um ruído aleatório aos batimentos cardíacos
            noise = random.uniform(-5, 5)
            
            # Usa a função sigmoidal ajustada com um valor inicial diferente de zero
            heart_rate = int(min_value + (max_value - min_value) * sigmoid(progress, midpoint, slope)) + noise
            
            # Aplica o fator de suavização adequado dependendo do estágio da simulação
            if progress < midpoint:
                smoothed_heart_rate = int(initial_smoothing_factor * heart_rate + (1 - initial_smoothing_factor) * heart_rate)
            else:
                smoothed_heart_rate = int(stable_smoothing_factor * heart_rate + (1 - stable_smoothing_factor) * heart_rate)
            
            json_value = {
                'publisher': 'luisfeitosa-127_1_0_0',
                'tag': 'electrical-pulse_heart-rate',
                'type': 'critico',
                'data': {
                    'sensor_id': 21,
                    'heart-rate': smoothed_heart_rate
                },
                'timestamp': timestamp_str
            }

            insert_data(session, timestamp, smoothed_heart_rate, "Capybara", 4)
            # send_json_to_s3(json_value, f"heart-rate-run_{timestamp_str}.json")
            print(json_value)
            timestamps.append(timestamp)
            heart_rates.append(smoothed_heart_rate)
            time.sleep(1)
        except Exception as e:
            print("Erro durante a simulação de corrida:", e)

    plot_heart_rate(timestamps, heart_rates)

def simulate_electrical_pulse(min_voltage, max_voltage, min_pulse_width, max_pulse_width, run_duration):
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=run_duration)

    timestamps = []
    peak_voltages = []
    pulse_widths = []

    # Random variations within defined ranges
    while datetime.now() < end_time:
        try:
            timestamp = datetime.now().replace(microsecond=0)

            peak_voltage = random.uniform(min_voltage, max_voltage)
            pulse_width = random.randint(min_pulse_width, max_pulse_width)

            # Convertendo o objeto datetime em uma string formatada
            timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')

            json_value = {
                'Peak Voltage': f'{peak_voltage:.2f}V',
                'Pulse Width': f'{pulse_width}ms',
                'Timestamp': timestamp_str
            }

            json_str = json.dumps(json_value)

            # send_json_to_s3(json_str, f"electrical_pulse_{timestamp_str}.json")
            print(json_str)

            timestamps.append(timestamp)
            peak_voltages.append(peak_voltage)
            pulse_widths.append(pulse_width)
            time.sleep(1)
        except Exception as e:
            print("Erro durante a simulação de pulso elétrico:", e)

@app.route('/<int:lim>/<int:av>')
def start_data_generation(lim, av):
    heart_rate_generator = average_heart_rate(lim, av)
    return jsonify({'message': list(heart_rate_generator)})
    
@app.route('/run/<int:min_value>/<int:max_value>/<int:run_duration>')
def start_running_simulation(min_value, max_value, run_duration):
    connection = connect_to_database(DB_TYPE)
    if connection:
        simulate_running(connection, min_value, max_value, run_duration)
        return jsonify({"message": "Running simulation completed."}), 200
    else:
        return jsonify({"error": "Could not connect to the database. Please check the configuration."}), 500
    
@app.route('/simulate_pulse/<float:min_voltage>/<float:max_voltage>/<int:min_pulse_width>/<int:max_pulse_width>/<int:run_duration>')
def start_simulate_electrical_pulse(min_voltage, max_voltage, min_pulse_width, max_pulse_width, run_duration):
    connection = True
    if connection:
        simulate_electrical_pulse(min_voltage, max_voltage, min_pulse_width, max_pulse_width, run_duration)
        return jsonify({"message": "Running simulation completed."}), 200
    else:
        return jsonify({"error": "Could not connect to the database. Please check the configuration."}), 500
    
if __name__ == '__main__':
    app.run(debug=True)