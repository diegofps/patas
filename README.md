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

import random
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
train_accuracy = 0.9 + 0.1 / (1+  w) + random.gauss(0,0.05)
test_accuracy  = 0.9 + 0.1 / (1+2*w) + random.gauss(0,0.05)

# Print relevant results
print("Results:")
print(f"    Train accuracy: {train_accuracy:.3f}")
print(f"    Test accuracy:  {test_accuracy:.3f}")
```

Assuming we want to vary the number of hidden neurons in the range `[10, 20, 30]` and the activation function in `['sigmoid', 'relu']`, we can parallelize the script above and collect its output using `patas explore grid`. For example, executing the following command from `$HOME/Sources/patas/`, patas will create the output folder named `tmp` holding the experiment's outputs.

```shell
patas explore grid \
    --cmd './main.py {neurons} {activation}' \
    --vl neurons 5 10 15 20 25 30 \
    --vl activation relu leaky_relu sigmoid tanh \
    --repeat 10
```

When the experiment is done, we can parse the outputs and collect desired values using `patas parse`.

```shell
patas parse \
    -e 'patasout/grid/' \
    -p train_acc  'Train accuracy: (@float@)' \
    -p test_acc   'Test accuracy:  (@float@)'
```

This will generate the file `$HOME/Sources/patas/tmp/quick_experiment/output.csv`, containing a table with the collected results, input variables and many other variables associated to the experiment. We can use `patas query` to inspect its content.

```shell
patas query 'select * from grid limit 1' -p
```

The output should be similar to the content bellow.

| in_activation | in_neurons | out_train_acc | out_test_acc | break_id | task_id | repeat_id | combination_id | experiment_id | experiment_name | duration |          started_at |            ended_at | tries | max_tries | cluster_id | cluster_name | node_id | node_name | worker_id | output_dir                                                 | work_dir                                  |
| ------------- | ---------- | ------------- | ------------ | -------- | ------- | --------- | -------------- | ------------- | --------------- | -------- | ------------------- | ------------------- | ----- | --------- | ---------- | ------------ | ------- | --------- | --------- | ---------------------------------------------------------- | ----------------------------------------- |
| sigmoid       |         10 |         0,909 |        0,913 |    False |      64 |         4 |              6 |         False | grid            |   0,032… | 2023-05-10 14:58:09 | 2023-05-10 14:58:09 |  True |         3 |      False | cluster      |   False | localhost |        44 | /home/diego/Sources/patas/examples/sanity/patasout/grid/64 | /home/diego/Sources/patas/examples/sanity |
| relu          |         10 |         0,898 |        0,890 |    False |      41 |         1 |              4 |         False | grid            |   0,033… | 2023-05-10 14:58:09 | 2023-05-10 14:58:09 |  True |         3 |      False | cluster      |   False | localhost |        21 | /home/diego/Sources/patas/examples/sanity/patasout/grid/41 | /home/diego/Sources/patas/examples/sanity |

We must remember that for every combination, patas will execute the program `--repeat` times, passing the same input parameters and collecting multiple output variables. This is useful when the algorithm we are evaluating is non-deterministic and we wish to collect reliable metrics. To aggregate these values we can calculate the average value using the `AVG` function with the `GROUP BY` statement.

```shell
patas query '
    SELECT in_activation, 
           in_neurons, 
           AVG(out_train_acc) as avg_train_acc, 
           AVG(out_test_acc) as avg_test_acc
    FROM grid GROUP BY in_activation, in_neurons' -p
```

This will give us an output similar to the table bellow.

| in_activation | in_neurons | avg(out_train_acc) | avg(out_test_acc) |
| ------------- | ---------- | ------------------ | ----------------- |
| leaky_relu    |          5 |             0,950… |            0,920… |
| leaky_relu    |         10 |             0,940… |            0,928… |
| leaky_relu    |         15 |             0,928… |            0,912… |
| leaky_relu    |         20 |             0,912… |            0,933… |
| leaky_relu    |         25 |             0,935… |            0,914… |
| leaky_relu    |         30 |             0,920… |            0,924… |
| relu          |          5 |             0,995… |            0,946… |
| relu          |         10 |             0,911… |            0,933… |
| relu          |         15 |             0,942… |            0,930… |
| relu          |         20 |             0,955… |            0,912… |
| relu          |         25 |             0,932… |            0,915… |
| relu          |         30 |             0,923… |            0,943… |
| sigmoid       |          5 |             0,957… |            0,917… |
| sigmoid       |         10 |             0,927… |            0,937… |
| sigmoid       |         15 |             0,924… |            0,914… |
| sigmoid       |         20 |             0,923… |            0,923… |
| sigmoid       |         25 |             0,921… |            0,928… |
| sigmoid       |         30 |             0,899… |            0,924… |
| tanh          |          5 |             0,973… |            0,938… |
| tanh          |         10 |             0,948… |            0,918… |
| tanh          |         15 |             0,962… |            0,915… |
| tanh          |         20 |             0,944… |            0,916… |
| tanh          |         25 |             0,920… |            0,927… |
| tanh          |         30 |             0,919… |            0,885… |


To pick the input parameters that gave us the best average test_accuracy, we could use the following query.

```shell
patas query '
    WITH avg_result AS (
        SELECT in_activation, 
               in_neurons, 
               AVG(out_train_acc) AS train_acc, 
               AVG(out_test_acc) AS test_acc 
        FROM grid 
        GROUP BY in_activation, in_neurons
    )
    SELECT * FROM avg_result AS t 
    WHERE t.test_acc=(SELECT MAX(test_acc) FROM avg_result)' -p
```

A possible output for the previous command would be.

| in_activation | in_neurons | train_acc | test_acc |
| ------------- | ---------- | --------- | -------- |
| relu          |          5 |    0,995… |   0,946… |


```
~/Sources/patas/patas/main.py draw heatmap \
    --input ./examples/sanity/patasout/grid/grid.csv \
    --x-column in_neurons \
    --y-column in_activation \
    --z-column out_test_acc \
    --reduce mean
```


# TL;DR 💻

```shell
# Parallelizing a program in the local machine. Use the local directory as workdir
patas explore grid \
    --cmd './main.py {neurons} {activation}' \
    --vl neurons 5 10 15 20 25 30 \
    --vl activation relu leaky_relu sigmoid tanh \
    --repeat 2

# Parsing the program output
patas parse \
    -e 'pandasout/grid/' \
    -p TRAIN_ACC  'Train accuracy: (@float@)' \
    -p TEST_ACC   'Test accuracy:  (@float@)'
```

# Source Code 🎼

The source code is available in the project's [repository](https://github.com/ubuntufps/patas).
