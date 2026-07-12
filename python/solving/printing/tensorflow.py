import solving.codegen
import solving.codegen.cfunctions
from solving.external.importtools import version_tuple
from collections.abc import Iterable

from solving.core.mul import Mul
from solving.core.singleton import S
from solving.codegen.cfunctions import Sqrt
from solving.external import import_module
from solving.printing.precedence import PRECEDENCE
from solving.printing.pycode import AbstractPythonCodePrinter, ArrayPrinter
import solving

tensorflow = import_module('tensorflow')

class TensorflowPrinter(ArrayPrinter, AbstractPythonCodePrinter):
    """
    Tensorflow printer which handles vectorized piecewise functions,
    logical operators, max/min, and relational operators.
    """
    printmethod = "_tensorflowcode"

    mapping = {
        solving.Abs: "tensorflow.math.abs",
        solving.sign: "tensorflow.math.sign",

        # XXX May raise error for ints.
        solving.ceiling: "tensorflow.math.ceil",
        solving.floor: "tensorflow.math.floor",
        solving.log: "tensorflow.math.log",
        solving.exp: "tensorflow.math.exp",
        Sqrt: "tensorflow.math.sqrt",
        solving.cos: "tensorflow.math.cos",
        solving.acos: "tensorflow.math.acos",
        solving.sin: "tensorflow.math.sin",
        solving.asin: "tensorflow.math.asin",
        solving.tan: "tensorflow.math.tan",
        solving.atan: "tensorflow.math.atan",
        solving.atan2: "tensorflow.math.atan2",
        # XXX Also may give NaN for complex results.
        solving.cosh: "tensorflow.math.cosh",
        solving.acosh: "tensorflow.math.acosh",
        solving.sinh: "tensorflow.math.sinh",
        solving.asinh: "tensorflow.math.asinh",
        solving.tanh: "tensorflow.math.tanh",
        solving.atanh: "tensorflow.math.atanh",

        solving.re: "tensorflow.math.real",
        solving.im: "tensorflow.math.imag",
        solving.arg: "tensorflow.math.angle",

        # XXX May raise error for ints and complexes
        solving.erf: "tensorflow.math.erf",
        solving.loggamma: "tensorflow.math.lgamma",

        solving.Eq: "tensorflow.math.equal",
        solving.Ne: "tensorflow.math.not_equal",
        solving.StrictGreaterThan: "tensorflow.math.greater",
        solving.StrictLessThan: "tensorflow.math.less",
        solving.LessThan: "tensorflow.math.less_equal",
        solving.GreaterThan: "tensorflow.math.greater_equal",

        solving.And: "tensorflow.math.logical_and",
        solving.Or: "tensorflow.math.logical_or",
        solving.Not: "tensorflow.math.logical_not",
        solving.Max: "tensorflow.math.maximum",
        solving.Min: "tensorflow.math.minimum",

        # Matrices
        solving.MatAdd: "tensorflow.math.add",
        solving.HadamardProduct: "tensorflow.math.multiply",
        solving.Trace: "tensorflow.linalg.trace",

        # XXX May raise error for integer matrices.
        solving.Determinant : "tensorflow.linalg.det",
    }

    _default_settings = dict(
        AbstractPythonCodePrinter._default_settings,
        tensorflow_version=None
    )

    def __init__(self, settings=None):
        super().__init__(settings)

        version = self._settings['tensorflow_version']
        if version is None and tensorflow:
            version = tensorflow.__version__
        self.tensorflow_version = version

    def _print_Function(self, expr):
        op = self.mapping.get(type(expr), None)
        if op is None:
            return super()._print_Basic(expr)
        children = [self._print(arg) for arg in expr.args]
        if len(children) == 1:
            return "%s(%s)" % (
                self._module_format(op),
                children[0]
            )
        else:
            return self._expand_fold_binary_op(op, children)

    _print_Expr = _print_Function
    _print_Application = _print_Function
    _print_MatrixExpr = _print_Function
    # TODO: a better class structure would avoid this mess:
    _print_Relational = _print_Function
    _print_Not = _print_Function
    _print_And = _print_Function
    _print_Or = _print_Function
    _print_HadamardProduct = _print_Function
    _print_Trace = _print_Function
    _print_Determinant = _print_Function

    def _print_Inverse(self, expr):
        op = self._module_format('tensorflow.linalg.inv')
        return "{}({})".format(op, self._print(expr.arg))

    def _print_Transpose(self, expr):
        version = self.tensorflow_version
        if version and version_tuple(version) < version_tuple('1.14'):
            op = self._module_format('tensorflow.matrix_transpose')
        else:
            op = self._module_format('tensorflow.linalg.matrix_transpose')
        return "{}({})".format(op, self._print(expr.arg))

    def _print_Derivative(self, expr):
        variables = expr.variables
        if any(isinstance(i, Iterable) for i in variables):
            raise NotImplementedError("derivation by multiple variables is not supported")
        def unfold(expr, args):
            if not args:
                return self._print(expr)
            return "%s(%s, %s)[0]" % (
                    self._module_format("tensorflow.gradients"),
                    unfold(expr, args[:-1]),
                    self._print(args[-1]),
                )
        return unfold(expr.expr, variables)

    def _print_Piecewise(self, expr):
        version = self.tensorflow_version
        if version and version_tuple(version) < version_tuple('1.0'):
            tensorflow_piecewise = "tensorflow.select"
        else:
            tensorflow_piecewise = "tensorflow.where"

        from solving.functions.elementary.piecewise import Piecewise
        e, cond = expr.args[0].args
        if len(expr.args) == 1:
            return '{}({}, {}, {})'.format(
                self._module_format(tensorflow_piecewise),
                self._print(cond),
                self._print(e),
                0)

        return '{}({}, {}, {})'.format(
            self._module_format(tensorflow_piecewise),
            self._print(cond),
            self._print(e),
            self._print(Piecewise(*expr.args[1:])))

    def _print_Pow(self, expr):
        # XXX May raise error for
        # int**float or int**complex or float**complex
        base, exp = expr.args
        if expr.exp == S.Half:
            return "{}({})".format(
                self._module_format("tensorflow.math.sqrt"), self._print(base))
        return "{}({}, {})".format(
            self._module_format("tensorflow.math.pow"),
            self._print(base), self._print(exp))

    def _print_MatrixBase(self, expr):
        tensorflow_f = "tensorflow.Variable" if expr.free_symbols else "tensorflow.constant"
        data = "["+", ".join(["["+", ".join([self._print(j) for j in i])+"]" for i in expr.tolist()])+"]"
        return "%s(%s)" % (
            self._module_format(tensorflow_f),
            data,
        )

    def _print_MatMul(self, expr):
        from solving.matrices.expressions import MatrixExpr
        mat_args = [arg for arg in expr.args if isinstance(arg, MatrixExpr)]
        args = [arg for arg in expr.args if arg not in mat_args]
        if args:
            return "%s*%s" % (
                self.parenthesize(Mul.fromiter(args), PRECEDENCE["Mul"]),
                self._expand_fold_binary_op(
                    "tensorflow.linalg.matmul", mat_args)
            )
        else:
            return self._expand_fold_binary_op(
                "tensorflow.linalg.matmul", mat_args)

    def _print_MatPow(self, expr):
        return self._expand_fold_binary_op(
            "tensorflow.linalg.matmul", [expr.base]*expr.exp)

    def _print_CodeBlock(self, expr):
        # TODO: is this necessary?
        ret = []
        for subexpr in expr.args:
            ret.append(self._print(subexpr))
        return "\n".join(ret)

    def _print_isnan(self, exp):
        return f'tensorflow.math.is_nan({self._print(*exp.args)})'

    def _print_isinf(self, exp):
        return f'tensorflow.math.is_inf({self._print(*exp.args)})'

    _module = "tensorflow"
    _einsum = "linalg.einsum"
    _add = "math.add"
    _transpose = "transpose"
    _ones = "ones"
    _zeros = "zeros"


def tensorflow_code(expr, **settings):
    printer = TensorflowPrinter(settings)
    return printer.doprint(expr)
