"""Check the local SDK and a tiny conversion. Never submits a cloud job."""
import inspect
import json

from cg.pricing.cim_backend import cim_options
from cg.pricing.cim_worker import check_interface, prepare_model


def main():
    import kaiwu as kw
    check_interface(kw)
    request = dict(ids=[0, 1], weights=[2, 1], edges=[[0, 1]], forbidden=[],
                   penalty=3.0, options=cim_options())
    matrix, variables = prepare_model(request, kw)
    print(json.dumps(dict(submitted=False, kaiwu_version=getattr(kw, "__version__", "unknown"),
        constructor=str(inspect.signature(kw.cim.CIMOptimizer)),
        matrix_shape=list(matrix.shape), variable_count=len(variables)), indent=2))


if __name__ == "__main__":
    main()
