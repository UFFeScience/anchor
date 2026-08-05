import os
import time

from fastmcp import FastMCP

from examples.commons.complex_phylogenetic_subtree.mcp.methods import (
    fix_invalid_sequences,
    multiple_sequence_alignment_using_mafft,
    sequence_validator_,
    subtree_generation_and_similarity_calculation,
    tree_construction,
)


mcp = FastMCP(name="Tools for Parallel Identification of Frequent Subtrees in Phylogenetic Tree Ensembles")


def _sleep(seconds: float) -> None:
    scale = float(os.getenv("COMPLEX_PHYLO_TIME_SCALE", os.getenv("SYNTHETIC_PHYLO_TIME_SCALE", "1.0")))
    time.sleep(seconds * scale)


def _run(seconds: float, operation, failure_message: str | None = None):
    # _sleep(seconds)
    time.sleep(seconds)
    if failure_message:
        raise RuntimeError(failure_message)
    return operation()


def _validator_description(tool_name: str, profile: str) -> str:
    return (
        "Function that checks if all sequences are valid proteins in FASTA format. Returns true if valid. False otherwise. "
        f"This is an alternative validation tool named {tool_name}; profile: {profile}."
    )


def _corrector_description(tool_name: str, profile: str) -> str:
    return (
        "This function, starting from a directory containing FASTA files, corrects the FASTA files with invalid"
        " sequences and creates a new path with valid FASTA files. This function returns the new path of the FASTA files. "
        f"This is an alternative correction tool named {tool_name}; profile: {profile}."
    )


def _alignment_description(tool_name: str, profile: str) -> str:
    return (
        "Performs multiple sequence alignment from a directory containing validated FASTA files. "
        "Persists the resulting sequence alignment files in a specified path."
        "The function's return value is a string indicating whether the function was executed successfully and the path where the results were saved. "
        f"This is an alternative alignment tool named {tool_name}; profile: {profile}."
    )


def _tree_description(tool_name: str, profile: str) -> str:
    return (
        "This function builds a phylogenetic tree from a path containing files with alignments. "
        "It does not return any data, only a string containing the path with tree construction results. The user can view the final result at this specified path. "
        f"This is an alternative tree construction tool named {tool_name}; profile: {profile}."
    )


def _subtree_description(tool_name: str, profile: str) -> str:
    return (
        "This function finds frequent subtrees in Phylogenetic Tree Ensembles. "
        "As input, the trees must have been previously generated and be available in a path. "
        "It returns a path containing the frequent subtrees. "
        f"This is an alternative subtree analysis tool named {tool_name}; profile: {profile}."
    )


@mcp.tool(
    name="sequence_validator",
    description=_validator_description("sequence_validator", "moderate speed, reliable"),
)
def sequence_validator(path_to_fasta_files: str) -> bool:
    return _run(2, lambda: sequence_validator_(path_to_fasta_files))


# @mcp.tool(
#     name="seqkit_sequence_validator",
#     description=_validator_description("seqkit_sequence_validator", "fast, reliable"),
# )
# def seqkit_sequence_validator(path_to_fasta_files: str) -> bool:
#     return _run(0.06, lambda: sequence_validator_(path_to_fasta_files))


# @mcp.tool(
#     name="emboss_sequence_validator",
#     description=_validator_description("emboss_sequence_validator", "fast, lower reliability in this environment"),
# )
# def emboss_sequence_validator(path_to_fasta_files: str) -> bool:
#     return _run(0.08, lambda: sequence_validator_(path_to_fasta_files), "EMBOSS validator failed during execution.")


@mcp.tool(
    name="invalid_sequence_corrector",
    description=_corrector_description("invalid_sequence_corrector", "moderate speed, reliable"),
)
def invalid_sequence_corrector(path_to_fasta_files: str) -> str:
    return _run(8, lambda: fix_invalid_sequences(path_to_fasta_files))


