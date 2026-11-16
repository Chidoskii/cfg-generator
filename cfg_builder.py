from cfg import CFG
from parser import (
    Block,
    Statement,
    IfStatement,
    WhileStatement,
    ForStatement,
    DoWhileStatement,
    BreakStatement,
    ContinueStatement,
)


class CFGBuilder:
    def __init__(self):
        self.graph = CFG()
        self.return_nodes = []
        self.loop_stack = []

    
    def build(self, function):
        # Create a temporary function-entry node.
        entry = self.graph.add_node(
            "FUNCTION_ENTRY",
            node_type="entry"
        )

        # Record the entry point.
        self.graph.entry_node = entry

        # Build the function body, starting from entry.
        exits = self.build_statement(
            function.body,
            [(entry, "")]
        )

        # Create the function's exit node.
        end = self.graph.add_node(
            "EXIT",
            node_type="exit"
        )

        # Connect normal completion paths.
        self.connect(exits, end)

        # Connect every return directly to EXIT.
        for node_id in self.return_nodes:
            self.graph.add_edge(node_id, end)

        return self.graph


    def connect(self, exits, target):
        for node_id, label in exits:
            self.graph.add_edge(node_id, target, label)

    
    
    def strip_outer_parentheses(self, condition):
        """
        Remove parentheses that enclose the
        entire Boolean expression.
        """
        condition = condition.strip()

        while condition.startswith("(") and condition.endswith(")"):
            depth = 0
            encloses_entire_expression = True

            for i, char in enumerate(condition):
                if char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1

                if depth == 0 and i < len(condition) - 1:
                    encloses_entire_expression = False
                    break

            if not encloses_entire_expression:
                break

            condition = condition[1:-1].strip()

        return condition

    def split_condition(self, condition):
        """
        Split a Boolean expression at the
        lowest-precedence top-level operator.

        || has lower precedence than &&.
        """
        condition = self.strip_outer_parentheses(condition)

        for operator in ("||", "&&"):
            depth = 0

            for i in range(len(condition) - 1):
                char = condition[i]

                if char == "(":
                    depth += 1
                elif char == ")":
                    depth -= 1

                if depth == 0 and condition[i:i + 2] == operator:
                    left = condition[:i].strip()
                    right = condition[i + 2:].strip()

                    return left, operator, right

        return None

    def build_condition(self, condition, incoming):
        """
        Construct decision nodes for a simple or
        two-part composite Boolean expression.

        Returns:
            (true_exits, false_exits)
        """
        condition = self.strip_outer_parentheses(condition)
        parts = self.split_condition(condition)

        if parts is None:
            node = self.graph.add_node(
                condition,
                node_type="decision"
            )
            self.connect(incoming, node)

            return (
                [(node, "True")],
                [(node, "False")]
            )

        left, operator, right = parts

        left_true, left_false = self.build_condition(
            left, incoming
        )

        if operator == "&&":
            right_true, right_false = self.build_condition(
                right, left_true
            )

            return (
                right_true,
                left_false + right_false
            )

        if operator == "||":
            right_true, right_false = self.build_condition(
                right, left_false
            )

            return (
                left_true + right_true,
                right_false
            )

    def build_statement(self, statement, incoming):
        if isinstance(statement, Block):
            exits = incoming

            for child in statement.statements:
                # No reachable path remains.
                if not exits and self.graph.nodes:
                    break

                exits = self.build_statement(child, exits)

            return exits
        
        if isinstance(statement, BreakStatement):
            if not self.loop_stack:
                raise SyntaxError("'break' outside a loop")

            node = self.graph.add_node(
                "break",
                node_type="break"
            )
            self.connect(incoming, node)

            self.loop_stack[-1]["break_exits"].append(
                (node, "")
            )

            return []

        if isinstance(statement, ContinueStatement):
            if not self.loop_stack:
                raise SyntaxError("'continue' outside a loop")

            node = self.graph.add_node(
                "continue",
                node_type="continue"
            )
            self.connect(incoming, node)

            context = self.loop_stack[-1]
            target = context["continue_target"]

            if target is not None:
                self.graph.add_edge(node, target)
            else:
                context["continue_exits"].append(
                    (node, "")
                )

            return []
       
        if isinstance(statement, Statement):
            text = statement.text.strip()

            is_return = (
                text == "return"
                or text.startswith("return ")
            )

            node = self.graph.add_node(
                text,
                node_type="return" if is_return else "statement"
            )

            self.connect(incoming, node)

            if is_return:
                self.return_nodes.append(node)
                return []

            return [(node, "")]

        if isinstance(statement, IfStatement):
            true_exits, false_exits = self.build_condition(
                statement.condition,
                incoming
            )

            then_exits = self.build_statement(
                statement.then_branch,
                true_exits
            )

            if statement.else_branch is not None:
                else_exits = self.build_statement(
                    statement.else_branch,
                    false_exits
                )
            else:
                else_exits = false_exits

            return then_exits + else_exits
        
        
        if isinstance(statement, WhileStatement):
            entry = self.graph.add_node(
                "WHILE_ENTRY",
                node_type="entry"
            )
            self.connect(incoming, entry)

            true_exits, false_exits = self.build_condition(
                statement.condition,
                [(entry, "")]
            )

            context = {
                "break_exits": [],
                "continue_target": entry,
                "continue_exits": []
            }
            self.loop_stack.append(context)

            body_exits = self.build_statement(
                statement.body,
                true_exits
            )

            self.loop_stack.pop()

            # Normal iteration returns to the condition.
            self.connect(body_exits, entry)

            # Break exits join the condition's false exits.
            return false_exits + context["break_exits"]
        
        
        if isinstance(statement, ForStatement):
            if statement.initialization:
                init = self.graph.add_node(
                    statement.initialization,
                    node_type="statement"
                )
                self.connect(incoming, init)
                incoming = [(init, "")]

            entry = self.graph.add_node(
                "FOR_ENTRY",
                node_type="entry"
            )
            self.connect(incoming, entry)

            if statement.condition:
                true_exits, false_exits = self.build_condition(
                    statement.condition,
                    [(entry, "")]
                )
            else:
                true_exits = [(entry, "")]
                false_exits = []

            # Create update node before building the body.
            update = None

            if statement.update:
                update = self.graph.add_node(
                    statement.update,
                    node_type="statement"
                )

            context = {
                "break_exits": [],
                "continue_target": update if update is not None else entry,
                "continue_exits": []
            }
            self.loop_stack.append(context)

            body_exits = self.build_statement(
                statement.body,
                true_exits
            )

            self.loop_stack.pop()

            if update is not None:
                self.connect(body_exits, update)
                self.graph.add_edge(update, entry)
            else:
                self.connect(body_exits, entry)

            return false_exits + context["break_exits"]
    
        
        if isinstance(statement, DoWhileStatement):
            entry = self.graph.add_node(
                "DO_ENTRY",
                node_type="entry"
            )
            self.connect(incoming, entry)

            context = {
                "break_exits": [],
                "continue_target": None,
                "continue_exits": []
            }
            self.loop_stack.append(context)

            body_exits = self.build_statement(
                statement.body,
                [(entry, "")]
            )

            self.loop_stack.pop()

            # Normal completion and continue both
            # proceed to the bottom condition.
            condition_incoming = (
                body_exits + context["continue_exits"]
            )

            # If no path reaches the condition,
            # do not create an unreachable decision.
            if not condition_incoming:
                return context["break_exits"]

            true_exits, false_exits = self.build_condition(
                statement.condition,
                condition_incoming
            )

            # A true condition repeats the body.
            self.connect(true_exits, entry)

            return false_exits + context["break_exits"]


        raise TypeError(
            f"Unsupported AST node: {type(statement).__name__}"
        )
