
from .util import range_from_cfg
from .arch_constraints import add_simd_constraint, add_conv_constraints, add_gemm_constraints
from .fusion_layers import FUSION_CODELETS, FUSION_OP_INFO
from .gradients import GRADIENT_CDLTS
from .binary import BINARY_CODELETS
from .unary import UNARY_CODELETS
from .dnn import DNN_CDLTS
from .transform import TRANSFORM_CDLTS
from .systolic_array import SA_CDLTS



GENESYS_CODELETS = {
    **FUSION_CODELETS,
    **GRADIENT_CDLTS,
    **BINARY_CODELETS,
    **UNARY_CODELETS,
    **DNN_CDLTS,
    **TRANSFORM_CDLTS,
    **SA_CDLTS
}