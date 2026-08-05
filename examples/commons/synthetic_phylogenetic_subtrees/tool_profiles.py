from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SyntheticToolProfile:
    name: str
    stage: str
    behavior: str
    sleep_seconds: float
    description: str
    failure_message: str | None = None


TOOL_PROFILES: dict[str, SyntheticToolProfile] = {
    "biopython_sequence_validator": SyntheticToolProfile(
        name="biopython_sequence_validator",
        stage="validation",
        behavior="real_validator",
        sleep_seconds=0.10,
        description=(
            "Biopython-based FASTA preparation tool for the validation stage. It checks protein FASTA parsing, "
            "amino-acid characters, duplicate records, and prepares a validated directory when cleanup is needed. "
            "Speed profile: moderate. Robustness profile: high for local FASTA parsing and identifier cleanup. "
            "Input: a directory containing protein FASTA files. Output: a message with the final validated FASTA "
            "directory path to use in the alignment stage."
        ),
    ),
    "seqkit_sequence_validator": SyntheticToolProfile(
        name="seqkit_sequence_validator",
        stage="validation",
        behavior="real_validator",
        sleep_seconds=0.06,
        description=(
            "SeqKit-style FASTA preparation tool for the validation stage. It performs fast file-level FASTA checks, "
            "duplicate removal, and sequence preparation for downstream alignment. Speed profile: fast. Robustness "
            "profile: good for simple FASTA cleanup and large batches. Input: a directory containing protein FASTA "
            "files. Output: a message with the final validated FASTA directory path to use in the alignment stage."
        ),
    ),
    "emboss_sequence_validator": SyntheticToolProfile(
        name="emboss_sequence_validator",
        stage="validation",
        behavior="mock_missing_binary",
        sleep_seconds=0.08,
        description=(
            "EMBOSS seqret-style FASTA preparation tool for the validation stage. It focuses on format-aware reading, "
            "sequence normalization, and conversion-oriented preparation before alignment. Speed profile: fast to "
            "moderate. Robustness profile: strong when format normalization is important. Input: a directory "
            "containing protein FASTA files. Output: a message with the final validated FASTA directory path to use "
            "in the alignment stage."
        ),
        failure_message="EMBOSS seqret execution failed: local binary is not configured for this environment.",
    ),
    "biopython_sequence_corrector": SyntheticToolProfile(
        name="biopython_sequence_corrector",
        stage="validation",
        behavior="real_corrector",
        sleep_seconds=0.12,
        description=(
            "Corrects and normalizes FASTA records using Biopython SeqIO-style parsing and writing. "
            "Best for local deduplication and sequence identifier normalization."
        ),
    ),
    "seqkit_sequence_deduplicator": SyntheticToolProfile(
        name="seqkit_sequence_deduplicator",
        stage="validation",
        behavior="real_corrector",
        sleep_seconds=0.08,
        description=(
            "Deduplicates and rewrites FASTA records using SeqKit-style sequence filtering. "
            "Best for fast preparation of validated FASTA batches."
        ),
    ),
    "emboss_seqret_normalizer": SyntheticToolProfile(
        name="emboss_seqret_normalizer",
        stage="validation",
        behavior="mock_missing_binary",
        sleep_seconds=0.10,
        description=(
            "Normalizes sequence files using EMBOSS seqret-style format conversion. "
            "Best when sequence files need format conversion before alignment."
        ),
        failure_message="EMBOSS seqret normalization failed: local binary is not configured for this environment.",
    ),
    "mafft_aligner": SyntheticToolProfile(
        name="mafft_aligner",
        stage="alignment",
        behavior="real_alignment",
        sleep_seconds=0.20,
        description=(
            "MAFFT-style multiple sequence alignment tool for protein FASTA files. Speed profile: moderate. Accuracy "
            "profile: high general-purpose alignment quality, especially when balancing speed and accuracy. Input: "
            "uses the validated FASTA directory produced by the validation stage. Output: a message with the alignment "
            "output path to use in tree construction."
        ),
    ),
    "clustalw_aligner": SyntheticToolProfile(
        name="clustalw_aligner",
        stage="alignment",
        behavior="mock_missing_binary",
        sleep_seconds=0.10,
        description=(
            "ClustalW-style progressive multiple sequence alignment tool for protein FASTA files. Speed profile: fast "
            "to moderate. Accuracy profile: classical baseline alignment quality; useful for smaller or standard "
            "datasets. Input: uses the validated FASTA directory produced by the validation stage. Output: a message "
            "with the alignment output path to use in tree construction."
        ),
        failure_message="ClustalW execution failed: local binary is not available in this environment.",
    ),
    "muscle_aligner": SyntheticToolProfile(
        name="muscle_aligner",
        stage="alignment",
        behavior="real_alignment",
        sleep_seconds=0.45,
        description=(
            "MUSCLE-style multiple sequence alignment tool for protein FASTA files. Speed profile: slower in this "
            "workflow. Accuracy profile: high, designed for accurate iterative alignments. Input: uses the validated "
            "FASTA directory produced by the validation stage. Output: a message with the alignment output path to "
            "use in tree construction."
        ),
    ),
    "kalign_aligner": SyntheticToolProfile(
        name="kalign_aligner",
        stage="alignment",
        behavior="real_alignment",
        sleep_seconds=0.15,
        description=(
            "Kalign-style progressive multiple sequence alignment tool. Speed profile: fast. Accuracy profile: good "
            "for scalable alignment where speed is important. Input: uses the validated FASTA directory produced by "
            "the validation stage. Output: a message with the alignment output path to use in tree construction."
        ),
    ),
    "biopython_neighbor_joining_tree_builder": SyntheticToolProfile(
        name="biopython_neighbor_joining_tree_builder",
        stage="tree_construction",
        behavior="real_tree",
        sleep_seconds=0.15,
        description=(
            "Biopython neighbor-joining tree construction tool. It builds distance-matrix trees from aligned protein "
            "sequences. Speed profile: moderate. Accuracy profile: suitable for lightweight local baseline trees, not "
            "a full maximum-likelihood search. Input: uses the alignment output directory. Output: a message with the "
            "tree output path to use in subtree analysis."
        ),
    ),
    "fasttree_tree_builder": SyntheticToolProfile(
        name="fasttree_tree_builder",
        stage="tree_construction",
        behavior="real_tree",
        sleep_seconds=0.08,
        description=(
            "FastTree-style tree construction tool. It builds approximately maximum-likelihood phylogenies from "
            "aligned protein sequences. Speed profile: fast. Accuracy profile: good scalable approximation, useful "
            "when speed matters more than exhaustive likelihood search. Input: uses the alignment output directory. "
            "Output: a message with the tree output path to use in subtree analysis."
        ),
    ),
    "iqtree_tree_builder": SyntheticToolProfile(
        name="iqtree_tree_builder",
        stage="tree_construction",
        behavior="mock_missing_binary",
        sleep_seconds=0.18,
        description=(
            "IQ-TREE-style tree construction tool. It targets model-aware maximum-likelihood phylogenetic inference. "
            "Speed profile: moderate to slow. Accuracy profile: high when model selection and likelihood-based "
            "inference are important. Input: uses the alignment output directory. Output: a message with the tree "
            "output path to use in subtree analysis."
        ),
        failure_message="IQ-TREE execution failed: local binary is not configured for this environment.",
    ),
    "raxml_tree_builder": SyntheticToolProfile(
        name="raxml_tree_builder",
        stage="tree_construction",
        behavior="mock_runtime_error",
        sleep_seconds=0.22,
        description=(
            "RAxML-style tree construction tool. It targets large-scale maximum-likelihood phylogenetic inference. "
            "Speed profile: slower. Accuracy profile: high for rigorous likelihood-based tree construction. Input: "
            "uses the alignment output directory. Output: a message with the tree output path to use in subtree "
            "analysis."
        ),
        failure_message="RAxML execution failed: runtime terminated before producing tree files.",
    ),
    "anchor_subtree_miner": SyntheticToolProfile(
        name="anchor_subtree_miner",
        stage="subtree_analysis",
        behavior="real_subtree",
        sleep_seconds=0.12,
        description=(
            "Anchor native subtree mining tool. It extracts frequent subtree patterns from generated phylogenetic "
            "tree files. Speed profile: fast. Robustness profile: high for the local Anchor tree output format. "
            "Input: uses the tree construction output directory. Output: a message with the final frequent-subtrees "
            "result path."
        ),
    ),
    "dendropy_subtree_miner": SyntheticToolProfile(
        name="dendropy_subtree_miner",
        stage="subtree_analysis",
        behavior="real_subtree",
        sleep_seconds=0.20,
        description=(
            "DendroPy-style subtree analysis tool. It parses phylogenetic tree files and extracts subtree structures "
            "using Python-native tree manipulation. Speed profile: moderate. Robustness profile: good for NEXUS and "
            "Newick-style tree processing. Input: uses the tree construction output directory. Output: a message with "
            "the final frequent-subtrees result path."
        ),
    ),
    "ete_subtree_miner": SyntheticToolProfile(
        name="ete_subtree_miner",
        stage="subtree_analysis",
        behavior="mock_format_error",
        sleep_seconds=0.14,
        description=(
            "ETE Toolkit-style subtree analysis tool. It traverses, annotates, and analyzes phylogenetic tree "
            "structures. Speed profile: fast to moderate. Robustness profile: strong for tree manipulation and "
            "annotation workflows. Input: uses the tree construction output directory. Output: a message with the "
            "final frequent-subtrees result path."
        ),
        failure_message="ETE Toolkit subtree analysis failed: unsupported tree encoding in the generated ensemble.",
    ),
    "treepattern_subtree_miner": SyntheticToolProfile(
        name="treepattern_subtree_miner",
        stage="subtree_analysis",
        behavior="mock_runtime_error",
        sleep_seconds=0.28,
        description=(
            "Tree-pattern mining tool for phylogenetic tree ensembles. It searches generated trees for repeated "
            "subtree structures across the ensemble. Speed profile: slower. Robustness profile: useful for exhaustive "
            "pattern-oriented subtree mining. Input: uses the tree construction output directory. Output: a message "
            "with the final frequent-subtrees result path."
        ),
        failure_message="Tree-pattern mining failed: search exceeded the configured synthetic execution budget.",
    ),
}


STAGE_TOOLS: dict[str, list[str]] = {
    "validation": [
        "biopython_sequence_validator",
        "seqkit_sequence_validator",
        "emboss_sequence_validator",
    ],
    "alignment": ["mafft_aligner", "clustalw_aligner", "muscle_aligner", "kalign_aligner"],
    "tree_construction": [
        "biopython_neighbor_joining_tree_builder",
        "fasttree_tree_builder",
        "iqtree_tree_builder",
        "raxml_tree_builder",
    ],
    "subtree_analysis": [
        "anchor_subtree_miner",
        "dendropy_subtree_miner",
        "ete_subtree_miner",
        "treepattern_subtree_miner",
    ],
}

TOOL_TO_STAGE = {
    tool_name: stage
    for stage, tool_names in STAGE_TOOLS.items()
    for tool_name in tool_names
}
