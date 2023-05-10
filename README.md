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

Assuming we want to vary the number of hidden neurons in the range `[10, 20, 30]` and the activation function in `['sigmoid', 'relu']`, we can parallelize the script above and collect its output using `patas explore grid`. For example, executing the following command from `$HOME/Sources/patas/`, patas will create the output folder named `tmp` holding the experiment's outputs.

```shell
patas explore grid \
    --cmd './main.py {neurons} {activation}' \
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
    -p train_acc  'Train accuracy: (@float@)' \
    -p test_acc   'Test accuracy:  (@float@)'
```

This will generate the file `$HOME/Sources/patas/tmp/quick_experiment/output.csv`, containing a table with the collected results, input variables and many other variables associated to the experiment. We can use `patas query` to inspect its content.

```shell
./patas/main.py query 'select * from grid limit 5' -p
```

The output should be similar to the content bellow.

| in_activation | in_neurons | out_train_acc | out_test_acc | break_id | task_id | repeat_id | combination_id | experiment_id | experiment_name | duration |          started_at |            ended_at | tries | max_tries | cluster_id | cluster_name | node_id | node_name | worker_id | output_dir                                 | work_dir                            |
| ------------- | ---------- | ------------- | ------------ | -------- | ------- | --------- | -------------- | ------------- | --------------- | -------- | ------------------- | ------------------- | ----- | --------- | ---------- | ------------ | ------- | --------- | --------- | ------------------------------------------ | ----------------------------------- |
| sigmoid       |         10 |         0,937 |        0,923 |    False |       1 |         1 |              0 |         False | grid            |   0,142… | 2023-05-10 11:09:18 | 2023-05-10 11:09:18 |  True |         3 |      False | cluster      |   False | node0     |         1 | /home/ubuntu/Sources/patas/patasout/grid/1  | $HOME/Sources/patas/examples/sanity |
| sigmoid       |         20 |         0,927 |        0,916 |    False |       8 |         2 |              2 |         False | grid            |   0,151… | 2023-05-10 11:09:18 | 2023-05-10 11:09:18 |  True |         3 |      False | cluster      |   False | node0     |         2 | /home/ubuntu/Sources/patas/patasout/grid/8  | $HOME/Sources/patas/examples/sanity |
| sigmoid       |         30 |         0,921 |        0,912 |    False |      13 |         1 |              4 |         False | grid            |   0,154… | 2023-05-10 11:09:17 | 2023-05-10 11:09:18 |  True |         3 |      False | cluster      |   False | node0     |         1 | /home/ubuntu/Sources/patas/patasout/grid/13 | $HOME/Sources/patas/examples/sanity |
| relu          |         10 |         0,942 |        0,926 |    False |       5 |         2 |              1 |         False | grid            |   0,151… | 2023-05-10 11:09:18 | 2023-05-10 11:09:18 |  True |         3 |      False | cluster      |   False | node0     |         1 | /home/ubuntu/Sources/patas/patasout/grid/5  | $HOME/Sources/patas/examples/sanity |
| relu          |         30 |         0,923 |        0,913 |    False |      17 |         2 |              5 |         False | grid            |   0,153… | 2023-05-10 11:09:17 | 2023-05-10 11:09:17 |  True |         3 |      False | cluster      |   False | node0     |         1 | /home/ubuntu/Sources/patas/patasout/grid/17 | $HOME/Sources/patas/examples/sanity |

# TL;DR 💻

```shell
# Parallelizing a program 
patas explore grid \
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

The source code is available in the project's [repository](https://github.com/ubuntufps/patas).
