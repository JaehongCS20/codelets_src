import json
import polymath as pm
from typing import List, Dict, Callable
from codelets.adl import ArchitectureNode, OperandTemplate, Codelet
from codelets.adl.operand import Datatype
from pathlib import Path
import numpy as np
from collections import defaultdict
from .compilation_parameters import get_compilation_parameters
from .relocation_table import RelocationTable

class CodeletProgram(object):

    def __init__(self, name, hag: ArchitectureNode):
        self._name = name
        self._hag = hag
        self._codelets = []
        self._relocatables = RelocationTable()

    @property
    def name(self) -> str:
        return self._name

    @property
    def hag(self) -> ArchitectureNode:
        return self._hag

    @property
    def codelets(self) -> List[Codelet]:
        return self._codelets

    @property
    def relocatables(self) -> RelocationTable:
        return self._relocatables

    def add_codelet(self, cdlt: Codelet):
        self._codelets.append(cdlt)

    def save(self, output_path=None, save_format="json"):
        if output_path:
            if output_path[-1] != "/":
                output_path = output_path + "/"
        else:
            output_path = str(Path.cwd()) + "/"

        if save_format == "json":
            full_path = f"{output_path}{self.name}.json"
            self.save_json(full_path)
        elif save_format == "text":
            full_path = f"{output_path}{self.name}.txt"
            self.save_text(full_path)
        else:
            raise ValueError(f"Invalid file output: {save_format}")

    # TODO: Fix these
    def save_json(self, full_path):
        json_blob = [o.compiled_json() for o in self.codelets]
        with open(full_path, 'w') as outfile:
            json.dump(json_blob, outfile, indent=4)

    def save_text(self, full_path):
        instructions = []
        for c in self.codelets:
            instructions += c.get_text_instructions()
        instructions = "\n".join(instructions)
        with open(full_path, 'w') as outfile:
            outfile.write(instructions)

    def save_binary(self, full_path):
        raise NotImplementedError

    def get_node_dtype(self, op_tmplt, node: pm.Node) -> Datatype:
        if "hag_dtype" not in node.kwargs:
            dtype = op_tmplt.dtypes[0]
            node.add_attribute("hag_dtype", str(dtype))
        else:
            assert op_tmplt.is_dtype_supported(node.kwargs['hag_dtype'])
            dtype = Datatype.from_str(node.kwargs['hag_dtype'])
        return dtype

    def get_node_shape_map(self, op_tmplt: OperandTemplate, node: pm.Node) -> Dict[str, Dict]:
        shape_map = {}
        for i, s in enumerate(node.shape):

            key = op_tmplt.shape_symbols[i]
            shape_map[key] = {'value': s,
                              'dimension': i}
        return shape_map

    def instantiate_inputs(self, cdlt, node, loop_values) -> List[OperandTemplate]:
        inputs = []
        for i, ipt in enumerate(node.source):
            dtype = self.get_node_dtype(cdlt.source[i], ipt)
            shape_map = self.get_node_shape_map(cdlt.source[i], ipt)
            name = ipt.name
            memory_path = cdlt.source[i].memory_path
            iter_domain = cdlt.source[i].iteration_domain
            ipt_instance = OperandTemplate(name,
                                           dtypes=dtype,
                                           memory_path=memory_path,
                                           shape_symbols=shape_map,
                                           iteration_domain=iter_domain)
            inputs.append(ipt_instance)

        return inputs

    def instantiate_outputs(self, cdlt, node, loop_values) -> List[OperandTemplate]:
        outputs = []
        for i, opt in enumerate(node.dest):
            dtype = self.get_node_dtype(cdlt.dest[i], opt)
            shape_map = self.get_node_shape_map(cdlt.dest[i], opt)
            name = opt.name
            memory_path = cdlt.dest[i].memory_path
            iter_domain = cdlt.dest[i].iteration_domain
            opt_instance = OperandTemplate(name,
                                           dtypes=dtype,
                                           memory_path=memory_path,
                                           shape_symbols=shape_map,
                                           iteration_domain=iter_domain)
            outputs.append(opt_instance)

        return outputs

    def get_tiling_dims(self, inputs: List[OperandTemplate], outputs: List[OperandTemplate]):
        assert all([i.is_instantiated() for i in inputs])
        assert all([o.is_instantiated() for o in outputs])

    def get_dim_values(self, cdlt: Codelet, node: pm.Node):
        all_cdlt_ops = cdlt.inputs + cdlt.outputs
        all_node_ops = node.inputs + node.outputs
        tiling_dims = {}
        for i, opt in enumerate(all_node_ops):
            tiling_dims.update(self.get_node_shape_map(all_cdlt_ops[i], opt))

        return tiling_dims

    def instantiate_codelet(self, node):
        cdlt = self.hag.get_codelet_template(node.op_name)
        instance_params = {}
        tiling_dims = self.get_dim_values(cdlt, node)
        inputs = self.instantiate_inputs(cdlt, node, tiling_dims)
        outputs = self.instantiate_outputs(cdlt, node, tiling_dims)
        cap_copy = [c.copy() for c in cdlt.capability_sequence]

        for k, v in cdlt.op_params.items():
            if isinstance(v, Callable):
                instance_params[k] = v(node)
            else:
                instance_params[k] = v
        cdlt_instance = Codelet(cap_copy, inputs, outputs, cdlt, op_params=instance_params)
        compilation_parameters = get_compilation_parameters(self.hag, cdlt_instance)
        if cdlt_instance.codelet_id == "conv1":
            print(compilation_parameters)
            # TODO: Need to make sure all nodes have input/output defined
        self.relocatables.add_relocation(node, cdlt_instance)
        self.add_codelet(cdlt_instance)
        return cdlt_instance

    #
    # def determine_compiler_params(self, cdlt):
    #     tiling = self.get_tiling(cdlt)



def generate_possible_tilings(shape_dict, memory_paths):
    possible_tilings = {}

    for k, v in shape_dict.items():
        tile_permutations = []

def tiling_constraint(shapes, node_capacities, tile_sizes):

    for i, t in enumerate(tile_sizes):
        data_size = np.prod([t[s] for s in shapes])
        if data_size >= node_capacities[i]:
            return False
    return True
