# Patas 🐾

Patas is a command line utility designed to execute any program in parallel and collect its output, varying its input parameters and starting the programs automatically. The script may be parallelized on your local machine or in a cluster. The only requirement to run it on a cluster is an SSH connection between the machines. Assuming the programs are located on each worker machine, patas can start and manage the parallel programs with one command. Parsing the outputs is done in a second command. Its name means PArser and TAsk Scheduler.

# When should I use Patas? ⭐

Use this program if you want to evaluate your model against multiple parameters and measure your own performance metrics. It is a quick way to parallelize an experiment over various machines. It is also handy when you don't want to, or can't, change the original program.

# When should I not use Patas? 🚧

Patas is designed to be a simple command line utility. It will not manage and constrain resource usage, like limiting the amount of RAM, cores, or disk used by the process. The only control available is the number of workers in each machine, representing how many processes we want to execute in the given machine. The reason for this is that when we constrain the process with a given amount of resources, like RAM, it's possible that a process will run out of memory, and the entire system has plenty of it available. The workaround is to estimate the number of workers based on how many resources your program needs. If a machine crashes, its ok, you can stop and execute patas again. It will skip completed tasks and continue from where it stopped.

# Basic usage 🐣

Considering a use case that we need to find the optimal configuration for a neural network, variating the number of hidden neurons and the activation function in the hidden layer. The following is a basic mockup script that receives these two input parameters. It pretends it has trained a model and prints relevant information to stdout. We will assume it is saved in the file `$HOME/Sources/patas/examples/sanity/main.py`.

```python
#!/usr/bin/env python3

import sys

# Read input parameters
hidden_neurons      = sys.argv[1]
activation_function = sys.argv[2]

# Pretend we have done something for a long time
print("Loading dataset...")
print("Applying transformations...")
print("Training model...")
print("Evaluating model...")

w = abs(int(hidden_neurons) + len(activation_function)) / 10
train_accuracy = 0.9 + 0.1 / (1+  w)
test_accuracy  = 0.9 + 0.1 / (1+2*w)

# Print relevant results
print("Results:")
print(f"    Train accuracy: {train_accuracy:.3f}")
print(f"    Test accuracy:  {test_accuracy:.3f}")
```

Assuming we want to vary the number of hidden neurons in the range `[10, 20, 30]` and the activation function in `['sigmoid', 'relu']`, we can parallelize the script above and collect its output using `patas exec grid`. For example, executing the following command from `$HOME/Sources/patas/`, patas will create the output folder named `tmp` holding the experiment's outputs.

```shell
patas exec grid \
    --cmd './main.py {hidden_neurons} {activation_function}' \
    --vl hidden_neurons 10 20 30 \
    --vl activation_function sigmoid relu \
    --workdir '$HOME/Sources/patas/examples/sanity' \
    --repeat 2 \
    -o tmp
```

When the experiment is done, we can parse the outputs and collect desired values using `patas parse`.

```shell
patas parse \
    -e 'tmp/quick_experiment/' \
    -p TRAIN_ACC  'Train accuracy: (@float@)' \
    -p TEST_ACC   'Test accuracy:  (@float@)'
```

This will generate the file `$HOME/Sources/patas/tmp/quick_experiment/output.csv`, containing a table with the collected results, input variables and many other variables associated to the experiment. Its data should be similar to those displayed below.

| VAR_activation_function | VAR_hidden_neurons | OUT_TRAIN_ACC | OUT_TEST_ACC | BREAK_ID | TASK_ID | REPEAT_ID | COMBINATION_ID | EXPERIMENT_ID | EXPERIMENT_NAME | DURATION | STARTED_AT | ENDED_AT | MAX_TRIES | TRIES | CLUSTER_ID | CLUSTER_NAME | NODE_ID | NODE_NAME | WORKER_ID | OUTPUT_DIR | WORK_DIR |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| sigmoid | 10 | 0.937 | 0.923 | 0 | 1 | 1 | 0 | 0 | quick_experiment | 0.018904 | 2023-05-09 18:05:18.012184 | 2023-05-09 18:05:18.031088 | 3 | 1 | 0 | quick_cluster | 0 | local_machine | 16 | /home/ubuntu/Sources/patas/tmp/quick_experiment/1 | $HOME/Sources/patas/examples/sanity |
| sigmoid | 20 | 0.927 | 0.916 | 0 | 8 | 2 | 2 | 0 | quick_experiment | 0.025697 | 2023-05-09 18:05:18.008116 | 2023-05-09 18:05:18.033813 | 3 | 1 | 0 | quick_cluster | 0 | local_machine | 9 | /home/ubuntu/Sources/patas/tmp/quick_experiment/8 | $HOME/Sources/patas/examples/sanity |
| sigmoid | 30 | 0.921 | 0.912 | 0 | 13 | 1 | 4 | 0 | quick_experiment | 0.027901 | 2023-05-09 18:05:18.005924 | 2023-05-09 18:05:18.033825 | 3 | 1 | 0 | quick_cluster | 0 | local_machine | 4 | /home/ubuntu/Sources/patas/tmp/quick_experiment/13 | $HOME/Sources/patas/examples/sanity |
| relu | 10 | 0.942 | 0.926 | 0 | 5 | 2 | 1 | 0 | quick_experiment | 0.027528 | 2023-05-09 18:05:18.010084 | 2023-05-09 18:05:18.037612 | 3 | 1 | 0 | quick_cluster | 0 | local_machine | 12 | /home/ubuntu/Sources/patas/tmp/quick_experiment/5 | $HOME/Sources/patas/examples/sanity |
| ... | ... | .... | .... | ... | ... | ... | ... | ... | ... | .... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |


# TL;DR 💻

```shell
# Parallelizing a program 
patas exec grid \
    --cmd './main.py {hidden_neurons} {activation_function}' \
    --vl hidden_neurons 10 20 30 \
    --vl activation_function sigmoid relu \
    --workdir '$HOME/Sources/patas/examples/sanity' \
    --repeat 2 \
    -o tmp

# Parsing the program output
patas parse \
    -e 'tmp/quick_experiment/' \
    -p TRAIN_ACC  'Train accuracy: (@float@)' \
    -p TEST_ACC   'Test accuracy:  (@float@)'
```

# Source Code 🎼

The source code is available in the project's [repository](https://github.com/diegofps/patas).
