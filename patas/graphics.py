
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np


sns.set_theme()


def change_column(data, column_name, change_function, context, name, add_f_string):
    if change_function:
        program = 'f"{' + change_function + '}"' if add_f_string else change_function
        change_function = compile(program, name, 'eval')
        data[column_name] = [eval(change_function, {'i':i, **context}) for i in range(data.shape[0])]


def render_heatmap(x_column, y_column, z_column,
                   title, x_label, y_label, z_label,
                   x_change, y_change, z_change, annot, fmt, 
                   input_file, output_file, 
                   fig_size, aggfunc):

    data_long = pd.read_csv(input_file)

    context = {
        'X': data_long[x_column],
        'Y': data_long[y_column],
        'Z': data_long[z_column],
    }

    change_column(data_long, x_column, x_change, context, 'patas.draw.heatmap.x_change', True )
    change_column(data_long, y_column, y_change, context, 'patas.draw.heatmap.y_change', True )
    change_column(data_long, z_column, z_change, context, 'patas.draw.heatmap.z_change', False)

    data = data_long.pivot_table(values=z_column, index=y_column, columns=x_column, aggfunc=aggfunc)

    cbar_kws = {}

    if z_label:
        cbar_kws['label'] = z_label

    f, ax = plt.subplots(figsize=fig_size)
    g = sns.heatmap(data, annot=annot, fmt=fmt, linewidths=.5, ax=ax, cbar_kws=cbar_kws)

    if x_label:
        g.set_xlabel(x_label)
    
    if y_label:
        g.set_ylabel(y_label)

    if title:
        g.set_title(title)

    f.tight_layout()

    if output_file:
        plt.savefig(output_file)
    else:
        plt.show()


def render_bars(x_column, y_column, 
                title, x_label, r_label, 
                x_change, y_change, r_format, 
                input_file, output_file, 
                size, r_function, bar_color, bar_size, horizontal, show_grid, 
                ticks, ticks_format, border, show_error,
                verbose):
    
    # Remove borders and display/save

    fig.tight_layout()

    if output_file:
        plt.savefig(output_file)
    else:
        plt.show()


def render_lines(lines, title, size, 
                 x_label, r_label, 
                 input_file, output_file, 
                 show_grid, border, show_error, 
                 ticks, ticks_format, legend_location,
                 verbose):
    
    # Remove borders and display/save

    fig.tight_layout()

    if output_file:
        plt.savefig(output_file)
    else:
        plt.show()



