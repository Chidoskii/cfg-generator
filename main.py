import sys
import argparse
from pathlib import Path
from graphviz.backend import ExecutableNotFound

from lexer import Lexer
from parser import Parser
from cfg_builder import CFGBuilder
from visualizer import visualize_cfg



def generate_graph(source, optimize=True):
    """
    Parse source code, construct its CFG,
    and optionally optimize the graph.
    """
    tokens = Lexer(source).tokenize()
    function = Parser(tokens).parse_function()

    print("\nFunction:", function.signature)

    graph = CFGBuilder().build(function)

    print("\nBEFORE OPTIMIZATION")
    graph.print_graph()

    if optimize:
        graph.remove_empty_entries()
        graph.reduce_basic_blocks()

        print("\nAFTER OPTIMIZATION")
        graph.print_graph()

    errors = graph.validate()

    if errors:
        raise ValueError(
            "CFG validation failed:\n" +
            "\n".join(errors)
        )

    print("\nCFG validation passed.")

    print(
        "\nCyclomatic Complexity:",
        graph.cyclomatic_complexity()
    )

    return graph



def main():
    argument_parser = argparse.ArgumentParser(
        description=(
            "Generate a control flow graph "
            "from a C++ or Java function."
        )
    )

    argument_parser.add_argument(
        "source_file",
        help="Path to a source file containing one function."
    )

    argument_parser.add_argument(
        "-o", "--output",
        default="cfg_output",
        help="Output filename without extension."
    )

    argument_parser.add_argument(
        "--no-optimize",
        action="store_true",
        help="Skip CFG optimization."
    )

    args = argument_parser.parse_args()

    source_path = Path(args.source_file)

    try:
        source = source_path.read_text(encoding="utf-8")

        graph = generate_graph(
            source,
            optimize=not args.no_optimize
        )

        visualize_cfg(graph, args.output)

        print(
            f"\nVisualization generated: {args.output}.png"
        )

    except FileNotFoundError:
        print(
            f"Error: Source file not found: {source_path}",
            file=sys.stderr
        )
        return 1

    except UnicodeError as error:
        print(
            f"Error: Could not decode source file: {error}",
            file=sys.stderr
        )
        return 1

    except (SyntaxError, ValueError, TypeError) as error:
        print(
            f"Error: Could not generate CFG.\nDetails: {error}",
            file=sys.stderr
        )
        return 1

    except ExecutableNotFound:
        print(
            "Error: Graphviz executable 'dot' was not found.\n"
            "Install Graphviz and add its bin directory to PATH.",
            file=sys.stderr
        )
        return 1

    except OSError as error:
        print(
            f"Error: File or visualization operation failed: {error}",
            file=sys.stderr
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
