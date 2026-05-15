import shutil
import json
from typing import Optional
from Bio import AlignIO, Phylo, SeqIO
from Bio.Phylo.TreeConstruction import DistanceCalculator, DistanceTreeConstructor
import os
from pathlib import Path

INPUT_PATH = 'testset' 
OUTPUT_FORMAT = 'nexus'
if OUTPUT_FORMAT == 'nexus':
    EXTENTION_FORMAT = 'nexus'
elif OUTPUT_FORMAT == 'nwk':
    EXTENTION_FORMAT = 'nwk'
else:
    raise ValueError(f"Unsupported output format: {OUTPUT_FORMAT}")

EXAMPLE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = EXAMPLE_DIR / "data" / "input"
DATA_OUTPUT_PATH = EXAMPLE_DIR / "data" / "output"
GENERAL_DIR = DATA_OUTPUT_PATH
GENERAL_DIR.mkdir(parents=True, exist_ok=True)


def _does_this_path_exist(path) -> bool:
    p = Path(path)
    return p.is_dir()


def _does_this_path_exist_str(path) -> Optional[str]:
    if not _does_this_path_exist(path):
        return f"The path {path} does not exist. Are you sure about this path?"
    return None


def clean_Trees():
    dir_Trees = os.path.join(DATA_OUTPUT_PATH,'Trees')
    file_trees = os.listdir(dir_Trees)

    for name_file_trees in file_trees:
        path_trees = os.path.join(dir_Trees,name_file_trees)
        if name_file_trees != ".gitkeep":
            os.remove(path_trees)

def clean_tmp():
    dir_tmp = os.path.join(DATA_OUTPUT_PATH,'tmp')
    files_tmp = os.listdir(dir_tmp)

    for name_file_tmp in files_tmp:
        path_tmp = os.path.join(dir_tmp,name_file_tmp)
        if name_file_tmp != ".gitkeep":
            os.remove(path_tmp)

def clean_NoPipe():
    dir_NoPipe = os.path.join(DATA_PATH, INPUT_PATH)

    for file_name in os.listdir(dir_NoPipe):
        if 'NoPipe' in file_name:
            file_path = os.path.join(dir_NoPipe, file_name)
            os.remove(file_path)


def validate_sequences(file_path):
    valid_characters = set('ACDEFGHIKLMNPQRSTVWY')
    try:
        with open(file_path, 'r') as file:
            for line in file:
                if line.startswith('>'):
                    continue
                sequence = line.strip()
                if not set(sequence).issubset(valid_characters):
                    return False
    except FileNotFoundError:
        print(f"The file '{file_path}' was not found.")
        return False

    return True


def duplicate_names(file_path):
    name_count = {}
    try:
        for record in SeqIO.parse(file_path, 'fasta'):
            name = record.id
            name_count[name] = name_count.get(name, 0) + 1
            if name_count[name] > 1:
                return True
    except FileNotFoundError:
        print(f"The file '{file_path}' was not found.")
        return False

    return False


def remove_pipe(original_file_path: str, new_file_path: str, file_name) -> str:
    sequences = list(SeqIO.parse(original_file_path, "fasta"))
    unique_sequences = {}
    for sequence in sequences:
        if str(sequence.seq) not in unique_sequences:
            unique_sequences[str(sequence.seq)] = sequence
    unique_sequences_list = list(unique_sequences.values())
    output_file_tmp = os.path.join(new_file_path,f'{file_name}_NoPipe')
    SeqIO.write(unique_sequences_list, output_file_tmp, "fasta")
    return output_file_tmp





def clean_dir(path_clean):
    if(os.path.exists(path_clean)):
        for name in os.listdir(path_clean):
            if(name != ".gitkeep"):
                file_path = os.path.join(path_clean, name)
                os.remove(file_path)
        shutil.rmtree(path_clean)


def clean_files():
    dir_tmp = os.path.join(DATA_OUTPUT_PATH) 
    tmp_files = os.listdir(dir_tmp)
    for name_file in tmp_files:
        if name_file != ".gitkeep":
            os.remove(os.path.join(dir_tmp,name_file))


####################################


def clean():
    clean_NoPipe()
    clean_tmp()
    clean_Trees()
    clean_files()


def sequence_validator_(path_to_fasta_files: str) -> bool:
    r =  _does_this_path_exist_str(path_to_fasta_files)
    if r:
        return r

    files = os.listdir(path_to_fasta_files)
    is_valid = True
    for file_name in files:
        file_path = os.path.join(path_to_fasta_files, file_name)
        is_valid = not(duplicate_names(file_path)) and validate_sequences(file_path)
        if not is_valid:
            return False
    return is_valid


def fix_invalid_sequences(path_to_fasta_files: str) -> str:
    r =  _does_this_path_exist_str(path_to_fasta_files)
    if r:
        return r

    files = os.listdir(path_to_fasta_files)
    new_path_to_fasta_files = GENERAL_DIR / 'validated-files'
    os.makedirs(new_path_to_fasta_files, exist_ok=True)
    for file_name in files:
        current_file_path = os.path.join(path_to_fasta_files, file_name)
        remove_pipe(current_file_path, new_path_to_fasta_files, file_name)

    return f'The new path with validated FASTA files is {new_path_to_fasta_files}.'


