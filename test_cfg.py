import unittest

from lexer import Lexer
from parser import Parser
from cfg_builder import CFGBuilder


def generate_cfg(source, optimize=True):
    tokens = Lexer(source).tokenize()
    function = Parser(tokens).parse_function()

    graph = CFGBuilder().build(function)

    if optimize:
        graph.remove_empty_entries()
        graph.reduce_basic_blocks()

    return graph


def has_cycle(graph):
    adjacency = {node: [] for node in graph.nodes}

    for source, target, label in graph.edges:
        adjacency[source].append(target)

    visited = set()
    active = set()

    def dfs(node):
        visited.add(node)
        active.add(node)

        for neighbor in adjacency[node]:
            if neighbor in active:
                return True

            if neighbor not in visited and dfs(neighbor):
                return True

        active.remove(node)
        return False

    return any(
        dfs(node)
        for node in graph.nodes
        if node not in visited
    )


class TestCFGGenerator(unittest.TestCase):

    def test_unreachable_code(self):
        source = """
        int test(int x) {
            return x;
            x = x + 1;
        }
        """

        graph = generate_cfg(source)

        statements = "\n".join(graph.nodes.values())

        self.assertNotIn("x = x + 1", statements)
        self.assertIn("return x", statements)

    def test_partial_return(self):
        source = """
        int test(int x) {
            if (x > 0) {
                return x;
            } else {
                x = x + 1;
            }

            x = x * 2;
            return x;
        }
        """

        graph = generate_cfg(source)

        self.assertEqual(len(graph.nodes), 5)
        self.assertEqual(len(graph.edges), 5)

        statements = "\n".join(graph.nodes.values())

        self.assertIn("x = x + 1", statements)
        self.assertIn("x = x * 2", statements)

    def test_empty_branch(self):
        source = """
        int test(int x) {
            if (x > 0) {
            } else {
                x = x + 1;
            }
            return x;
        }
        """

        graph = generate_cfg(source)

        self.assertEqual(len(graph.nodes), 4)
        self.assertEqual(len(graph.edges), 4)

    def test_nested_loops(self):
        source = """
        int test(int n) {
            int count = 0;

            for (int i = 0; i < n; i = i + 1) {
                int j = 0;

                while (j < 3) {
                    count = count + 1;
                    j = j + 1;
                }
            }

            return count;
        }
        """

        graph = generate_cfg(source)

        self.assertEqual(len(graph.nodes), 8)
        self.assertEqual(len(graph.edges), 9)

    def test_composite_and(self):
        source = """
        int test(int x, int y) {
            if (x > 0 && y < 10) {
                return x;
            }
            return y;
        }
        """

        graph = generate_cfg(source)

        decision_nodes = [
            node_id
            for node_id, node_type in graph.node_types.items()
            if node_type == "decision"
        ]

        self.assertEqual(len(decision_nodes), 2)

    
    def test_boolean_precedence(self):
        source = """
        int test(int x, int y, int z) {
            if (x > 0 || y < 10 && z == 5) {
                return 1;
            }
            return 0;
        }
        """

        graph = generate_cfg(source, optimize=False)

        decisions = {
            node_id: text
            for node_id, text in graph.nodes.items()
            if graph.node_types[node_id] == "decision"
        }

        self.assertEqual(len(decisions), 3)

        self.assertIn("x > 0", decisions.values())
        self.assertIn("y < 10", decisions.values())
        self.assertIn("z == 5", decisions.values())

        def find_node(text):
            return next(
                node_id
                for node_id, value in graph.nodes.items()
                if value == text
            )

        x = find_node("x > 0")
        y = find_node("y < 10")
        z = find_node("z == 5")
        return_one = find_node("return 1")

        edges = set(graph.edges)

        # OR short-circuit: True skips remaining conditions.
        self.assertIn((x, return_one, "True"), edges)

        # False evaluates the right-hand AND expression.
        self.assertIn((x, y, "False"), edges)

        # AND: True evaluates the next condition.
        self.assertIn((y, z, "True"), edges)

    def test_boolean_parentheses(self):
        source = """
        int test(int x, int y, int z) {
            if ((x > 0 || y < 10) && z == 5) {
                return 1;
            }
            return 0;
        }
        """

        graph = generate_cfg(source, optimize=False)

        def find_node(text):
            return next(
                node_id
                for node_id, value in graph.nodes.items()
                if value == text
            )

        x = find_node("x > 0")
        y = find_node("y < 10")
        z = find_node("z == 5")
        return_one = find_node("return 1")
        return_zero = find_node("return 0")

        edges = set(graph.edges)

        # First evaluate x > 0.
        # If True, skip y and evaluate z.
        self.assertIn((x, z, "True"), edges)

        # If False, evaluate y.
        self.assertIn((x, y, "False"), edges)

        # Either True result from the OR
        # expression leads to z.
        self.assertIn((y, z, "True"), edges)

        # If both OR conditions are False,
        # skip the if body.
        self.assertIn((y, return_zero, "False"), edges)

        # The final AND condition determines
        # whether the if body executes.
        self.assertIn((z, return_one, "True"), edges)
        self.assertIn((z, return_zero, "False"), edges)

    def test_empty_while_loop(self):
        source = """
        int emptyWhile(int x) {
            while (x < 10) {
            }
            return x;
        }
        """

        graph = generate_cfg(source, optimize=True)

        def find_node(text):
            return next(
                node_id
                for node_id, value in graph.nodes.items()
                if value == text
            )

        condition = find_node("x < 10")
        return_node = find_node("return x")
        exit_node = find_node("EXIT")

        edges = set(graph.edges)

        # Empty loop body returns to the condition.
        self.assertIn(
            (condition, condition, "True"),
            edges
        )

        # False exits the loop.
        self.assertIn(
            (condition, return_node, "False"),
            edges
        )

        # Return connects to EXIT.
        self.assertIn(
            (return_node, exit_node, ""),
            edges
        )

    
    def test_empty_for_loop(self):
        source = """
        int emptyFor(int n) {
            for (int i = 0; i < n; i++) {
            }
            return n;
        }
        """

        graph = generate_cfg(source, optimize=True)

        # Display the graph for inspection.
        print("\nEMPTY FOR LOOP")
        graph.print_graph()

        statements = "\n".join(graph.nodes.values())

        self.assertIn("i < n", statements)
        self.assertIn("return n", statements)

        # A loop must contain a cycle.
        self.assertTrue(has_cycle(graph))

    def test_empty_do_while_loop(self):
        source = """
        int emptyDoWhile(int x) {
            do {
            } while (x < 10);

            return x;
        }
        """

        graph = generate_cfg(source, optimize=True)

        print("\nEMPTY DO-WHILE LOOP")
        graph.print_graph()

        statements = "\n".join(graph.nodes.values())

        self.assertIn("x < 10", statements)
        self.assertIn("return x", statements)

        # An empty do-while still loops.
        self.assertTrue(has_cycle(graph))


    def test_cyclomatic_complexity(self):
        cases = [
            (
                "Straight-line code",
                """
                int test(int x) {
                    x = x + 1;
                    return x;
                }
                """,
                1
            ),
            (
                "One if-else",
                """
                int test(int x) {
                    if (x > 0) {
                        x = x + 1;
                    } else {
                        x = x - 1;
                    }
                    return x;
                }
                """,
                2
            ),
            (
                "One while loop",
                """
                int test(int x) {
                    while (x < 10) {
                        x++;
                    }
                    return x;
                }
                """,
                2
            ),
            (
                "Nested loops",
                """
                int test(int n) {
                    for (int i = 0; i < n; i++) {
                        int j = 0;
                        while (j < 3) {
                            j++;
                        }
                    }
                    return n;
                }
                """,
                3
            ),
        ]

        for name, source, expected in cases:
            with self.subTest(name=name):
                graph = generate_cfg(source)
                self.assertEqual(
                    graph.cyclomatic_complexity(),
                    expected
                )

    def test_cfg_validation(self):
            source = """
            int test(int x) {
                while (x < 10) {
                    if (x == 5) {
                        return x;
                    }
                    x++;
                }
                return x;
            }
            """
    
            graph = generate_cfg(source)

            print("\nCFG VALIDATION TEST")
            graph.print_graph()

            errors = graph.validate()

            print("Validation errors:", errors)

            self.assertEqual(errors, [])

    def test_cfg_validation_invalid_edge(self):
        source = """
        int test(int x) {
            x = x + 1;
            return x;
        }
        """

        graph = generate_cfg(source)

        # Deliberately introduce an invalid edge.
        graph.add_edge(graph.entry_node, 999)

        errors = graph.validate()

        self.assertTrue(
            any("missing target 999" in error for error in errors),
            f"Expected missing-target error, got: {errors}"
        )

    
    def test_comments(self):
        source = """
        int test(int x) {
            // Increment the input
            x = x + 1;

            /*
               This is a multi-line comment.
               It should not create a CFG node.
            */

            if (x > 10) {
                // Return the updated value
                return x;
            }

            return 0;
        }
        """

        graph = generate_cfg(source)

        statements = "\n".join(graph.nodes.values())

        # Comments should not appear in the CFG.
        self.assertNotIn(
            "Increment the input",
            statements
        )

        self.assertNotIn(
            "multi-line comment",
            statements
        )

        self.assertNotIn(
            "Return the updated value",
            statements
        )

        # Executable statements must remain.
        self.assertIn("x = x + 1", statements)
        self.assertIn("x > 10", statements)
        self.assertIn("return x", statements)
        self.assertIn("return 0", statements)

        # The resulting graph must be valid.
        self.assertEqual(graph.validate(), [])

    def test_boolean_assignment(self):
        source = """
        int test(int x, int y) {
            bool valid = (x > 5 && y < 10);
            bool ready = valid || (x == y);

            if (ready) {
                return 1;
            }

            return 0;
        }
        """

        graph = generate_cfg(source)

        graph.print_graph()

        statements = "\n".join(graph.nodes.values())

        # Boolean assignments should remain in the CFG.
        self.assertIn("bool valid", statements)
        self.assertIn("&&", statements)
        self.assertIn("bool ready", statements)
        self.assertIn("||", statements)

        # The if condition should also be represented.
        self.assertIn("ready", statements)

        # The graph must remain structurally valid.
        self.assertEqual(graph.validate(), [])

    def test_mixed_nesting(self):
        source = """
        int test(int n) {
            int total = 0;

            for (int i = 0; i < n; i++) {
                if (i > 2) {
                    while (total < 10) {
                        total = total + i;
                    }
                } else {
                    total = total + 1;
                }
            }

            return total;
        }
        """

        graph = generate_cfg(source)

        graph.print_graph()

        statements = "\n".join(graph.nodes.values())

        # Verify key statements and conditions.
        self.assertIn("int total = 0", statements)
        self.assertIn("i < n", statements)
        self.assertIn("i > 2", statements)
        self.assertIn("total < 10", statements)
        self.assertIn("total = total + i", statements)
        self.assertIn("total = total + 1", statements)
        self.assertIn("return total", statements)

        # Verify the CFG is structurally valid.
        self.assertEqual(graph.validate(), [])

        # Multiple nested decisions should increase complexity.
        self.assertEqual(graph.cyclomatic_complexity(), 4)


    def test_parse_break_continue(self):
        from lexer import Lexer
        from parser import (
            Parser,
            Block,
            WhileStatement,
            IfStatement,
            BreakStatement,
            ContinueStatement
        )

        source = """
        int test(int x) {
            while (x < 10) {
                if (x == 3) {
                    continue;
                }

                if (x == 7) {
                    break;
                }

                x++;
            }

            return x;
        }
        """

        tokens = Lexer(source).tokenize()
        function = Parser(tokens).parse_function()

        loop = function.body.statements[0]
        self.assertIsInstance(loop, WhileStatement)

        self.assertIsInstance(loop.body, Block)

        first_if = loop.body.statements[0]
        second_if = loop.body.statements[1]

        self.assertIsInstance(first_if, IfStatement)
        self.assertIsInstance(second_if, IfStatement)

        self.assertIsInstance(
            first_if.then_branch.statements[0],
            ContinueStatement
        )

        self.assertIsInstance(
            second_if.then_branch.statements[0],
            BreakStatement
        )

    
    def test_break_continue_while(self):
        source = """
        int test(int n) {
            int i = 0;

            while (i < n) {
                i++;

                if (i == 3) {
                    continue;
                }

                if (i == 7) {
                    break;
                }
            }

            return i;
        }
        """

        graph = generate_cfg(source)
        graph.print_graph()

        statements = graph.nodes

        continue_nodes = [
            node for node, text in statements.items()
            if text == "continue"
        ]

        break_nodes = [
            node for node, text in statements.items()
            if text == "break"
        ]

        self.assertEqual(len(continue_nodes), 1)
        self.assertEqual(len(break_nodes), 1)

        condition = next(
            node for node, text in statements.items()
            if text == "i < n"
        )

        return_node = next(
            node for node, text in statements.items()
            if text == "return i"
        )

        self.assertIn(
            (continue_nodes[0], condition, ""),
            graph.edges
        )

        self.assertIn(
            (break_nodes[0], return_node, ""),
            graph.edges
        )

        self.assertEqual(graph.validate(), [])


    def test_break_continue_for(self):
        source = """
        int test(int n) {
            int total = 0;

            for (int i = 0; i < n; i++) {
                if (i == 3) {
                    continue;
                }

                if (i == 7) {
                    break;
                }

                total = total + i;
            }

            return total;
        }
        """

        graph = generate_cfg(source)
        graph.print_graph()

        def find_node(text):
            matches = [
                node for node, value in graph.nodes.items()
                if value == text
            ]
            self.assertEqual(len(matches), 1)
            return matches[0]

        continue_node = find_node("continue")
        break_node = find_node("break")
        update_node = find_node("i ++")
        condition_node = find_node("i < n")
        return_node = find_node("return total")

        # Continue must execute the update expression.
        self.assertIn(
            (continue_node, update_node, ""),
            graph.edges
        )

        # The update returns to the loop condition.
        self.assertIn(
            (update_node, condition_node, ""),
            graph.edges
        )

        # Break bypasses the update and exits the loop.
        self.assertIn(
            (break_node, return_node, ""),
            graph.edges
        )

        self.assertEqual(graph.validate(), [])
    
    def test_break_continue_do_while(self):
        source = """
        int test(int n) {
            int i = 0;

            do {
                i++;

                if (i == 3) {
                    continue;
                }

                if (i == 7) {
                    break;
                }
            } while (i < n);

            return i;
        }
        """

        graph = generate_cfg(source)
        graph.print_graph()

        def find_node(text):
            matches = [
                node for node, value in graph.nodes.items()
                if value == text
            ]
            self.assertEqual(len(matches), 1)
            return matches[0]

        continue_node = find_node("continue")
        break_node = find_node("break")
        condition_node = find_node("i < n")
        return_node = find_node("return i")

        # Continue evaluates the bottom condition.
        self.assertIn(
            (continue_node, condition_node, ""),
            graph.edges
        )

        # Break exits the loop immediately.
        self.assertIn(
            (break_node, return_node, ""),
            graph.edges
        )

        # The graph must remain valid.
        self.assertEqual(graph.validate(), [])


    def test_unconditional_break_do_while(self):
        source = """
        int test(int x) {
            do {
                break;
            } while (x < 10);

            return x;
        }
        """

        graph = generate_cfg(source)
        graph.print_graph()

        statements = "\n".join(graph.nodes.values())

        # Break must remain in the CFG.
        self.assertIn("break", statements)

        # The condition is unreachable.
        self.assertNotIn("x < 10", statements)

        # Execution must proceed to the return.
        break_node = next(
            node for node, text in graph.nodes.items()
            if text == "break"
        )

        return_node = next(
            node for node, text in graph.nodes.items()
            if text == "return x"
        )

        self.assertIn(
            (break_node, return_node, ""),
            graph.edges
        )

        self.assertEqual(graph.validate(), [])

    def test_nested_break_continue(self):
            source = """
            int test(int n) {
                int total = 0;
    
                for (int i = 0; i < n; i++) {
                    int j = 0;
    
                    while (j < 5) {
                        j++;
    
                        if (j == 2) {
                            continue;
                        }
    
                        if (j == 4) {
                            break;
                        }
    
                        total = total + j;
                    }
    
                    total = total + i;
                }
    
                return total;
            }
            """
    
            graph = generate_cfg(source)
            graph.print_graph()
    
            def find_node(text):
                matches = [
                    node for node, value in graph.nodes.items()
                    if value == text
                ]
                self.assertEqual(len(matches), 1)
                return matches[0]
    
            continue_node = find_node("continue")
            break_node = find_node("break")
    
            inner_condition = find_node("j < 5")
            outer_condition = find_node("i < n")
    
            after_inner_loop = next(
                node for node, text in graph.nodes.items()
                if "total = total + i" in text.splitlines()
            )
    
            # Continue targets the inner while condition.
            self.assertIn(
                (continue_node, inner_condition, ""),
                graph.edges
            )
    
            # Break exits only the inner while loop.
            self.assertIn(
                (break_node, after_inner_loop, ""),
                graph.edges
            )
    
            # Continue must not target the outer loop.
            self.assertNotIn(
                (continue_node, outer_condition, ""),
                graph.edges
            )
    
            self.assertEqual(graph.validate(), [])


    def test_do_while_both_branches_terminate(self):
        source = """
        int test(int x) {
            do {
                if (x > 5) {
                    break;
                } else {
                    return x;
                }
            } while (x < 10);

            return 0;
        }
        """

        graph = generate_cfg(source)
        graph.print_graph()

        def find_node(text):
            matches = [
                node for node, value in graph.nodes.items()
                if value == text
            ]
            self.assertEqual(len(matches), 1)
            return matches[0]

        condition = find_node("x > 5")
        break_node = find_node("break")
        return_x = find_node("return x")
        return_zero = find_node("return 0")

        # The bottom condition must be unreachable.
        self.assertFalse(
            any(
                text == "x < 10"
                for text in graph.nodes.values()
            )
        )

        # True branch breaks out of the loop.
        self.assertIn(
            (condition, break_node, "True"),
            graph.edges
        )

        # False branch returns immediately.
        self.assertIn(
            (condition, return_x, "False"),
            graph.edges
        )

        # Break reaches the statement after the loop.
        self.assertIn(
            (break_node, return_zero, ""),
            graph.edges
        )

        self.assertEqual(graph.validate(), [])


    def test_read_write(self):
        source = """
        int readWrite(int x) {
            int total = 0;
            cin >> x;

            if (x > 0) {
                total = x * 2;
                cout << total;
            } else {
                total = 0;
                cout << total;
            }

            return total;
        }
        """

        graph = generate_cfg(source)

        self.assertEqual(graph.validate(), [])
        self.assertEqual(graph.cyclomatic_complexity(), 2)

        labels = list(graph.nodes.values())
        self.assertTrue(any("cin >> x" in label for label in labels))
        self.assertTrue(any("cout << total" in label for label in labels))


    def test_comprehensive(self):
        source = """
        int comprehensive(int n) {
            int total = 0;
            int i = 0;

            while (i < n) {
                if (i > 2 && i < 8) {
                    total = total + i;
                } else {
                    total = total + 1;
                }
                i++;
            }

            for (int j = 0; j < 5; j++) {
                total = total + j;
            }

            do {
                total = total - 1;
            } while (total > 20);

            if (total < 0 || total == 10) {
                total = 0;
            }

            return total;
        }
        """

        graph = generate_cfg(source)

        self.assertEqual(graph.validate(), [])
        self.assertEqual(graph.cyclomatic_complexity(), 8)
        self.assertEqual(len(graph.nodes), 17)
        self.assertEqual(len(graph.edges), 23)

if __name__ == "__main__":
    unittest.main()
