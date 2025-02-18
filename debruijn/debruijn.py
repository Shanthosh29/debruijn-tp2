#!/bin/env python3
# -*- coding: utf-8 -*-
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#    A copy of the GNU General Public License is available at
#    http://www.gnu.org/licenses/gpl-3.0.html

"""Perform assembly based on debruijn graph."""

import argparse
import os
import sys
from pathlib import Path
from networkx import (
    DiGraph,
    all_simple_paths,
    lowest_common_ancestor,
    has_path,
    random_layout,
    draw,
    spring_layout,
)
import matplotlib
from operator import itemgetter
import random

random.seed(9001)
from random import randint
import statistics
import textwrap
import matplotlib.pyplot as plt
from typing import Iterator, Dict, List

matplotlib.use("Agg")

__author__ = "Your Name"
__copyright__ = "Universite Paris Diderot"
__credits__ = ["Your Name"]
__license__ = "GPL"
__version__ = "1.0.0"
__maintainer__ = "Your Name"
__email__ = "your@email.fr"
__status__ = "Developpement"


def isfile(path: str) -> Path:  # pragma: no cover
    """Check if path is an existing file.

    :param path: (str) Path to the file

    :raises ArgumentTypeError: If file does not exist

    :return: (Path) Path object of the input file
    """
    myfile = Path(path)
    if not myfile.is_file():
        if myfile.is_dir():
            msg = f"{myfile.name} is a directory."
        else:
            msg = f"{myfile.name} does not exist."
        raise argparse.ArgumentTypeError(msg)
    return myfile


def get_arguments():  # pragma: no cover
    """Retrieves the arguments of the program.

    :return: An object that contains the arguments
    """
    # Parsing arguments
    parser = argparse.ArgumentParser(
        description=__doc__, usage="{0} -h".format(sys.argv[0])
    )
    parser.add_argument(
        "-i", dest="fastq_file", type=isfile, required=True, help="Fastq file"
    )
    parser.add_argument(
        "-k", dest="kmer_size", type=int, default=22, help="k-mer size (default 22)"
    )
    parser.add_argument(
        "-o",
        dest="output_file",
        type=Path,
        default=Path(os.curdir + os.sep + "contigs.fasta"),
        help="Output contigs in fasta file (default contigs.fasta)",
    )
    parser.add_argument(
        "-f", dest="graphimg_file", type=Path, help="Save graph as an image (png)"
    )
    return parser.parse_args()


def read_fastq(fastq_file: Path) -> Iterator[str]:
    """Extract reads from fastq files.

    :param fastq_file: (Path) Path to the fastq file.
    :return: A generator object that iterate the read sequences.
    """
    with open(fastq_file, 'r') as file:
        while True:
            # Read the 4 lines of each FASTQ entry
            identifier = file.readline().strip()
            if not identifier:  # End of file
                break
            sequence = file.readline().strip()
            file.readline()  # Skip the '+' line
            file.readline()  # Skip the quality score line
            
            yield sequence 
    pass


def cut_kmer(read: str, kmer_size: int) -> Iterator[str]:
    """Cut read into kmers of size kmer_size.

    :param read: (str) Sequence of a read.
    :return: A generator object that provides the kmers (str) of size kmer_size.
    """
    
    for i in range(len(read) - kmer_size + 1):
        yield read[i:i+kmer_size]
  
    pass

def build_kmer_dict(fastq_file: Path, kmer_size: int) -> Dict[str, int]:
    """Build a dictionnary object of all kmer occurrences in the fastq file

    :param fastq_file: (str) Path to the fastq file.
    :return: A dictionnary object that identify all kmer occurrences.
    """

    kmer_dict = {}
    for read in read_fastq(fastq_file):
        for kmer in cut_kmer(read, kmer_size):
            if kmer in kmer_dict:
                kmer_dict[kmer] += 1
            else:
                kmer_dict[kmer] = 1
    return kmer_dict

    pass


def build_graph(kmer_dict: Dict[str, int]) -> DiGraph:
    """Build the debruijn graph

    :param kmer_dict: A dictionnary object that identify all kmer occurrences.
    :return: A directed graph (nx) of all kmer substring and weight (occurrence).
    """
    graph = DiGraph()
    for kmer, weight in kmer_dict.items():
        prefix = kmer[:-1]
        suffix = kmer[1:]
        graph.add_edge(prefix, suffix, weight= weight )
    return graph

    pass


