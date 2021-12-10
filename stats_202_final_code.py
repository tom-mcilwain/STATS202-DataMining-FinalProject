# -*- coding: utf-8 -*-
"""STATS_202_Final_Project.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/15YiH3Akhon6btT3iIyY9uUeGVqzlgxvP
"""

# Imports
from google.colab import files
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tqdm import tqdm
import warnings
import tensorflow as tf
from keras.preprocessing.sequence import TimeseriesGenerator
from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM
import keras

# Defining helpful methods
def time_to_idx(time, day):
  day_idx = 5040
  idx = int(int(time[6:]) / 5) + (12 * int(time[3:5])) + (12 * 60 * (int(time[0:2]) - 6)) + (day_idx * day)
  return int(idx)

def next_time(prev_time):
  next_time = prev_time.copy()
  if prev_time[3] < 55:
    next_time[3] += 5
  elif prev_time[3] == 55:
    next_time[3] = 0
    next_time[2] += 1
  if next_time[2] == 60:
    next_time[2] = 0
    next_time[1] += 1
  if next_time[1] == 13:
    next_time[1] = 6
    next_time[0] += 1
  return next_time

def time_to_str(time):
  return f'{time[0]:01}-{time[1]:02}:{time[2]:02}:{time[3]:02}'

# Loading data
train_data = pd.read_csv('/content/drive/My Drive/train_data.csv')
train_data.head()

# Preprocessing
columns = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']

data = pd.DataFrame(np.zeros((time_to_idx('06:00:00', 87), len(columns))), columns=columns)

for i in tqdm(range(train_data.shape[0])):
  row = train_data.iloc[i,:]
  t = row['time']
  d = row['day']
  if t == t and d == d:
    new_idx = time_to_idx(t, d)
    data[row['symbol']][new_idx] = row['open']
data.to_csv('/content/drive/My Drive/full_data.csv')

# Loading in newly formatted data
data = pd.read_csv('/content/drive/My Drive/full_data.csv', index_col=0)

# Changing missing data to random walk
warnings.filterwarnings("ignore")
means = data.mean(axis=0)
if np.where(data.iloc[0,:] == 0)[0] != []:
  loc = np.where(data.iloc[0,:] == 0)
  data.iloc[0, loc[0]] = means[loc[0]]
for i in tqdm(range(data.shape[0])):
  loc = np.where(data.iloc[i,:] == 0)
  move = np.random.choice([-0.001, 0.001], 1)
  data.iloc[i,loc[0]] = data.iloc[i-1,loc[0]] + move
data.head()

# Visualizing opening prices for each ticker over time
data.plot()
plt.title('Security Prices over Time')
plt.xlabel('Observation')
plt.ylabel('Price')
print()

# Adding day, hour, minute, and second features to the dataset
time = [0, 6, 0, 0]
times = pd.DataFrame(np.zeros(shape=(data.shape[0], 4)), columns=['day', 'hour', 'minute', 'second'])
for i in tqdm(range(data.shape[0])):
  times.iloc[i,:] = time
  time = next_time(time)
  
data['day'] = times.iloc[:,0]
data['hour'] = times.iloc[:,1]
data['minute'] = times.iloc[:,2]
data['second'] = times.iloc[:,3]

data.head()

"""### Train Test Split"""

# Loading final data
data = pd.read_csv('/content/drive/My Drive/data.csv', index_col=0)

# Train-test split
train_size = 0.8
train_idx = int(train_size * data.shape[0])
targets = data.shift(1, axis=0).iloc[:,:-4]

train_data = tf.convert_to_tensor(np.asarray(data.iloc[:train_idx,:]).astype('float32'))[1:]
train_targets = tf.convert_to_tensor(np.asarray(targets.iloc[:train_idx,:]).astype('float32'))[1:]

test_data = tf.convert_to_tensor(np.asarray(data.iloc[train_idx:,:]).astype('float32'))[1:]
test_targets = tf.convert_to_tensor(np.asarray(targets.iloc[train_idx:,:]).astype('float32'))[1:]

"""# **LSTM**"""

# Generating dataset with lag variables

n_input = 12 # number of lag variables
generator = TimeseriesGenerator(train_data, train_targets, n_input, batch_size=1)

# Implementing the LSTM
model = Sequential()
model.add(LSTM(50, activation='relu', input_shape=(None, 14)))
model.add(Dense(10))
model.compile(optimizer='adam', loss='mse')

# Fitting and saving the model
model.fit_generator(generator, epochs=1)
model.save('/content/drive/My Drive/lstm_model_2')

"""# Loading model"""

# Loading model
model = keras.models.load_model('/content/drive/My Drive/lstm_model_2')

