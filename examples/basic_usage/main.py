#!/usr/bin/env python3

from random import gauss
import sys

# Read variable parameters

hidden_neurons      = int(sys.argv[1]) if len(sys.argv) > 1 else 10
activation_function = sys.argv[2]      if len(sys.argv) > 2 else 'relu'
preprocessing_alg   = sys.argv[3]      if len(sys.argv) > 3 else 'fast'

# Configurations that defines the model performance as a function of the input parameters

# (optimal_number_of_neurons, deviation, percent_drop_from_train_to_test_acc)
activation_params = {
    "relu"      : (25 , 10, 0.98),
    "leaky_relu": (20 ,  5, 0.95),
    "sigmoid"   : (30 , 20, 0.97),
    "tanh"      : (13 , 20, 0.94),
}

# The closer to 1, the more representative the data
preprocessing_params = {
    "fast": 0.79,
    "medium": 0.87,
    "intense": 0.94
}

act = activation_params[activation_function]
pre = preprocessing_params[preprocessing_alg]


# Pretend we are loading and preparing the data

print("Loading dataset...")
print("Cleaning the data...")

# Simulate that we are training during multiple epochs

print("Training model...")

pivot = max(1, gauss(10, 4))
speed = max(1, gauss(3.14, 0.2))

for i in range(100):
    loss = pivot / gauss(i+1, 0.1) * speed
    print(f"Training epoch {i+1}, loss = {loss}")

# Simulate that we are evaluating the model

print("Evaluating model...")

# Generate fake train and test accuracies

train_accuracy = 1 / (1 + abs(hidden_neurons - gauss(act[0], 0.5)) / gauss(act[1], 1.0)) * gauss(pre, 0.1)
test_accuracy  = train_accuracy * gauss(act[2], 0.01)

# Generate fake train and test times

train_time = max(10, gauss(175, 20.0))
test_time  = max(1, gauss(10, 4.0))

# Consolidate results

print("Results:")
print(f"    Time to train (ms): {train_time:.3f}"    )
print(f"    Time to test (ms):  {test_time:.3f}"     )
print(f"    Train accuracy:     {train_accuracy:.3f}")
print(f"    Test accuracy:      {test_accuracy:.3f}" )
print(f"    Final Loss:         {loss:.3f}"          )
