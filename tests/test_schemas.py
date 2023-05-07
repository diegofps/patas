from patas.schemas import load_cluster, load_experiment, format_as_yaml

def unindent(n, data):

    prefix = ' ' * n
    lines = [x[n:] if x.startswith(prefix) else x for x in data.split('\n')]
    return '\n'.join(lines[1:] if lines[0] == '' else lines)


def test_cluster_schema():
    cluster = load_cluster('./tests/data/cluster.yaml')
    assert cluster.name == 'wespa'
    assert len(cluster.nodes) == 2

def test_experiment_schema():
    experiment = load_experiment('./tests/data/experiment.yaml')
    assert experiment.name == 'trackerx'
    assert experiment.workdir == '$HOME/Sources/patas/test'
    assert experiment.repeat == 3
    assert experiment.max_tries == 2
    assert experiment.redo == True
    assert len(experiment.cmd) == 1
    assert len(experiment.vars) == 3

def test_format_as_yaml():
    expected_output = unindent(8, """
        cmd:
        - ls -la {v1}
        max_tries: 2
        name: trackerx
        redo: true
        repeat: 3
        vars:
        - type: list
          values:
          - a
          - b
          - c
          - d
        - factor: 1
          max: 10
          min: 1
          type: arithmetic
        - factor: 2
          max: 17
          min: 1
          type: geometric
        workdir: $HOME/Sources/patas/test
        """)

    experiment = load_experiment('./tests/data/experiment.yaml')
    assert format_as_yaml(experiment) == expected_output

