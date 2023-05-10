#!/usr/bin/env python3

import random
import sys

# Read variable parameters
hidden_neurons      = sys.argv[1]
activation_function = sys.argv[2]

# Pretend we have done something for a long time
print("Loading dataset...")
print("Applying transformations...")
print("Training model...")
print("Evaluating model...")

w = abs(int(hidden_neurons) + len(activation_function)) / 10
train_accuracy = 0.9 + 0.1 / (1+  w) + random.gauss(0,0.05)
test_accuracy  = 0.9 + 0.1 / (1+2*w) + random.gauss(0,0.05)

# Print results
print("Results:")
print(f"    Train accuracy: {train_accuracy:.3f}")
print(f"    Test accuracy:  {test_accuracy:.3f}")