def multiple_sequence_alignment_using_mafft(output_path: str = None) -> str:
    path_to_fasta_files = GENERAL_DIR / 'validated-files'
    output_path = GENERAL_DIR / 'align'
    output_path.mkdir(parents=True, exist_ok=True)

    r =  _does_this_path_exist_str(path_to_fasta_files)
    if r:
        return r
    
    r =  _does_this_path_exist_str(output_path)
    if r:
        return r

    import shutil
    files = os.listdir(path_to_fasta_files)
    for file_name in files:
        file_path = os.path.join(path_to_fasta_files, file_name)
        output_file_path_aln = os.path.join(output_path,f'{Path(file_name).stem}.aln')
        tree_file_path = os.path.join(path_to_fasta_files,f'{Path(file_name).stem}.tree')
        new_tree_file_path = os.path.join(output_path,f'{Path(file_name).stem}.dnd')

        import subprocess
        cmd = ["mafft", "--auto", "--clustalout", "--treeout", file_path]
        with open(output_file_path_aln, "w") as out_file:
            subprocess.run(cmd, stdout=out_file, check=True)

        print(tree_file_path)
        print(new_tree_file_path)
        shutil.move(tree_file_path, new_tree_file_path)

    return 'The sequences were successfully aligned.'


def evolutionary_model_selection():
    pass


def tree_construction(output_format: str = 'nexus') -> str:
    aln_path = GENERAL_DIR / 'align'

    r =  _does_this_path_exist_str(aln_path)
    if r:
        return r
    
    files = os.listdir(aln_path)
    for file_name in files:
        suffix = Path(file_name).suffix
        if suffix == ".aln":
            file_path = os.path.join(aln_path, file_name)
            with open(file_path, "r") as handle:
                alignment = AlignIO.read(handle, "clustal")

            calculator = DistanceCalculator('identity') 
            distance_matrix = calculator.get_distance(alignment)

            constructor = DistanceTreeConstructor() 
            tree = constructor.nj(distance_matrix)

            path_out_tree = os.path.join(aln_path,f'tree_{Path(file_name).stem}.{output_format}')
            Phylo.write(tree, path_out_tree, output_format)

    return f'The phylogenetic tree was successfully constructed; you can find the files at path={aln_path}.'


def subtree_generation_and_similarity_calculation(path = None, data_format: str = "nexus") -> str:
    path = GENERAL_DIR / 'align'

    r =  _does_this_path_exist_str(path)
    if r:
        return r 

    def sub_tree(path, name_subtree):
        tree = Phylo.read(f"{path}/{name_subtree}",data_format)
        name_subtree = name_subtree.rsplit(".", 1)[0]

        row_subtree = []

        for clade in tree.find_clades():
            subtree = Phylo.BaseTree.Tree(clade)
            if subtree.count_terminals() > 1:
                filepath_out = os.path.join(path,f'{name_subtree}_{clade.name}.{data_format}')
                Phylo.write(subtree, filepath_out, data_format)        
                row_subtree.append(filepath_out)
                
        return row_subtree 
    

    files = os.listdir(path)

    matriz_subtree = []

    for filename in files:
        if Path(filename).suffix == f".{data_format}":
            file_path = os.path.join(path,filename)
            matriz_subtree.append(sub_tree(path, filename))

    max_columns = max(len(row) for row in matriz_subtree)
    max_rows = len(matriz_subtree)

    def preencher_matriz(matriz, valor_preenchimento):
        for row in matriz:
            while len(row) < max_columns:
                row.append(valor_preenchimento)

        return matriz

    # print(max_rows, max_columns)

    matriz_subtree = preencher_matriz(matriz_subtree, None)

    # for linha in matriz_subtree:
    #     print(linha)

    def grade_maf(path_1, path_2):
        if(path_1 is None or path_2 is None):
            return -1      
        grau = 0

        subtree_1 = Phylo.read(path_1, data_format)
        subtree_2 = Phylo.read(path_2, data_format)

        list_1 = [i.name for i in subtree_1.get_terminals()]
        list_2 = [i.name for i in subtree_2.get_terminals()]

        sorted_list1 = sorted(list_1)
        sorted_list2 = sorted(list_2)
        
        for i in range(len(list_1)):
            for j in range(len(list_2)):
                if sorted_list1[i] == sorted_list2[j]:
                    grau += 1
        return grau

    dict_maf_database = {}

    def fill_dict(dict, max_columns):
        for i in range(max_columns):
            dict[i+1] = {}

        return dict_maf_database

    dict_maf_database = fill_dict(dict_maf_database,max_columns)
    # print(dict_maf_database)


    max_maf = 0
    for i in range(max_rows):
        for j in range(max_columns):
            dict_aux = {}
            for k in range(max_rows):
                for l in range(max_columns): 
                    if i != k:
                        if max_maf <= grade_maf(matriz_subtree[i][j],matriz_subtree[k][l]):
                            max_maf = grade_maf(matriz_subtree[i][j],matriz_subtree[k][l])

                        g_maf = grade_maf(matriz_subtree[i][j], matriz_subtree[k][l])
                        if g_maf is not False and g_maf >= 1:
                            if g_maf not in dict_maf_database:
                                dict_maf_database[g_maf] = {}
                            if matriz_subtree[i][j] not in dict_maf_database[g_maf]:
                                dict_maf_database[g_maf][matriz_subtree[i][j]] = []
                            dict_maf_database[g_maf][matriz_subtree[i][j]].append(matriz_subtree[k][l])

    # print(max_maf)

    # for i, j in dict_maf_database.items():
    #     print(i,j)

    filename = GENERAL_DIR / 'frequent-subtrees.json'
    # Open the file in write mode ('w') and use json.dump() to save the data
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(dict_maf_database, f, ensure_ascii=False, indent=4)

    return f"Frequent subtrees successfully found. Result persisted on path={filename}."
