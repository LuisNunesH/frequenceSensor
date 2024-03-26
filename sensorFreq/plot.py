import matplotlib.pyplot as plt

def plot_heart_rate(timestamps, heart_rates):
    plt.plot(timestamps, heart_rates)
    plt.xlabel('Timestamp')
    plt.ylabel('Heart Rate')
    plt.title('Heart Rate Variation')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()