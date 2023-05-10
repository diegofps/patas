from matplotlib import pyplot as plt
from collections import defaultdict

import numpy as np


def read_csv(filepath):
    
    return np.genfromtxt(filepath, delimiter=';', dtype=None, encoding='utf-8')


def find_all_values(column):

    unique_values = []
    value2id = {}

    for i in range(column.shape[0]):
        l = column[i]
        if not l in value2id:
            value2id[l] = len(value2id)
            unique_values.append(l)

    return value2id, unique_values


def render_heatmap(x_column, y_column, z_column,
                   title, x_label, y_label,
                   x_change, y_change, z_change,
                   input_file, output_file, 
                   z_format, size, verbose, reduce):
    
    # Read the data

    src     = read_csv(input_file)
    headers = src[0,:]
    data    = src[1:,:]

    if verbose:
        print("HEADERS")
        print(headers)
        
        print("DATA")
        print(data)

    # Locate headers and create a new matrix

    x_index = np.where(headers == x_column)[0][0]
    y_index = np.where(headers == y_column)[0][0]
    z_index = np.where(headers == z_column)[0][0]

    data2 = np.array([data[:,x_index], data[:,y_index], data[:,z_index].astype(float)], dtype='object').transpose()

    if verbose:
        print("COLUMNS: x={}, y={}, z={}".format(x_index, y_index, z_index))
        print(data2)

    # Apply transformations

    if x_change:
        for y in range(data.shape[0]):
            data2[y,0] = eval(x_change)

    if y_change:
        for y in range(data.shape[0]):
            data2[y,1] = eval(y_change)

    if z_change:
        for y in range(data.shape[0]):
            data2[y,2] = eval(z_change)


    # Aggregate the results
    
    xy_to_z_values = defaultdict(list)

    for y in range(data2.shape[0]):

        x_value = data2[y, 0]
        y_value = data2[y, 1]
        z_value = data2[y, 2]

        z_values = xy_to_z_values[(x_value, y_value)]
        z_values.append(z_value)

    x_value_to_pos, x_values = find_all_values(data2[:,0])
    y_value_to_pos, y_values = find_all_values(data2[:,1])

    # Create the heatmap and aggregate multiple values

    heatmap = np.zeros((len(y_value_to_pos), len(x_value_to_pos)), np.float32)

    reduce = {
        "sum"    : np.sum,
        "mean"   : np.mean,
        "std"    : np.std,
        "product": np.product,
        "min"    : np.min,
        "max"    : np.max,
    }[reduce]

    for key in xy_to_z_values:
        z_values = xy_to_z_values[key]
        x_value, y_value = key

        x_pos = x_value_to_pos[x_value]
        y_pos = y_value_to_pos[y_value]

        heatmap[y_pos, x_pos] = reduce(z_values)

    # Create the heatmap

    if not size:
        size = (10,7)
        
    fig, ax = plt.subplots(figsize=size)

    im = ax.imshow(heatmap)

    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel("Intensity", rotation=-90, va="bottom")

    ax.set_xticks(np.arange(len(x_value_to_pos)))
    ax.set_yticks(np.arange(len(y_value_to_pos)))

    ax.set_xticklabels(x_values)
    ax.set_yticklabels(y_values)

    if y_label:
        ax.set_ylabel(y_label)
    
    if x_label:
        ax.set_xlabel(x_label)

    # Draw labels for each cell

    if z_format:
        for y in range(len(y_value_to_pos)):
            for x in range(len(x_value_to_pos)):
                value = eval(z_format)
                text = ax.text(x, y, value, ha="center", va="center", color="w")

    # Draw labels for x and y axis

    plt.setp(ax.get_xticklabels(), rotation=30, ha="right", rotation_mode="anchor")
    plt.setp(ax.get_yticklabels(), rotation=30, ha="right", rotation_mode="anchor")

    # Set title
    if title:
        ax.set_title(title)

    fig.tight_layout()

    if output_file:
        plt.savefig(output_file)
    else:
        plt.show()
