
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import math


sns.set_theme()
# sns.set_theme(style="whitegrid")

class ColumnChanger:
    def __init__(self, change_function, column_name, context_name, function_name, add_f_string):
        self.column_name = column_name
        self.change_function = change_function
        self.context_name = context_name
        self.function_name = function_name
        self.add_f_string = add_f_string
        self.result = None


class ColumnsChanger:

    def __init__(self):
        self.changers:list[ColumnChanger] = []
    
    def add(self, change_function, column_name, context_name, function_name, add_f_string):
        self.changers.append(ColumnChanger(change_function, column_name, context_name, function_name, add_f_string))
    
    def apply(self, data):
        context = { 'math': math, 'pd': pd, 'np': np }

        for changer in self.changers:
            if changer.column_name:
                context[changer.context_name] = data[changer.column_name]
        
        for changer in self.changers:
            if changer.change_function:
                program = 'f"{' + changer.change_function + '}"' if changer.add_f_string else changer.change_function
                change_function = compile(program, changer.function_name, 'eval')
                changer.result = [eval(change_function, {'i':i, **context}) for i in range(data.shape[0])]
        
        for changer in self.changers:
            if changer.column_name and changer.result:
                data[changer.column_name] = changer.result


def render_heatmap(x_column, y_column, z_column,
                   title, x_label, y_label, z_label,
                   x_change, y_change, z_change, annot, fmt, 
                   input_file, output_file, 
                   fig_size, aggfunc, z_range):

    data_long = pd.read_csv(input_file)

    cc = ColumnsChanger()
    cc.add(x_change, x_column, 'X', 'patas.draw.heatmap.x_change', True)
    cc.add(y_change, y_column, 'Y', 'patas.draw.heatmap.y_change', True)
    cc.add(z_change, z_column, 'Z', 'patas.draw.heatmap.z_change', False)
    cc.apply(data_long)

    data = data_long.pivot_table(values=z_column, index=y_column, columns=x_column, aggfunc=aggfunc)

    cbar_kws = {}

    if z_label:
        cbar_kws['label'] = z_label

    f, ax = plt.subplots(figsize=fig_size)
    g = sns.heatmap(data, annot=annot, fmt=fmt, linewidths=.5, ax=ax, vmin=z_range[0], vmax=z_range[1], cbar_kws=cbar_kws)

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


def render_categories(x_column, y_column, hue_column,
                       title, x_label, y_label, legend_label,
                       x_change, y_change, hue_change, 
                       input_file, output_file, 
                       fig_size, errorbar):
    
    data_long = pd.read_csv(input_file)

    cc = ColumnsChanger()
    cc.add(x_change, x_column, 'X', 'patas.draw.categorical.x_change', True)
    cc.add(y_change, y_column, 'Y', 'patas.draw.categorical.y_change', True)
    cc.add(hue_change, hue_column, 'H', 'patas.draw.categorical.hue_change', False)
    cc.apply(data_long)

    g = sns.catplot(data=data_long, kind="bar", x=x_column, y=y_column, hue=hue_column, errorbar=errorbar)

    if fig_size:
        g.fig.set_size_inches(*fig_size)
        
    g.despine(left=True)
    g.fig.subplots_adjust(left=.08, bottom=.14)

    if legend_label:
        g.legend.set_title(legend_label)

    if x_label:
        g.ax.set_xlabel(x_label)
    
    if y_label:
        g.ax.set_ylabel(y_label)

    if title:
        g.fig.subplots_adjust(top=.9)
        g.ax.set_title(title)

    if output_file:
        plt.savefig(output_file)
    else:
        plt.show()


def render_lines(title, x_label, y_label, legend_label, 
                 x_column, y_column, hue_column, style_column, 
                 x_change, y_change, hue_change, style_change, 
                 input_file, output_file, 
                 fig_size, err_style, errorbar):
    
    data_long = pd.read_csv(input_file)

    cc = ColumnsChanger()
    cc.add(x_change, x_column, 'X', 'patas.draw.lines.x_change', True)
    cc.add(y_change, y_column, 'Y', 'patas.draw.lines.y_change', True)
    cc.add(hue_change, hue_column, 'H', 'patas.draw.lines.hue_change', False)
    cc.add(style_change, style_column, 'S', 'patas.draw.lines.style_change', False)
    cc.apply(data_long)

    ax = sns.lineplot(data=data_long, 
                     x=x_column, y=y_column, hue=hue_column, style=style_column,
                     err_style=err_style, errorbar=errorbar)

    fig = ax.get_figure()

    ax.set(xticks=data_long[x_column].unique())

    if fig_size:
        fig.set_size_inches(*fig_size)
        
    fig.subplots_adjust(left=.08, bottom=.14)

    if title:
        fig.subplots_adjust(top=.9)
        ax.set_title(title)

    if x_label:
        ax.set_xlabel(x_label)
    
    if y_label:
        ax.set_ylabel(y_label)

    if legend_label:
        ax.get_legend().set_title(legend_label)

    # if style_label:
    #     g.legend.set_title(hue_label)

    if output_file:
        plt.savefig(output_file)
    else:
        plt.show()


