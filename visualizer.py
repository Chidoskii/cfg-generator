from graphviz import Digraph


def visualize_cfg(graph, filename="cfg_output"):
    dot = Digraph("ControlFlowGraph", format="png")
    dot.attr(rankdir="TB")
    dot.attr("node", fontname="Arial")

    for node_id, statements in graph.nodes.items():
        node_type = graph.node_types.get(node_id, "statement")

        if node_type == "decision":
            shape, color = "diamond", "lightyellow"
        elif node_type == "return":
            shape, color = "box", "lightblue"
        elif node_type == "exit":
            shape, color = "oval", "lightgray"
        else:
            shape, color = "box", "white"

        dot.node(
            str(node_id),
            label=f"{node_id}: {statements}",
            shape=shape,
            style="filled",
            fillcolor=color
        )

    for source, target, label in graph.edges:
        color = {
            "True": "green",
            "False": "red"
        }.get(label, "black")

        dot.edge(
            str(source),
            str(target),
            label=label,
            color=color
        )

    output_path = dot.render(
        filename=filename,
        cleanup=False
    )

    print(f"\nCFG visualization saved to: {output_path}")
    return output_path
