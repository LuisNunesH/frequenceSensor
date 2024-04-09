from flask import Flask, request, jsonify
import random
import time
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import SQLAlchemyError
from config import DB_TYPE
from plot import plot_heart_rate
import numpy as np
from config import MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)

Base = declarative_base()

class HeartRateData(Base):
    __tablename__ = 'HeartRateData'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime)
    heart_rate = Column(Integer)
    animal = Column(String)
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
    offset = 2  # Offset máximo permitido
    inicio = time.time()
    while time.time() - inicio < lim:
        valor = random.randint(av - offset, av + offset)
        valor = max(av - offset, min(valor, av + offset))  # Garantir que o valor está dentro do intervalo permitido
        print(valor)
        yield valor
        time.sleep(1)  # Aguardar 1 segundo antes de gerar o próximo valor

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
        try:
            timestamp = datetime.now()
            timestamp = timestamp.replace(microsecond=0)
            progress = (timestamp - start_time).total_seconds()
            
            # Adiciona um ruído aleatório aos batimentos cardíacos
            noise = random.uniform(-5, 5)
            
            # Usa a função sigmoidal ajustada com um valor inicial diferente de zero
            heart_rate = int(min_value + (max_value - min_value) * sigmoid(progress, midpoint, slope)) + noise
            
            # Aplica o fator de suavização adequado dependendo do estágio da simulação
            if progress < midpoint:
                smoothed_heart_rate = initial_smoothing_factor * heart_rate + (1 - initial_smoothing_factor) * heart_rate
            else:
                smoothed_heart_rate = stable_smoothing_factor * heart_rate + (1 - stable_smoothing_factor) * heart_rate
            
            print(f"Timestamp: {timestamp}, Heart rate: {smoothed_heart_rate}")
            insert_data(session, timestamp, smoothed_heart_rate, "Capybara", 4)
            timestamps.append(timestamp)
            heart_rates.append(smoothed_heart_rate)
            time.sleep(1)
        except Exception as e:
            print("Erro durante a simulação de corrida:", e)

    plot_heart_rate(timestamps, heart_rates)

@app.route('/<int:lim>/<int:av>')
def start_data_generation(lim, av):
    heart_rate_generator = average_heart_rate(lim, av)
    return jsonify({'heart_rate': list(heart_rate_generator)})
    
@app.route('/run/<int:min_value>/<int:max_value>/<int:run_duration>')
def start_running_simulation(min_value, max_value, run_duration):
    connection = connect_to_database(DB_TYPE)
    if connection:
        simulate_running(connection, min_value, max_value, run_duration)
        return jsonify({"message": "Running simulation completed."}), 200
    else:
        return jsonify({"error": "Could not connect to the database. Please check the configuration."}), 500
    
if __name__ == '__main__':
    app.run(debug=True)