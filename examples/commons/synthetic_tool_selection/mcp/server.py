from fastmcp import FastMCP

from examples.commons.synthetic_tool_selection.simulator import default_input_path, run_synthetic_tool


mcp = FastMCP(name="Synthetic Tool Selection Benchmark")


@mcp.tool(
    name="fast_cleaner",
    description="Fast data cleaning tool. Same purpose as other cleaners; quicker but more failure-prone.",
)
def fast_cleaner(input_path: str = default_input_path()) -> str:
    return run_synthetic_tool("fast_cleaner", input_path)


@mcp.tool(
    name="balanced_cleaner",
    description="Balanced data cleaning tool. Same purpose as other cleaners; moderate runtime and reliability.",
)
def balanced_cleaner(input_path: str = default_input_path()) -> str:
    return run_synthetic_tool("balanced_cleaner", input_path)


@mcp.tool(
    name="strict_cleaner",
    description="Strict data cleaning tool. Same purpose as other cleaners; slower but most reliable.",
)
def strict_cleaner(input_path: str = default_input_path()) -> str:
    return run_synthetic_tool("strict_cleaner", input_path)


@mcp.tool(
    name="quick_feature_extractor",
    description="Quick feature extraction tool. Same purpose as other feature extractors; fast but less reliable.",
)
def quick_feature_extractor(input_path: str) -> str:
    return run_synthetic_tool("quick_feature_extractor", input_path)


@mcp.tool(
    name="robust_feature_extractor",
    description="Robust feature extraction tool. Same purpose as other feature extractors; slower but reliable.",
)
def robust_feature_extractor(input_path: str) -> str:
    return run_synthetic_tool("robust_feature_extractor", input_path)


@mcp.tool(
    name="experimental_feature_extractor",
    description="Experimental feature extraction tool. Same purpose as other feature extractors; unstable.",
)
def experimental_feature_extractor(input_path: str) -> str:
    return run_synthetic_tool("experimental_feature_extractor", input_path)


@mcp.tool(
    name="fast_scorer",
    description="Fast scoring tool. Same purpose as other scorers; quick but less reliable.",
)
def fast_scorer(input_path: str) -> str:
    return run_synthetic_tool("fast_scorer", input_path)


@mcp.tool(
    name="accurate_scorer",
    description="Accurate scoring tool. Same purpose as other scorers; slower but reliable.",
)
def accurate_scorer(input_path: str) -> str:
    return run_synthetic_tool("accurate_scorer", input_path)


@mcp.tool(
    name="unstable_scorer",
    description="Unstable scoring tool. Same purpose as other scorers; very fast but failure-prone.",
)
def unstable_scorer(input_path: str) -> str:
    return run_synthetic_tool("unstable_scorer", input_path)


if __name__ == "__main__":
    mcp.run()