def remove_paths(
    graph: DiGraph,
    path_list: List[List[str]],
    delete_entry_node: bool,
    delete_sink_node: bool,
) -> DiGraph:
    """Remove a list of path in a graph. A path is set of connected node in
    the graph

    :param graph: (nx.DiGraph) A directed graph object
    :param path_list: (list) A list of path
    :param delete_entry_node: (boolean) True->We remove the first node of a path
    :param delete_sink_node: (boolean) True->We remove the last node of a path
    :return: (nx.DiGraph) A directed graph object
    """
    for path in path_list:
        if len(path) < 2:
            continue
        start = 0 if delete_entry_node else 1
        end = len(path) if delete_sink_node else len(path) - 1
        for node in path[start:end]:
            graph.remove_node(node)
    return graph


    pass


def select_best_path(
    graph: DiGraph,
    path_list: List[List[str]],
    path_length: List[int],
    weight_avg_list: List[float],
    delete_entry_node: bool = False,
    delete_sink_node: bool = False,
) -> DiGraph:
    """Select the best path between different paths

    :param graph: (nx.DiGraph) A directed graph object
    :param path_list: (list) A list of path
    :param path_length_list: (list) A list of length of each path
    :param weight_avg_list: (list) A list of average weight of each path
    :param delete_entry_node: (boolean) True->We remove the first node of a path
    :param delete_sink_node: (boolean) True->We remove the last node of a path
    :return: (nx.DiGraph) A directed graph object
    """


    best_path_index = max(range(len(path_list)), key=lambda i: (weight_avg_list[i], path_length[i]))
    best_path = path_list[best_path_index]

    paths_to_remove = path_list.copy()
    paths_to_remove.pop(best_path_index)

    return remove_paths(graph, paths_to_remove, delete_entry_node, delete_sink_node)

    pass


def path_average_weight(graph: DiGraph, path: List[str]) -> float:
    """Compute the weight of a path

    :param graph: (nx.DiGraph) A directed graph object
    :param path: (list) A path consist of a list of nodes
    :return: (float) The average weight of a path
    """
    return statistics.mean(
        [d["weight"] for (u, v, d) in graph.subgraph(path).edges(data=True)]
    )


def solve_bubble(graph: DiGraph, ancestor_node: str, descendant_node: str) -> DiGraph:
    """Explore and solve bubble issue

    :param graph: (nx.DiGraph) A directed graph object
    :param ancestor_node: (str) An upstream node in the graph
    :param descendant_node: (str) A downstream node in the graph
    :return: (nx.DiGraph) A directed graph object
    """


    paths = list(all_simple_paths(graph, ancestor_node, descendant_node))
    
    # If there's only one path or none, return the graph as is
    if len(paths) <= 1:
        return graph

    # Initialize variables to track the best path
    best_path = None
    best_weight = -1
    best_length = -1

    # Evaluate each path based on weight and length
    for path in paths:
        weight = path_average_weight(graph, path)
        length = len(path)

        # Determine if this path is better based on criteria
        if (weight > best_weight) or (weight == best_weight and length > best_length):
            best_path = path
            best_weight = weight
            best_length = length

    # Remove all paths except for the best one
    for path in paths:
        if path != best_path:
            graph.remove_nodes_from(path[1:-1])  # Remove intermediate nodes

    return graph
    pass


def simplify_bubbles(graph: DiGraph) -> DiGraph:
    """Detect and explode bubbles

    :param graph: (nx.DiGraph) A directed graph object
    :return: (nx.DiGraph) A directed graph object
    """
    # Create a list to hold nodes that need to be removed
    nodes_to_remove = []

    for node in graph.nodes():
        predecessors = list(graph.predecessors(node))
        
        # Check if the node has multiple predecessors
        if len(predecessors) > 1:
            # Find the lowest common ancestor of all predecessors
            lca = lowest_common_ancestor(graph, *predecessors)
            if lca is not None:
                # If an LCA exists, solve the bubble using this node
                for predecessor in predecessors:
                    if predecessor != lca:
                        graph = solve_bubble(graph, predecessor, node)

                # After processing, we can also check if we need to remove any edges
                paths = list(all_simple_paths(graph, lca, node))
                if paths:
                    best_path = max(paths, key=lambda p: path_average_weight(graph, p))
                    for path in paths:
                        if path != best_path:
                            # Mark intermediate nodes for removal
                            nodes_to_remove.extend(path[1:-1])  # Exclude start and end

    # Remove marked nodes from the graph after iteration
    graph.remove_nodes_from(set(nodes_to_remove))

    return graph
    pass


