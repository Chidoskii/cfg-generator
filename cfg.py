class CFG:
    def __init__(self):
        self.nodes = {}
        self.node_types = {}
        self.edges = []
        self.next_id = 1
        self.entry_node = None

    def add_node(self, statements, node_type="statement"):
        node_id = self.next_id
        self.next_id += 1

        self.nodes[node_id] = statements
        self.node_types[node_id] = node_type

        return node_id

    def add_edge(self, source, target, label=""):
        self.edges.append((source, target, label))

    def print_graph(self):
        print("Vertices:")
        for node_id, statements in self.nodes.items():
            print(f"{node_id}: {statements}")

        print("\nEdges:")
        for source, target, label in self.edges:
            if label:
                print(f"({source}, {target}) [{label}]")
            else:
                print(f"({source}, {target})")

    
    
    def reduce_basic_blocks(self):
        """
        Merge consecutive statement nodes while
        preserving decision and control-flow nodes.
        """

        changed = True

        while changed:
            changed = False

            for source, target, label in list(self.edges):

                if label or source == target:
                    continue

                if source not in self.nodes or target not in self.nodes:
                    continue

                # Only merge ordinary statement nodes.
                if self.node_types[source] != "statement":
                    continue

                if self.node_types[target] != "statement":
                    continue

                outgoing = [
                    edge for edge in self.edges
                    if edge[0] == source
                ]

                incoming = [
                    edge for edge in self.edges
                    if edge[1] == target
                ]

                # Both nodes must form a straight-line path.
                if len(outgoing) != 1 or len(incoming) != 1:
                    continue

                # Combine statements.
                self.nodes[source] += "\n" + self.nodes[target]

                # Redirect outgoing edges from target.
                new_edges = []

                for edge_source, edge_target, edge_label in self.edges:

                    if edge_source == source and edge_target == target:
                        continue

                    if edge_source == target:
                        new_edges.append((
                            source,
                            edge_target,
                            edge_label
                        ))
                    else:
                        new_edges.append((
                            edge_source,
                            edge_target,
                            edge_label
                        ))

                self.edges = new_edges

                if self.entry_node == target:
                    self.entry_node = source

                del self.nodes[target]
                del self.node_types[target]

                changed = True
                break
    
    
    def remove_empty_entries(self):
        """
        Remove temporary entry nodes that have
        exactly one outgoing edge.
        """

        entry_types = {
            "FUNCTION_ENTRY",
            "WHILE_ENTRY",
            "FOR_ENTRY",
            "DO_ENTRY"
        }

        for node_id, text in list(self.nodes.items()):
            if text not in entry_types:
                continue

            outgoing = [
                edge for edge in self.edges
                if edge[0] == node_id
            ]

            if len(outgoing) != 1:
                continue

            successor = outgoing[0][1]

            if successor == node_id:
                continue

            # NEW: Preserve the CFG entry point.
            if self.entry_node == node_id:
                self.entry_node = successor

            new_edges = []

            for source, target, label in self.edges:
                if source == node_id:
                    continue

                if target == node_id:
                    new_edges.append((
                        source,
                        successor,
                        label
                    ))
                else:
                    new_edges.append((
                        source,
                        target,
                        label
                    ))

            self.edges = new_edges
            del self.nodes[node_id]
            del self.node_types[node_id]


    def cyclomatic_complexity(self):
        """
        Calculate McCabe's cyclomatic complexity.

        Assumes a connected CFG with a single
        entry and exit structure.
        """
        vertices = len(self.nodes)
        edges = len(self.edges)

        if vertices == 0:
            return 0

        return edges - vertices + 2

    
    def validate(self):
        """
        Validate the structural integrity of the CFG.

        Returns a list of errors.
        An empty list means validation passed.
        """
        errors = []

        entry = self.entry_node

        if entry is None:
            errors.append("CFG entry node is not defined")
            return errors

        if entry not in self.nodes:
            errors.append(
                f"CFG entry node {entry} does not exist"
            )
            return errors

        adjacency = {
            node: [] for node in self.nodes
        }

        reverse_adjacency = {
            node: [] for node in self.nodes
        }

        # Check edge references.
        for source, target, label in self.edges:
            if source not in self.nodes:
                errors.append(
                    f"Edge references missing source {source}"
                )
                continue

            if target not in self.nodes:
                errors.append(
                    f"Edge references missing target {target}"
                )
                continue

            adjacency[source].append(target)
            reverse_adjacency[target].append(source)


        def reachable(start, graph):
            visited = set()
            stack = [start]

            while stack:
                node = stack.pop()

                if node in visited:
                    continue

                visited.add(node)
                stack.extend(graph[node])

            return visited

        # All vertices should be reachable from entry.
        reachable_nodes = reachable(entry, adjacency)

        unreachable = set(self.nodes) - reachable_nodes

        if unreachable:
            errors.append(
                f"Unreachable vertices: {sorted(unreachable)}"
            )

        # Find EXIT.
        exit_nodes = [
            node for node, text in self.nodes.items()
            if text == "EXIT"
        ]

        if len(exit_nodes) != 1:
            errors.append(
                f"Expected one EXIT, found {len(exit_nodes)}"
            )
            return errors

        exit_node = exit_nodes[0]

        # All vertices should be able to reach EXIT.
        can_reach_exit = reachable(
            exit_node,
            reverse_adjacency
        )

        trapped = set(self.nodes) - can_reach_exit

        if trapped:
            errors.append(
                f"Vertices cannot reach EXIT: {sorted(trapped)}"
            )

        # Return nodes must connect to EXIT.
        for node, node_type in self.node_types.items():
            if node_type == "return":
                if exit_node not in adjacency[node]:
                    errors.append(
                        f"Return node {node} does not reach EXIT directly"
                    )

        return errors




