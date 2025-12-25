"""Stan lexer for Rosettes.

Thread-safe regex-based tokenizer for Stan probabilistic programming language.
"""

import re

from bengal.rendering.rosettes._types import TokenType
from bengal.rendering.rosettes.lexers._base import PatternLexer, Rule

__all__ = ["StanLexer"]

_BLOCKS = (
    "functions",
    "data",
    "transformed data",
    "parameters",
    "transformed parameters",
    "model",
    "generated quantities",
)

_KEYWORDS = (
    "break",
    "continue",
    "else",
    "for",
    "if",
    "in",
    "print",
    "reject",
    "return",
    "while",
    "profile",
    "target",
)

_TYPES = (
    "int",
    "real",
    "vector",
    "simplex",
    "unit_vector",
    "ordered",
    "positive_ordered",
    "row_vector",
    "matrix",
    "cholesky_factor_corr",
    "cholesky_factor_cov",
    "corr_matrix",
    "cov_matrix",
    "complex",
    "complex_vector",
    "complex_row_vector",
    "complex_matrix",
    "array",
    "tuple",
    "void",
)

_DISTRIBUTIONS = (
    "normal",
    "bernoulli",
    "binomial",
    "poisson",
    "exponential",
    "gamma",
    "beta",
    "uniform",
    "cauchy",
    "student_t",
    "lognormal",
    "chi_square",
    "inv_chi_square",
    "inv_gamma",
    "weibull",
    "pareto",
    "gumbel",
    "logistic",
    "double_exponential",
    "dirichlet",
    "multi_normal",
    "multi_normal_cholesky",
    "multinomial",
    "categorical",
    "ordered_logistic",
    "neg_binomial",
    "beta_binomial",
    "hypergeometric",
    "von_mises",
    "wishart",
    "inv_wishart",
    "lkj_corr",
    "lkj_corr_cholesky",
)

_FUNCTIONS = (
    "abs",
    "acos",
    "acosh",
    "asin",
    "asinh",
    "atan",
    "atan2",
    "atanh",
    "cbrt",
    "ceil",
    "cos",
    "cosh",
    "erf",
    "erfc",
    "exp",
    "exp2",
    "expm1",
    "fabs",
    "floor",
    "lgamma",
    "log",
    "log10",
    "log1p",
    "log2",
    "round",
    "sin",
    "sinh",
    "sqrt",
    "tan",
    "tanh",
    "tgamma",
    "trunc",
    "dot_product",
    "columns_dot_product",
    "rows_dot_product",
    "fma",
    "multiply_log",
    "lmultiply",
    "log1m",
    "log1p_exp",
    "log1m_exp",
    "log_diff_exp",
    "log_mix",
    "log_sum_exp",
    "log_inv_logit",
    "logit",
    "inv_logit",
    "inv_cloglog",
    "cloglog",
    "Phi",
    "Phi_approx",
    "inv_Phi",
    "binary_log_loss",
    "owens_t",
    "inc_beta",
    "lbeta",
    "tgamma",
    "lgamma",
    "digamma",
    "trigamma",
    "lmgamma",
    "gamma_p",
    "gamma_q",
    "binomial_coefficient_log",
    "choose",
    "bessel_first_kind",
    "bessel_second_kind",
    "modified_bessel_first_kind",
    "modified_bessel_second_kind",
    "falling_factorial",
    "lchoose",
    "log_falling_factorial",
    "rising_factorial",
    "log_rising_factorial",
    "fmin",
    "fmax",
    "fdim",
    "fmod",
    "hypot",
    "min",
    "max",
    "sum",
    "prod",
    "log_sum_exp",
    "mean",
    "variance",
    "sd",
    "distance",
    "squared_distance",
    "dims",
    "num_elements",
    "rows",
    "cols",
    "size",
    "rep_vector",
    "rep_row_vector",
    "rep_matrix",
    "rep_array",
    "append_col",
    "append_row",
    "block",
    "col",
    "row",
    "diagonal",
    "diag_matrix",
    "sub_col",
    "sub_row",
    "head",
    "tail",
    "segment",
    "inverse",
    "inverse_spd",
    "cholesky_decompose",
    "eigenvalues_sym",
    "eigenvectors_sym",
    "qr_Q",
    "qr_R",
    "svd_U",
    "svd_V",
    "softmax",
    "log_softmax",
    "cumulative_sum",
    "sort_asc",
    "sort_desc",
    "sort_indices_asc",
    "sort_indices_desc",
    "rank",
)


def _classify_word(match: re.Match[str]) -> TokenType:
    word = match.group(0)
    if word in _BLOCKS:
        return TokenType.KEYWORD_DECLARATION
    if word in _KEYWORDS:
        return TokenType.KEYWORD
    if word in _TYPES:
        return TokenType.KEYWORD_TYPE
    if word in _DISTRIBUTIONS:
        return TokenType.NAME_FUNCTION
    if word in _FUNCTIONS:
        return TokenType.NAME_BUILTIN
    return TokenType.NAME


class StanLexer(PatternLexer):
    """Stan lexer. Thread-safe."""

    name = "stan"
    aliases = ()
    filenames = ("*.stan",)
    mimetypes = ("text/x-stan",)

    _WORD_PATTERN = r"\b[a-zA-Z_][a-zA-Z0-9_]*\b"

    rules = (
        # Block declarations
        Rule(
            re.compile(
                r"\b(?:functions|data|transformed\s+data|parameters|transformed\s+parameters|model|generated\s+quantities)\b"
            ),
            TokenType.KEYWORD_DECLARATION,
        ),
        # Comments
        Rule(re.compile(r"//.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        Rule(re.compile(r"/\*[\s\S]*?\*/"), TokenType.COMMENT_MULTILINE),
        Rule(re.compile(r"#.*$", re.MULTILINE), TokenType.COMMENT_SINGLE),
        # Strings
        Rule(re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), TokenType.STRING),
        # Numbers
        Rule(re.compile(r"\d+\.\d*(?:[eE][+-]?\d+)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\.\d+(?:[eE][+-]?\d+)?"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+[eE][+-]?\d+"), TokenType.NUMBER_FLOAT),
        Rule(re.compile(r"\d+"), TokenType.NUMBER_INTEGER),
        # Sampling statement
        Rule(re.compile(r"~"), TokenType.OPERATOR),
        # Constraints
        Rule(re.compile(r"<(?:lower|upper)\s*="), TokenType.OPERATOR),
        # Keywords/names
        Rule(re.compile(_WORD_PATTERN), _classify_word),
        # Operators
        Rule(re.compile(r"<-|->"), TokenType.OPERATOR),
        Rule(re.compile(r"&&|\|\||==|!=|<=|>=|<|>"), TokenType.OPERATOR),
        Rule(re.compile(r"\+=|-=|\*=|/=|\.="), TokenType.OPERATOR),
        Rule(re.compile(r"\.?\*|\.?/|\.\^|'"), TokenType.OPERATOR),
        Rule(re.compile(r"[+\-*/%^!<>=?:]"), TokenType.OPERATOR),
        # Punctuation
        Rule(re.compile(r"[()[\]{}:;,|]"), TokenType.PUNCTUATION),
        # Whitespace
        Rule(re.compile(r"\s+"), TokenType.WHITESPACE),
    )
