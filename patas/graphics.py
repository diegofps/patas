from matplotlib import pyplot as plt
from collections import defaultdict

import numpy as np
import math


DEFAULT_SIZE = (10,7)

REDUCE_OPTIONS = {
    "sum"    : np.sum,
    "mean"   : np.mean,
    "std"    : np.std,
    "product": np.product,
    "min"    : np.min,
    "max"    : np.max,
}

def read_csv(filepath):
    
    return np.genfromtxt(filepath, delimiter=',', dtype=None, encoding='utf-8')


def find_all_values(column):

    unique = np.unique(column)

    try:
        weights = unique.astype(float)
    except ValueError:
        weights = unique
    
    pairs = list(zip(weights, unique))
    pairs.sort()

    value_to_id = {x[1]:i for i,x in enumerate(pairs)}
    values      = [x[1] for x in pairs]
    
    return value_to_id, values


def get_size(size):
    return DEFAULT_SIZE if size is None else size


def get_color(color):
    
    if color is None:
        return 'maroon'
    else:
        from matplotlib.colors import to_rgba
        return to_rgba(color if color[0] == '#' else '#' + color)


def get_width(width):
    return 0.7 if width is None else width


def get_colormap(colormap):

    if not colormap:
        return None

    elif len(colormap) == 1:
        return colormap[0]
    
    else:
        from matplotlib.colors import LinearSegmentedColormap
        from matplotlib.colors import to_rgba

        colors = [to_rgba(x if x[0] == '#' else '#' + x) for x in colormap]
        n      = len(colormap)

        cdict = {
            'red':   [[i/(n-1), color[0], color[0]] for i, color in enumerate(colors)],
            'green': [[i/(n-1), color[1], color[1]] for i, color in enumerate(colors)],
            'blue':  [[i/(n-1), color[2], color[2]] for i, color in enumerate(colors)],
        }
        
        return LinearSegmentedColormap('CustomCMap', segmentdata=cdict, N=256)


def find_column(headers, column_name):
    return np.where(headers == column_name)[0][0]


def change_column(data, column_idx, change_function, name, context):

    if change_function:
        change_function = compile('f"{' + change_function + '}"', name, 'eval')
        for i in range(data.shape[0]):
            context['i'] = i
            data[i,column_idx] = eval(change_function, context)


def render_heatmap(x_column, y_column, z_column,
                   title, x_label, y_label, z_label,
                   x_change, y_change, z_change, z_format, 
                   input_file, output_file, 
                   size, reduce, colormap, verbose):
    
    # Read the data

    src     = read_csv(input_file)
    headers = src[0,:]
    data    = src[1:,:]

    if verbose:
        print("HEADERS")
        print(headers)
        
        print("DATA")
        print(data)

    # Locate headers and isolate the parse the data into a new matrix

    x_index = find_column(headers, x_column)
    y_index = find_column(headers, y_column)
    z_index = find_column(headers, z_column)

    data2 = np.array([data[:,x_index], data[:,y_index], data[:,z_index].astype(float)], dtype='object').transpose()

    if verbose:
        print("COLUMNS: x={}, y={}, z={}".format(x_index, y_index, z_index))
        print(data2)

    # Apply transformations

    context = {
        'math': math,
        'X':data2[:,0],
        'Y':data2[:,1],
        'Z':data2[:,2],
    }

    change_column(data2, 0, x_change, 'x_change', context)
    change_column(data2, 1, y_change, 'y_change', context)
    change_column(data2, 2, z_change, 'z_change', context)

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

    reduce = REDUCE_OPTIONS[reduce]

    for (x_value, y_value), z_values in xy_to_z_values.items():
        # z_values = xy_to_z_values[key]
        # x_value, y_value = key

        x_pos = x_value_to_pos[x_value]
        y_pos = y_value_to_pos[y_value]

        heatmap[y_pos, x_pos] = reduce(z_values)

    # Create the heatmap

    if not size:
        size = DEFAULT_SIZE
        
    fig, ax = plt.subplots(figsize=size)

    im = ax.imshow(heatmap, cmap=get_colormap(colormap))

    cbar = ax.figure.colorbar(im, ax=ax)
    cbar.ax.set_ylabel(z_label if z_label else "Intensity", rotation=-90, va="bottom")

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

        z_format = compile(z_format, 'z_format', 'eval')

        context = {
            'math': math,
            'D': heatmap
        }

        for y in range(len(y_value_to_pos)):
            for x in range(len(x_value_to_pos)):

                context['y'] = y
                context['x'] = x

                value = eval(z_format, context)
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


