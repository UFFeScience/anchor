import sys

from fastmcp import FastMCP

from examples.commons.phylogenetic_subtrees.mcp.methods import fix_invalid_sequences, multiple_sequence_alignment_using_mafft, sequence_validator_, tree_construction


mcp = FastMCP(name="Tools for Parallel Identification of Frequent Subtrees in Phylogenetic Tree Ensembles")


@mcp.tool(
    name="sequence_validator",
    description="Function that checks if all sequences are valid proteins in FASTA format. Returns true if valid. False otherwise."
)
def sequence_validator(path_to_fasta_files: str) -> bool: 
    return sequence_validator_(path_to_fasta_files)


@mcp.tool(
    name="invalid_sequence_corrector",
    description=(
        "This function, starting from a directory containing FASTA files, corrects the FASTA files with invalid"
        " sequences and creates a new path with valid FASTA files. This function returns the new path of the FASTA files."
    )
)
def invalid_sequence_corrector(path_to_fasta_files: str) -> str:
    return fix_invalid_sequences(path_to_fasta_files)


@mcp.tool(
    name="multiple_sequence_alignment",
    description=(
        "Performs multiple sequence alignment from a directory containing validated FASTA files. "
        "Persists the resulting sequence alignment files in a specified path."
        # "The input is the path containing the FASTA files, and the output_path indicates where the results should be saved after the tool is executed."
        "The function's return value is a string indicating whether the function was executed successfully and the path where the results were saved."
    )
)
def multiple_sequence_alignment() -> str:
    return multiple_sequence_alignment_using_mafft()
# def multiple_sequence_alignment(path_to_fasta_files: str, output_path: str) -> str:
#     return multiple_sequence_alignment_using_mafft(path_to_fasta_files, output_path)


# @mcp.tool(
#     name="choice_of_evolutionary_model",
#     description="Choice of evolutionary model used in generating the phylogenetic tree"
# )
# def choice_of_evolutionary_model(file_path: str) -> None:
#     pass


@mcp.tool(
    name="tree_constructor",
    description=(
        "This function builds a phylogenetic tree from a path containing files with alignments. "
        # "The path parameter receives a path (string) with multiple sequence alignment."
        "It does not return any data, only a string containing the path with tree construction results. The user can view the final result at this specified path."
    )
)
def tree_constructor() -> str:
    return tree_construction()
# def tree_constructor(path: str) -> str:
#     return tree_construction(path)


@mcp.tool(
    name="identify_frequent_subtrees",
    description=(
       "This function finds frequent subtrees in Phylogenetic Tree Ensembles. "
       "As input, the trees must have been previously generated and be available in a path. "
       "It returns a path containing the frequent subtrees."
    )
)
def identify_frequent_subtrees() -> str:
    from examples.commons.phylogenetic_subtrees.mcp.methods import subtree_generation_and_similarity_calculation
    return subtree_generation_and_similarity_calculation()
    # return 'success'
# def identify_frequent_subtrees(path: str) -> str:
#     from examples.commons.phylogenetic_subtrees.mcp.methods import subtree_generation_and_similarity_calculation
#     return subtree_generation_and_similarity_calculation(path)


if __name__ == "__main__":
    print("--- Starting FastMCP server ---")
    # stdio transport is used by default.
    mcp.run()