# @mcp.tool(
#     name="fast_invalid_sequence_corrector",
#     description=_corrector_description("fast_invalid_sequence_corrector", "fast, reliable"),
# )
# def fast_invalid_sequence_corrector(path_to_fasta_files: str) -> str:
#     return _run(0.08, lambda: fix_invalid_sequences(path_to_fasta_files))


# @mcp.tool(
#     name="emboss_invalid_sequence_corrector",
#     description=_corrector_description("emboss_invalid_sequence_corrector", "fast, lower reliability in this environment"),
# )
# def emboss_invalid_sequence_corrector(path_to_fasta_files: str) -> str:
#     return _run(0.10, lambda: fix_invalid_sequences(path_to_fasta_files), "EMBOSS corrector failed during execution.")


# @mcp.tool(
#     name="multiple_sequence_alignment",
#     description=_alignment_description("multiple_sequence_alignment", "moderate speed, reliable"),
# )
# def multiple_sequence_alignment() -> str:
#     return _run(0.20, multiple_sequence_alignment_using_mafft)


@mcp.tool(
    name="mafft_sequence_alignment",
    description=_alignment_description("mafft_sequence_alignment", "moderate speed, moderate reliability"),
)
def mafft_sequence_alignment() -> str:
    return _run(10, multiple_sequence_alignment_using_mafft) # "mafft alignment failed during execution."


@mcp.tool(
    name="muscle_sequence_alignment",
    description=_alignment_description("muscle_sequence_alignment", "slower, reliable"),
)
def muscle_sequence_alignment() -> str:
    return _run(20, multiple_sequence_alignment_using_mafft)


@mcp.tool(
    name="clustalw_sequence_alignment",
    description=_alignment_description("clustalw_sequence_alignment", "fast, moderate reliability"),
)
def clustalw_sequence_alignment() -> str:
    return _run(5, multiple_sequence_alignment_using_mafft)


# @mcp.tool(
#     name="tree_constructor",
#     description=_tree_description("tree_constructor", "moderate speed, reliable"),
# )
# def tree_constructor() -> str:
#     return _run(0.15, tree_construction)


@mcp.tool(
    name="fasttree_constructor",
    description=_tree_description("fasttree_constructor", "fast, moderate realibility"),
)
def fasttree_constructor() -> str:
    return _run(5, tree_construction) # "fasttree construction failed during execution."


@mcp.tool(
    name="iqtree_constructor",
    description=_tree_description("iqtree_constructor", "moderate speed, reliable"),
)
def iqtree_constructor() -> str:
    return _run(15, tree_construction)


@mcp.tool(
    name="raxml_constructor",
    description=_tree_description("raxml_constructor", "fast, lower reliability"),
)
def raxml_constructor() -> str:
    return _run(8, tree_construction)


# @mcp.tool(
#     name="identify_frequent_subtrees",
#     description=_subtree_description("identify_frequent_subtrees", "fast, reliable"),
# )
# def identify_frequent_subtrees() -> str:
#     return _run(0.12, subtree_generation_and_similarity_calculation)


@mcp.tool(
    name="dendropy_identify_frequent_subtrees",
    description=_subtree_description("dendropy_identify_frequent_subtrees", "moderate speed, reliable"),
)
def dendropy_identify_frequent_subtrees() -> str:
    return _run(15, subtree_generation_and_similarity_calculation)


@mcp.tool(
    name="ete_identify_frequent_subtrees",
    description=_subtree_description("ete_identify_frequent_subtrees", "fast, lower reliability"),
)
def ete_identify_frequent_subtrees() -> str:
    return _run(5, subtree_generation_and_similarity_calculation, "ETE subtree analysis failed during execution.")


@mcp.tool(
    name="treepattern_identify_frequent_subtrees",
    description=_subtree_description("treepattern_identify_frequent_subtrees", "slower, lower reliability"),
)
def treepattern_identify_frequent_subtrees() -> str:
    return _run(30, subtree_generation_and_similarity_calculation, "Tree-pattern mining failed during execution.")


if __name__ == "__main__":
    print("--- Starting FastMCP server ---")
    mcp.run()
