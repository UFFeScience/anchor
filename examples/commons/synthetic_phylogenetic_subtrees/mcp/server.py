from fastmcp import FastMCP

from examples.commons.synthetic_phylogenetic_subtrees.mcp.methods import (
    run_profiled_alignment,
    run_profiled_subtree_analyzer,
    run_profiled_tree_builder,
    run_profiled_validation_pipeline,
)
from examples.commons.synthetic_phylogenetic_subtrees.tool_profiles import TOOL_PROFILES


mcp = FastMCP(name="Synthetic Phylogenetic Subtree Tool Alternatives")


VALIDATION_DESCRIPTION = (
    "Function that checks if all sequences are valid proteins in FASTA format and correct the sequences if its necessary. This function returns the new path of the FASTA files."
)

ALIGNMENT_DESCRIPTION = (
    "Performs multiple sequence alignment from a directory containing validated FASTA files. "
    "Persists the resulting sequence alignment files in a specified path."
    "The function's return value is a string indicating whether the function was executed successfully and the path where the results were saved."
)

TREE_DESCRIPTION = (
    "This function builds a phylogenetic tree from a path containing files with alignments. "
    "It does not return any data, only a string containing the path with tree construction results. The user can view the final result at this specified path."
)

SUBTREE_DESCRIPTION = (
   "This function finds frequent subtrees in Phylogenetic Tree Ensembles. "
   "As input, the trees must have been previously generated and be available in a path. "
   "It returns a path containing the frequent subtrees."
)


def _profile_note(tool_name: str) -> str:
    profile = TOOL_PROFILES[tool_name]
    speed = "fast" if profile.sleep_seconds <= 0.1 else "moderate" if profile.sleep_seconds <= 0.2 else "slower"
    reliability = "lower reliability" if profile.behavior.startswith("mock_") else "higher reliability"
    return f"Tool name: {tool_name}. Tool characteristics: {speed}, {reliability}."


def _validator_description(tool_name: str) -> str:
    return VALIDATION_DESCRIPTION + _profile_note(tool_name)


def _alignment_description(tool_name: str) -> str:
    return ALIGNMENT_DESCRIPTION + _profile_note(tool_name)


def _tree_description(tool_name: str) -> str:
    return TREE_DESCRIPTION + _profile_note(tool_name)


def _subtree_description(tool_name: str) -> str:
    return SUBTREE_DESCRIPTION + _profile_note(tool_name)


@mcp.tool(name="biopython_sequence_validator", description=_validator_description("biopython_sequence_validator"))
def biopython_sequence_validator(path_to_fasta_files: str) -> str:
    return run_profiled_validation_pipeline("biopython_sequence_validator", path_to_fasta_files)


@mcp.tool(name="seqkit_sequence_validator", description=_validator_description("seqkit_sequence_validator"))
def seqkit_sequence_validator(path_to_fasta_files: str) -> str:
    return run_profiled_validation_pipeline("seqkit_sequence_validator", path_to_fasta_files)


@mcp.tool(name="emboss_sequence_validator", description=_validator_description("emboss_sequence_validator"))
def emboss_sequence_validator(path_to_fasta_files: str) -> str:
    return run_profiled_validation_pipeline("emboss_sequence_validator", path_to_fasta_files)


@mcp.tool(name="mafft_aligner", description=_alignment_description("mafft_aligner"))
def mafft_aligner() -> str:
    return run_profiled_alignment("mafft_aligner")


@mcp.tool(name="clustalw_aligner", description=_alignment_description("clustalw_aligner"))
def clustalw_aligner() -> str:
    return run_profiled_alignment("clustalw_aligner")


@mcp.tool(name="muscle_aligner", description=_alignment_description("muscle_aligner"))
def muscle_aligner() -> str:
    return run_profiled_alignment("muscle_aligner")


@mcp.tool(name="kalign_aligner", description=_alignment_description("kalign_aligner"))
def kalign_aligner() -> str:
    return run_profiled_alignment("kalign_aligner")


@mcp.tool(
    name="biopython_neighbor_joining_tree_builder",
    description=_tree_description("biopython_neighbor_joining_tree_builder"),
)
def biopython_neighbor_joining_tree_builder() -> str:
    return run_profiled_tree_builder("biopython_neighbor_joining_tree_builder")


@mcp.tool(name="fasttree_tree_builder", description=_tree_description("fasttree_tree_builder"))
def fasttree_tree_builder() -> str:
    return run_profiled_tree_builder("fasttree_tree_builder")


@mcp.tool(name="iqtree_tree_builder", description=_tree_description("iqtree_tree_builder"))
def iqtree_tree_builder() -> str:
    return run_profiled_tree_builder("iqtree_tree_builder")


@mcp.tool(name="raxml_tree_builder", description=_tree_description("raxml_tree_builder"))
def raxml_tree_builder() -> str:
    return run_profiled_tree_builder("raxml_tree_builder")


@mcp.tool(name="anchor_subtree_miner", description=_subtree_description("anchor_subtree_miner"))
def anchor_subtree_miner() -> str:
    return run_profiled_subtree_analyzer("anchor_subtree_miner")


@mcp.tool(name="dendropy_subtree_miner", description=_subtree_description("dendropy_subtree_miner"))
def dendropy_subtree_miner() -> str:
    return run_profiled_subtree_analyzer("dendropy_subtree_miner")


@mcp.tool(name="ete_subtree_miner", description=_subtree_description("ete_subtree_miner"))
def ete_subtree_miner() -> str:
    return run_profiled_subtree_analyzer("ete_subtree_miner")


@mcp.tool(name="treepattern_subtree_miner", description=_subtree_description("treepattern_subtree_miner"))
def treepattern_subtree_miner() -> str:
    return run_profiled_subtree_analyzer("treepattern_subtree_miner")


if __name__ == "__main__":
    mcp.run()
