from graphviz import Digraph
from typing import Callable
from igraph import Graph
from html import escape
import pickle
import json
import os

class Log:
    def __init__(self, output_path: str):
        '''
        Usage:
            Create a log file.
            It is used to keep track of the last index.
            So that we don not need to generate the data from scratch every time.

        Parameters:
            :output_path: the path of the output file.

        Returns:
            A file named 'idx.log' in the same directory as the output file.
            Example:
                {"filename": "train.jsonl", "idx": 110}
                {"filename": "dev.jsonl", "idx": 0}
        '''
        dirname = os.path.dirname(output_path)
        basename = os.path.basename(output_path)
        log_path = os.path.join(dirname, 'idx.log')
        self.log_path = log_path
        self.last_idx = 0
        if dirname and not os.path.exists(dirname):
            os.makedirs(dirname)
        self.logs = []
        if os.path.exists(log_path):
            with open(log_path, 'r', encoding='utf-8') as f_r:
                for line in f_r:
                    js = json.loads(line)
                    if js['filename'] == basename:
                        self.last_idx = int(js['idx'])
                    else:
                        self.logs.append(js)
        self.logs.append({'filename': basename, 'idx': self.last_idx})

    def update(self, idx: int):
        '''
        Usage:
            Update the last index of the idx data.

        Parameters:
            :idx: the new index.

        Returns:
            Rewrite the 'idx.log' file with the new index.
        '''
        with open(self.log_path, 'w', encoding='utf-8') as f_a:
            self.logs[-1]['idx'] = idx
            for js in self.logs:
                f_a.write(json.dumps(js, ensure_ascii=False) + '\n')
        self.last_idx = idx

    def set_zero(self):
        '''
        Usage:
            Set the last index of the data to 0.

        Returns:
            Rewrite the 'idx.log' file to set the last index to 0.
        '''
        self.last_idx = 0
        self.logs[-1]['idx'] = 0
        with open(self.log_path, 'w', encoding='utf-8') as f_a:
            for js in self.logs:
                f_a.write(json.dumps(js, ensure_ascii=False) + '\n')

class VisableGraph:
    def __init__(self):
        self.graph = Graph(directed=True)

    def node(self, id: int, **attrs):
        '''
        Usage:
            Add a node to the graph.

        Parameters:
            :id: the id of the node.
            :attrs: the attributes of the node.
                set the 'dot_kwargs' attribute to add dot node attribution.

        Example:
            node(1, label='Node 1', dot_kwargs={'shape': 'box', 'color': 'blue'})
        '''
        self.graph.add_vertex(str(id), **attrs)

    def edge(self, source: int, target: int, **attrs):
        '''
        Usage:
            Add an edge to the graph.

        Parameters:
            :source: the source node of the edge.
            :target: the target node of the edge.
            :attrs: the attributes of the edge.
                set the 'dot_kwargs' attribute to add dot edge attribution.

        Example:
            edge(1, 2, label='Edge 1', dot_kwargs={'color': 'blue'})
        '''
        self.graph.add_edge(str(source), str(target), **attrs)

    def nodes(self, ids: list[int], attrs: dict[str, list]):
        '''
        Usage:
            Add multiple nodes to the graph. Fast
            
        Parameters:
            :ids: the ids of the nodes.
            :attrs: the attributes of the nodes.

        Example:
            nodes(
                    [1, 2, 3], 
                    {
                        'label': ['Node 1', 'Node 2', 'Node 3'], 
                        'dot_kwargs': [
                            {'shape': 'box', 'color': 'blue'}, 
                            {'shape': 'circle', 'color': 'green'}, 
                            {'shape': 'diamond', 'color':'red'}
                        ]
                    }
                )
        '''
        self.graph.add_vertices(ids, attrs)

    def edges(self, edges: list[tuple[int, int]], attrs: dict[str, list]):
        '''
        Usage:
            Add multiple edges to the graph. Fast
            
        Parameters:
            :edges: the edges of the graph.
            :attrs: the attributes of the edges.

        Example:
            edges(
                    [(1, 2), (2, 3), (3, 1)], 
                    {
                        'label': ['Edge 1', 'Edge 2', 'Edge 3'], 
                        'dot_kwargs': [
                            {'color': 'blue'}, 
                            {'color': 'green'}, 
                            {'color':'red'}
                        ]
                    }
        '''
        self.graph.add_edges(edges, attrs)

    def render(self, node_property: Callable, edge_property: Callable = None, filename: str='output'):
        '''
        Usage:
            Render the graph.

        Parameters:
            :node_property: a function to get the label of the node.
            :edge_property: a function to get the label of the edge.
            :filename: the name of the output pdf file.

        Example:
            render(lambda node: node['label'], lambda edge: edge['label'], 'output.pdf')
        '''
        dot = Digraph(comment=filename)
        for node in self.graph.vs:
            node_attr = node.attributes()
            node_label = escape(node_property(node_attr))
            if 'dot_kwargs' in node_attr and node_attr['dot_kwargs']:
                dot.node(str(node.index), node_label, **node_attr['dot_kwargs'])
            else:
                dot.node(str(node.index), node_label)
            
        for edge in self.graph.es:
            edge_attr = edge.attributes()
            edge_label = escape(edge_property(edge_attr)) if edge_property else ''
            if 'dot_kwargs' in edge_attr and edge_attr['dot_kwargs']:
                dot.edge(str(edge.source), str(edge.target), edge_label, **edge_attr['dot_kwargs'])
            else:
                dot.edge(str(edge.source), str(edge.target), edge_label,)
            
        dot.render(filename, view=True, cleanup=True)

    def save(self, output_dir: str='output'):
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        with open(f'{output_dir}/graph.pkl', 'wb') as f:
            pickle.dump(self.graph, f)
    
    def load(self, input_dir: str='output'):
        with open(f'{input_dir}/graph.pkl', 'rb') as f:
            self.graph = pickle.load(f)

    def help(self):
        print('See igraph documentation at https://python.igraph.org/en/latest/tutorial.html')
        print('See python graphviz docs at https://graphviz.readthedocs.io/en/stable/manual.html')
        print('See dot node attribution at https://graphviz.org/docs/nodes/')
        print('See dot edge attribution at https://graphviz.org/docs/edges/')

    def __str__(self):
        return self.graph.summary()

