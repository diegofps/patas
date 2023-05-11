#!/usr/bin/env python3

from random import gauss
import sys

# Read variable parameters

hidden_neurons      = int(sys.argv[1])
activation_function = sys.argv[2]

# Configuration that defines the model performance as a function of the input parameters
# model_name: (optimal_number_of_neurons, deviation, percent_drop_from_train_to_test_acc)

optimal_model_params = {
    "relu"      : (25 , 10, 0.98),
    "leaky_relu": (20 ,  5, 0.95),
    "sigmoid"   : (30 , 20, 0.97),
    "tanh"      : (13 , 20, 0.94),
}

p = optimal_model_params[activation_function]

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

train_accuracy = 1 / (1 + abs(hidden_neurons - gauss(p[0], 0.5)) / gauss(p[1], 1.0))
test_accuracy  = train_accuracy * gauss(p[2], 0.01)

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
