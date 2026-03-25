import pandas as pd
import numpy as np
import secrets

freq_array = np.arange(400, 500, 10)
power_array = np.arange(15, 45, 1)

def get_power_err():
    options = [-2.5, -2.0, -1.5, -1.0, -.5, 0, 0.5, 1, 1.5, 2.0, 2.5]
    val_to_return = secrets.choice(options)
    return val_to_return

cal_dict = {}
freq_list = []
for power in power_array:

    for freq in freq_array:
        print(f'Power: {power}, Freq: {freq}, Power Err: {get_power_err()}')



data = {400: [3, 2, 1, 0], 500: ['a', 'b', 'c', 'd']}

list_of_powers = []
list_of_freqs = []


df = pd.DataFrame.from_dict(data, orient='index',
                       columns=['A', 'B', 'C', 'D'])

print(df)