def solve_entry_tips(graph: DiGraph, starting_nodes: List[str]) -> DiGraph:
    """Remove entry tips

    :param graph: (nx.DiGraph) A directed graph object
    :param starting_nodes: (list) A list of starting nodes
    :return: (nx.DiGraph)  A directed graph object
    """

    # Create a list to hold nodes that need to be removed
    nodes_to_remove = []

    for node in starting_nodes:
        successors = list(graph.successors(node))
        
        # If the node has exactly one successor, check its predecessors
        if len(successors) == 1:
            successor = successors[0]
            predecessors = list(graph.predecessors(successor))
            
            # If the successor has multiple predecessors, we have an entry tip
            if len(predecessors) > 1:
                # Identify the best path from the node to its successor
                paths = list(all_simple_paths(graph, node, successor))
                if paths:
                    # Calculate the average weights for each path
                    path_weights = [path_average_weight(graph, path) for path in paths]
                    best_path_index = path_weights.index(max(path_weights))
                    best_path = paths[best_path_index]

                    # Mark all other paths for removal
                    for path in paths:
                        if path != best_path:
                            nodes_to_remove.extend(path[1:-1])  # Remove intermediate nodes

    # Remove marked nodes from the graph after iteration
    graph.remove_nodes_from(set(nodes_to_remove))

    return graph       
    pass


def solve_out_tips(graph: DiGraph, ending_nodes: List[str]) -> DiGraph:
    """Remove out tips

    :param graph: (nx.DiGraph) A directed graph object
    :param ending_nodes: (list) A list of ending nodes
    :return: (nx.DiGraph) A directed graph object
    """
    pass


def get_starting_nodes(graph: DiGraph) -> List[str]:
    """Get nodes without predecessors

    :param graph: (nx.DiGraph) A directed graph object
    :return: (list) A list of all nodes without predecessors
    """
    return [node for node in graph.nodes() if graph.in_degree(node) == 0]

    pass


def get_sink_nodes(graph: DiGraph) -> List[str]:
    """Get nodes without successors

    :param graph: (nx.DiGraph) A directed graph object
    :return: (list) A list of all nodes without successors
    """

    return [node for node in graph.nodes() if graph.out_degree(node) == 0]



    pass


def get_contigs(
    graph: DiGraph, starting_nodes: List[str], ending_nodes: List[str]
) -> List:
    """Extract the contigs from the graph

    :param graph: (nx.DiGraph) A directed graph object
    :param starting_nodes: (list) A list of nodes without predecessors
    :param ending_nodes: (list) A list of nodes without successors
    :return: (list) List of [contiguous sequence and their length]
    """

    contigs = []
    for start in starting_nodes:
        for end in ending_nodes:
            if has_path(graph, start, end):
                paths = list(all_simple_paths(graph, start, end))
                for path in paths:
                    contig = path[0]
                    for node in path[1:]:
                        contig += node[-1]
                    contigs.append([contig, len(contig)])
    return contigs
    pass


def save_contigs(contigs_list: List[str], output_file: Path) -> None:
    """Write all contigs in fasta format

    :param contig_list: (list) List of [contiguous sequence and their length]
    :param output_file: (Path) Path to the output file
    """

    with open(output_file, 'w') as f:
        for i, (contig, length) in enumerate(contigs_list):
            f.write(f">contig_{i} len={length}\n{contig}\n")
    pass


def draw_graph(graph: DiGraph, graphimg_file: Path) -> None:  # pragma: no cover
    """Draw the graph

    :param graph: (nx.DiGraph) A directed graph object
    :param graphimg_file: (Path) Path to the output file
    """
    fig, ax = plt.subplots()
    elarge = [(u, v) for (u, v, d) in graph.edges(data=True) if d["weight"] > 3]
    # print(elarge)
    esmall = [(u, v) for (u, v, d) in graph.edges(data=True) if d["weight"] <= 3]
    # print(elarge)
    # Draw the graph with networkx
    # pos=nx.spring_layout(graph)
    pos = nx.random_layout(graph)
    nx.draw_networkx_nodes(graph, pos, node_size=6)
    nx.draw_networkx_edges(graph, pos, edgelist=elarge, width=6)
    nx.draw_networkx_edges(
        graph, pos, edgelist=esmall, width=6, alpha=0.5, edge_color="b", style="dashed"
    )
    # nx.draw_networkx(graph, pos, node_size=10, with_labels=False)
    # save image
    plt.savefig(graphimg_file.resolve())


# ==============================================================
# Main program
# ==============================================================
def main() -> None:  # pragma: no cover
    
    #Main program function
    
    # Get arguments
    args = get_arguments()

    # Fonctions de dessin du graphe
    # A decommenter si vous souhaitez visualiser un petit
    # graphe
    # Plot the graph
    # if args.graphimg_file:
    #     draw_graph(graph, args.graphimg_file)


if __name__ == "__main__":  # pragma: no cover
    main()
