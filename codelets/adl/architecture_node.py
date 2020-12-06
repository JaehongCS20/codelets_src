import numpy as np

from codelets.graph import Node
from codelets.adl.architecture_graph import ArchitectureGraph
from codelets.adl.codelet import Codelet
from pygraphviz import AGraph
from collections import namedtuple

Edge = namedtuple('Edge', ['src', 'dst', 'attributes'])

class ArchitectureNode(Node):
    """
    Base class for Architecture Node
    Inherited from Node
    """

    def __init__(self, name, index=None):
        super(ArchitectureNode, self).__init__(index=index)
        self._has_parent = None
        self._subgraph = ArchitectureGraph()
        self._name = name
        if self.name:
            self.set_attr("name", self.name)
        # type
        self._anode_type = type(self).__name__
        self._all_subgraph_nodes = {}
        self._subgraph_nodes = {}
        self._subgraph_edges = []
        self._in_edges = {}
        self._out_edges = {}

        # capabilities
        self._capabilities = {}

        # occupied: [(op_node, capability, begin_cycle, end_cycle)]
        # later consider changing to custom Heap because this needs to be accessed very frequently
        self._occupied = [] # NOTE state in TABLA compiler...

    def __enter__(self):
        return self

    def __exit__(self, exec_type, exec_value, exec_traceback):
        pass
    
    def __str__(self):
        return f'op {self.index} ({self.get_type()}): \
                 preds={self.get_preds_indices()} ({self._attrs["in_degree"]}), \
                 succs={self.get_succs_indices()} ({self._attrs["out_degree"]})'
    
    # two categories of operation
    # modifying anode type arbitrarily should not be permitted

    @property
    def name(self):
        return self._name

    @property
    def subgraph(self):
        return self._subgraph

    def networkx_visualize(self, filename):
        dgraph = AGraph(strict=False, directed=True)

        for n in self.subgraph.get_nodes():
            self.subgraph._add_nx_subgraph(dgraph, n)

        dgraph.add_edges_from(self.subgraph.get_viz_edge_list())

        dgraph.layout("dot")
        dgraph.draw(f"{filename}.pdf", format="pdf")
    #
    def set_parent(self, node_id):
        self._has_parent = node_id

    def get_viz_attr(self):
        raise NotImplementedError

    def add_subgraph_edge(self, src, dst, attributes=None):

        if self._has_parent:
            raise RuntimeError("Already added node to graph, cannot continue to add subgraph edges")
        if attributes:
            assert isinstance(attributes, dict)
            attr = []
            for k,v in attributes.items():
                attr.append({k: v})
        else:
            attr = []

        if isinstance(src, str):
            src = self.get_subgraph_node(src)

        if isinstance(dst, str):
            dst = self.get_subgraph_node(dst)

        if src.index not in self.subgraph._nodes:
            self.add_in_edge(src)

        if dst.index not in self.subgraph._nodes:
            self.add_out_edge(dst)

        edge = Edge(src=src.index, dst=dst.index, attributes=attr)
        self._subgraph_edges.append(edge)
        self.subgraph.add_edge(src, dst)

    def add_subgraph_node(self, node: 'ArchitectureNode'):
        if self._has_parent:
            raise RuntimeError("Already added node to graph, cannot continue to add subgraph nodes")


        self.merge_subgraph_nodes(node)
        node.set_parent(self.index)
        self.subgraph._add_node(node)
        self._subgraph_nodes[node.name] = node
        self._all_subgraph_nodes[node.name] = node

    def add_composite_node(self, node: 'ArchitectureNode', sub_nodes):
        for s in sub_nodes:
            s_node = self.get_subgraph_node(s)
            s_node.set_parent(None)
            node.add_subgraph_node(s_node)
            self.subgraph._nodes.pop(s_node.index)
            s_node.set_parent(node)
        self.add_subgraph_node(node)


    def add_in_edge(self, src):
        self._in_edges[src.name] = src
        self.subgraph.add_input(src)

    def add_out_edge(self, dst):
        self._out_edges[dst.name] = dst
        self.subgraph.add_output(dst)

    def get_subgraph_node(self, name):
        if name in self._in_edges:
            return self._in_edges[name]
        elif name in self._out_edges:
            return self._out_edges[name]
        elif name in self._all_subgraph_nodes:
            return self._all_subgraph_nodes[name]
        raise KeyError(f"{name} not found in subgraph or input_components")

    def get_type(self):
        return self._anode_type

    def merge_subgraph_nodes(self, node):
        intersection = node.subgraph._nodes.keys() & self.subgraph._nodes.keys()
        if len(intersection) > 0:
            raise RuntimeError(f"Overlapping keys when merging nodes for {self.name} and {node.name}")
        for name, n in node._all_subgraph_nodes.items():
            self._all_subgraph_nodes[n.name] = n
        self.subgraph._nodes.update(node.subgraph._nodes)


    def add_capability(self, capability: Codelet):
        self._capabilities[capability.get_name()] = capability

    def get_capability(self, name):
        return self._capabilities[name]

    def get_capabilities(self):
        return self._capabilities.keys()

    def is_compatible(self, op_name):
        return op_name in self._capabilities.keys()
    
    def set_occupied(self, op_code, capability, begin_cycle, end_cycle):
        
        # check for overlaps, "o" is occupied and "n" is new
        n = (begin_cycle, end_cycle)
        overlaps = [o for o in self._occupied if o[2] > n[0] and o[2] < n[1] or o[3] > n[0] and o[3] < n[1]]
        assert len(overlaps) == 0, 'this op_node cannot be mapped here, check before using set_occupied'

        # append to _occupied
        self._occupied.append((op_code, capability, begin_cycle, end_cycle))

    def get_occupied(self):
        return self._occupied

    def is_available(self, begin_cycle, end_cycle):

        # check for overlaps, "o" is occupied and "n" is new
        n = (begin_cycle, end_cycle)
        overlaps = [o for o in self._occupied if o[2] > n[0] and o[2] < n[1] or o[3] > n[0] and o[3] < n[1]]
        return len(overlaps) == 0

    @property
    def viz_color(self):
        raise NotImplementedError

    def get_subgraph_nodes(self):
        return list(self._subgraph_nodes.values())

    def get_subgraph_edges(self):
        return self._subgraph_edges

    def get_graph_node_count(self):
        count = 0
        for n in self.get_subgraph_nodes():
            count += (1 + n.get_graph_node_count())
        return count

    def get_graph_edge_count(self):
        count = len(self.get_subgraph_edges())
        for n in self.get_subgraph_nodes():
            count += n.get_graph_edge_count()
        return count

    def print_subgraph_edges(self, tabs=""):
        edge_pairs = [f"SRC: {self.subgraph.get_node_by_index(e.src).name}\t" \
                      f"DST:{self.subgraph.get_node_by_index(e.dst).name}" for e in self.get_subgraph_edges()]
        print(f"Total edges: {len(edge_pairs)}\n"
              f"Unique: {len(set(edge_pairs))}")
        print("\n".join(edge_pairs))
        tabs = tabs+"\t"
        for n in self.get_subgraph_nodes():
            n.print_subgraph_edges(tabs=tabs)