def render_bars(x_column, y_column, 
                title, x_label, y_label, 
                x_change, y_change, y_format, 
                input_file, output_file, 
                size, reduce, color, width, horizontal, gridlines, ticks, tick_format,
                verbose):
    
    src     = read_csv(input_file)
    headers = src[0,:]
    data    = src[1:,:]

    # Locate headers and isolate the parse the data into a new matrix

    x_index = find_column(headers, x_column)
    y_index = find_column(headers, y_column)

    data2 = np.array([data[:,x_index], data[:,y_index].astype(float)], dtype='object').transpose()

    # Apply transformations

    context = {
        'math': math,
        'X':data2[:,0],
        'Y':data2[:,1],
    }

    change_column(data2, 0, x_change, 'x_change', context)
    change_column(data2, 1, y_change, 'y_change', context)

    # Reduce values
    
    x_to_y_values = defaultdict(list)

    for y in range(data2.shape[0]):
        x_value = data2[y, 0]
        y_value = data2[y, 1]
        x_to_y_values[x_value].append(y_value)

    x_value_to_pos, x_data = find_all_values(data2[:,0])

    # Create the heatmap and aggregate multiple values

    y_data = np.zeros((len(x_value_to_pos),), np.float32)
    reduce   = REDUCE_OPTIONS[reduce]

    for x_value, y_values in x_to_y_values.items():
        x_pos = x_value_to_pos[x_value]
        y_data[x_pos] = reduce(y_values)

    # Create the graphic

    fig, ax = plt.subplots(figsize = get_size(size))

    # Add annotation to bars

    if y_format:
        for i in ax.patches:
            plt.text(i.get_width() + 0.2, 
                     i.get_y() + 0.5,
                     str(round((i.get_width()), 2)),
                     fontsize = 10, 
                     fontweight = 'bold',
                     color = 'grey')
    
    # Show Gridlines

    if gridlines:
        ax.grid(visible=True, 
                color='grey',
                linestyle='-.', 
                linewidth=0.5,
                alpha=0.2)
    
    # Creating the bar plot

    if horizontal:
        ax.barh(x_data, y_data, color=get_color(color), height=get_width(width))
    else:
        ax.bar(x_data, y_data, color=get_color(color), width=get_width(width))
    
    if x_label:
        ax.xlabel(x_label)
    
    if y_label:
        ax.ylabel(y_label)
    
    if title:
        ax.title(title)
    
    # Format ticks 

    tick_function            = plt.xticks if horizontal else plt.yticks

    if tick_format:
        tick_format = compile('f"{' + tick_format + '}"', 'tick_format', 'eval')
    
    if ticks:
        lowest      = np.min(y_data)
        highest     = np.max(y_data)
        step        = (highest - lowest) / (ticks - 1)
        tick_values = np.arange(lowest, highest + step / 2, step)

        if tick_format:
            tick_labels = [eval(tick_format, {'t':t}) for t in tick_values]
            tick_function(ticks=tick_values, labels=tick_labels)
            
        else:
            tick_labels = [str(t) for t in tick_values]
            tick_function(ticks=tick_values, labels=tick_labels)
        
    elif tick_format:
        tick_values, _ = tick_function()
        tick_labels = [eval(tick_format, {'t':t}) for t in tick_values]
        tick_function(ticks=tick_values, labels=tick_labels)

    # Remove borders and display/save

    fig.tight_layout()

    if output_file:
        plt.savefig(output_file)
    else:
        plt.show()


def render_lines():
    pass
