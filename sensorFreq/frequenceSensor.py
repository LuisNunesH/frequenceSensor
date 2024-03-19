from flask import Flask, request, jsonify
import random
import time
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import DB_TYPE, MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE
import matplotlib.pyplot as plt

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

def generate_heart_rate_data(session, min_value, max_value, lim):
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=lim)
    while datetime.now() < end_time:
        try:
            timestamp = datetime.now()
            animal = "Capybara"
            sensor_id = 4
            heart_rate = random.randint(min_value, max_value)
            print(f"Timestamp: {timestamp}, Heart rate: {heart_rate}")
            insert_data(session, timestamp, heart_rate, animal, sensor_id)
            yield timestamp, heart_rate
            interval = 1
            time.sleep(interval)
        except Exception as e:
            print("Erro durante a geração de dados:", e)

def simulate_running(session, min_value, max_value, run_duration):
    start_time = datetime.now()
    end_time = start_time + timedelta(seconds=run_duration)

    initial_hr = min_value
    final_hr = max_value

    timestamps = []
    heart_rates = []

    while datetime.now() < end_time:
        try:
            timestamp = datetime.now()
            progress = (timestamp - start_time).total_seconds() / run_duration
            heart_rate = int(initial_hr + progress * (final_hr - initial_hr))
            print(f"Timestamp: {timestamp}, Heart rate: {heart_rate}")
            insert_data(session, timestamp, heart_rate, "Capybara", 4)
            timestamps.append(timestamp)
            heart_rates.append(heart_rate)
            time.sleep(1)
        except Exception as e:
            print("Erro durante a simulação de corrida:", e)
    plot_heart_rate(timestamps, heart_rates)

def plot_heart_rate(timestamps, heart_rates):
    plt.plot(timestamps, heart_rates)
    plt.xlabel('Timestamp')
    plt.ylabel('Heart Rate')
    plt.title('Heart Rate Variation')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

@app.route('/<int:min_value>/<int:max_value>/<int:lim>')
def start_data_generation(min_value, max_value, lim):
    connection = connect_to_database(DB_TYPE)
    if connection:
        generator = generate_heart_rate_data(connection, min_value, max_value, lim)
        try:
            while True:
                next(generator)
        except StopIteration:
            return jsonify({"message": "Data generation completed."}), 200
    else:
        return jsonify({"error": "Could not connect to the database. Please check the configuration."}), 500
    
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