# Getting predictions for validation data
def predict(num_predictions, pred_list):
  time = [0, 6, 0, 0]  
  times = np.zeros(shape=(num_predictions,4))
  for i in range(num_predictions):
      times[i,:] = time
      time = next_time(time)
  times = tf.expand_dims(tf.convert_to_tensor(times.astype('float32')), 1)
  time = times[0,:]
  for i in tqdm(range(num_predictions)):
    X = pred_list[-n_input:,:]
    X = tf.expand_dims(X, 0)
    pred = model.predict(X)
    pred = tf.concat([pred, time], 1)
    pred_list = tf.concat([pred_list, pred], 0)
    if i+1 < num_predictions:
      time = times[i+1,:]
  pred_list = pred_list[n_input-1:]
  return pred_list

n_input = 12
num_predictions = test_data.shape[0]
pred_list = train_data[-n_input:,:]
pred_list = predict(num_predictions, pred_list)
np.save('/content/drive/My Drive/val_predictions', pred_list)

# Visualizing the predictions
pred_list = np.load('/content/drive/My Drive/val_predictions.npy')
colors = ['c', 'orange', 'k', 'r', 'g', 'y', 'b', 'purple', 'm', 'lightblue']
predictions = np.asarray(pred_list)[1:,:-4]
time = range(predictions.shape[0])
true = np.asarray(test_data)[:,:-4]

day = 5040

# Plotting all
plt.subplots(3,1, figsize=(10,16))
plt.subplot(3,1,1)
plt.title('Validation Data vs. Predictions')
plt.xlabel('Day')
plt.ylabel('Price')
time = np.arange(0, (1+time[-1])/day, 1/day)
for i in range(10):
  plt.plot(time, predictions[:,i], color=colors[i])
  plt.plot(time, true[:,i], color=colors[i])

# Plotting a week
symbol = 4
plt.subplot(3,1,2)
plt.title('One Week of Predictions')
plt.xlabel('Day')
plt.ylabel('Price')
plt.plot(time[:day*5], predictions[day*2:day*7,symbol], colors[2])
plt.plot(time[:day*5], true[day*2:day*7,symbol], colors[3])

# Plotting a day
plt.subplot(3,1,3)
plt.title('One Day of Predictions')
plt.xlabel('Day')
plt.ylabel('Price')
plt.plot(time[:day], predictions[day*4:day*5,symbol], colors[2])
plt.plot(time[:day], true[day*4:day*5,symbol], colors[3])

print()

# Manual Calculation of Validation MSE
num_days = (1 + pred_list.shape[0])/day
days_p1 = int(np.ceil(num_days/2))
days_p2 = num_days - days_p1

pred = pred_list[1:,:-4]
test = test_targets

# period 1
avg_sums = []
for day_num in range(1,days_p1+1):
  p1_t = test[day*day_num:day*(day_num+1)]
  p1_p = pred[day*day_num:day*(day_num+1)]
  p1_res = np.square(p1_t - p1_p)
  p1_sum = np.sum(np.sum(p1_res))
  p1_avg_sum = p1_sum / day
  avg_sums.append(p1_avg_sum)
p1_mse = np.mean(avg_sums)
print('Period 1 MSE:', np.around(p1_mse, 3))

# period 2
avg_sums = []
for day_num in range(days_p1,int(num_days)+1):
  if day_num == int(num_days):
    p2_t = test[day*day_num:]
    p2_p = pred[day*day_num:]
  else:
    p2_t = test[day*day_num:day*(day_num+1)]
    p2_p = pred[day*day_num:day*(day_num+1)]
  p2_res = np.square(p2_t - p2_p)
  p2_sum = np.sum(np.sum(p1_res))
  p2_avg_sum = p2_sum / day
  avg_sums.append(p2_avg_sum)
p1_mse = np.sum(avg_sums) / days_p2
print('Period 2 MSE:', np.around(p2_mse, 3))

"""# Refitting and predicting"""

# Refitting with validation data
n_input = 12
generator = TimeseriesGenerator(test_data, test_targets, n_input, batch_size=1)
model.fit_generator(generator, epochs=1)
model.save('/content/drive/My Drive/lstm_model_3')

# Generating the predictions for the next 9 days
num_predictions = time_to_idx('06:00:00', 9)
pred_list = test_data[-n_input:]
pred_list = predict(num_predictions, pred_list)
np.save('/content/drive/My Drive/good_predictions', pred_list)

# Saving predictions to file in the proper format for Kaggle submission
symbols = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']
from tqdm import tqdm

predictions = pd.DataFrame(np.zeros(shape=(num_predictions*10, 2)), columns=['id', 'open'])
datetime = [0, 6, 0, 0]
for i in tqdm(range(len(pred_list))):
  pred = pred_list[i]
  string = time_to_str(datetime)
  for j, symbol in enumerate(symbols):
    id = f'{symbol}-{string}'
    predictions.iloc[i*10 + j,:] = np.append(id, pred[j])
  datetime = next_time(datetime)

predictions.to_csv('/content/drive/My Drive/actual_predictions.csv', index=False)