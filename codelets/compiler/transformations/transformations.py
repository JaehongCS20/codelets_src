from codelets.adl.graph import ArchitectureNode
from codelets.adl.operation import Operation, Loop, Compute, Configure, Transfer
from codelets.adl.codelet import Codelet
from typing import List, Union, Dict, Tuple

TileConstraint = Dict[Tuple[str, str], Tuple[int, int]]


def unroll(loop):
    pass

def fuse(loops):
    pass

def reorder(loops, loop_permutation):
    pass

def find_minimum_idx(op: Operation, op_idx_map, op_list):
    dep_indices = [op_idx_map[o] for o in op.dependencies]
    if len(dep_indices) > 0:
        min_idx = max(dep_indices)
    else:
        min_idx = op_idx_map[op.op_str]

    return min_idx + 1

def split_loop(cdlt: Codelet, outer_loop: Loop, inner_loop: Loop, inner_tile_level: int):
    # split_factor = cdlt.t

    return inner_loop


def split_transfer(cdlt: Codelet, outer_xfer: Transfer, inner_xfer: Transfer):

    full_path = outer_xfer.path.copy()
    all_transfers = outer_xfer.transfers.copy()
    all_offsets = outer_xfer.offsets.copy()

    outer_xfer.path = full_path[:2]
    inner_xfer.path = full_path[1:]

    outer_xfer_key = tuple(full_path[:2])
    outer_xfer.transfers = {outer_xfer_key: all_transfers[outer_xfer_key]}
    inner_xfer.transfers.pop(outer_xfer_key)

    outer_xfer.offsets = all_offsets[:2]
    inner_xfer.offsets = all_offsets[1:]

    all_sizes = outer_xfer.sizes.copy()
    outer_xfer.sizes = [all_sizes[0]]
    inner_xfer.sizes = all_sizes[1:]

    return inner_xfer


def split_operation(cdlt: Codelet, op: Operation, loop_level: int, tile_level: int):

    inner_op = op.copy(cdlt)

    inner_op.op_id = Operation.op_id_counters[op.op_type]
    inner_op.global_op_id = Operation.id_counter
    inner_op.loop_level = loop_level
    Operation.op_id_counters[op.op_type] += 1
    Operation.id_counter += 1
    cdlt.op_map[inner_op.op_str] = inner_op
    cdlt.global_op_map[inner_op.global_op_id] = inner_op
    if isinstance(op, Transfer):
        inner_op = split_transfer(cdlt, op, inner_op)
    elif isinstance(op, Loop):
        inner_op = split_loop(cdlt, op, inner_op, tile_level)

    return inner_op


def lift_op(new_index, old_index, op_list: List[Union[Compute, Loop, Transfer, Configure, Operation]]):
    op = op_list[old_index]
    op._loop_id = op_list[new_index-1].loop_id
    op._loop_level = op_list[new_index-1].loop_level if op_list[new_index-1].op_type != "loop" else op_list[new_index-1].loop_level + 1
    op_list.insert(new_index, op_list.pop(old_index))

# TODO: The ordering relative to other operations needs to consider the loop level
def lift_operations(cdlt: Codelet):
    dep_indices = {l.op_str: i
                    for i, l in enumerate(cdlt.ops)}
    lifted_ops = cdlt.ops.copy()

    for o in cdlt.ops:
        if o.op_type != "loop" and len(o.dependencies) > 0:
            min_idx = find_minimum_idx(o, dep_indices, lifted_ops)
            if min_idx < dep_indices[o.op_str]:
                lift_op(min_idx, dep_indices[o.op_str], lifted_ops)
                dep_indices = {l.op_str: i
                               for i, l in enumerate(lifted_ops)}
    cdlt._ops = lifted_ops
    return cdlt


