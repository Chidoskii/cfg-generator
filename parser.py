from dataclasses import dataclass, field


@dataclass
class Statement:
    text: str


@dataclass
class BreakStatement:
    pass


@dataclass
class ContinueStatement:
    pass


@dataclass
class Block:
    statements: list = field(default_factory=list)


@dataclass
class IfStatement:
    condition: str
    then_branch: object
    else_branch: object = None


@dataclass
class WhileStatement:
    condition: str
    body: object


@dataclass
class ForStatement:
    initialization: str
    condition: str
    update: str
    body: object


@dataclass
class DoWhileStatement:
    body: object
    condition: str


@dataclass
class Function:
    signature: str
    body: Block


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.position = 0

    def current(self):
        return self.tokens[self.position]

    def advance(self):
        token = self.current()
        if token.type != "EOF":
            self.position += 1
        return token

    def match(self, value):
        if self.current().value == value:
            self.advance()
            return True
        return False

    def expect(self, value):
        if not self.match(value):
            token = self.current()
            raise SyntaxError(
                f"Expected {value!r}, got "
                f"{token.value!r} at line {token.line}"
            )
    
    
    
    def collect_until(self, delimiter):
        values = []
        depth = 0

        while self.current().type != "EOF":
            token = self.current()

            if token.value == delimiter and depth == 0:
                break

            # A closing brace before a required semicolon
            # indicates a likely missing semicolon.
            if token.value == "}" and depth == 0:
                raise SyntaxError(
                    f"Expected {delimiter!r} before "
                    f"'}}' at line {token.line}"
                )

            if token.value == "(":
                depth += 1

            elif token.value == ")":
                if depth == 0:
                    raise SyntaxError(
                        f"Unexpected ')' at line {token.line}"
                    )
                depth -= 1

            values.append(self.advance().value)

        if self.current().type == "EOF":
            raise SyntaxError(
                f"Expected delimiter {delimiter!r} "
                "before end of file"
            )

        return " ".join(values)

    def parse_condition(self):
        self.expect("(")
        values = []
        depth = 1

        while depth > 0:
            token = self.advance()

            if token.type == "EOF":
                raise SyntaxError("Unclosed condition")

            if token.value == "(":
                depth += 1
            elif token.value == ")":
                depth -= 1

            if depth > 0:
                values.append(token.value)

        return " ".join(values)

    def parse_function(self):
        signature = []

        while self.current().value != "{":
            if self.current().type == "EOF":
                raise SyntaxError("Expected function body")
            signature.append(self.advance().value)

        body = self.parse_block()

        if self.current().type != "EOF":
            raise SyntaxError("Unexpected tokens after function")

        return Function(" ".join(signature), body)

    def parse_block(self):
        self.expect("{")
        statements = []

        while self.current().value != "}":
            if self.current().type == "EOF":
                raise SyntaxError("Unclosed block")

            statements.append(self.parse_statement())

        self.expect("}")
        return Block(statements)

    
    def parse_statement(self):
        token = self.current()

        if token.value == "{":
            return self.parse_block()

        if token.value == "if":
            return self.parse_if()

        if token.value == "while":
            return self.parse_while()

        if token.value == "for":
            return self.parse_for()

        if token.value == "do":
            return self.parse_do_while()

        if token.value == "break":
            self.advance()
            self.expect(";")
            return BreakStatement()

        if token.value == "continue":
            self.advance()
            self.expect(";")
            return ContinueStatement()

        if token.value == "else":
            raise SyntaxError(
                f"Unexpected else at line {token.line}"
            )

        text = self.collect_until(";")
        self.expect(";")

        return Statement(text)


    def parse_if(self):
        self.expect("if")
        condition = self.parse_condition()

        then_branch = self.parse_statement()
        else_branch = None

        if self.match("else"):
            else_branch = self.parse_statement()

        return IfStatement(
            condition,
            then_branch,
            else_branch
        )

    
    def parse_while(self):
        self.expect("while")
        condition = self.parse_condition()
        body = self.parse_statement()

        return WhileStatement(condition, body)

    def parse_for(self):
        self.expect("for")
        self.expect("(")

        initialization = self.collect_until(";")
        self.expect(";")

        condition = self.collect_until(";")
        self.expect(";")

        update = self.collect_until(")")
        self.expect(")")

        body = self.parse_statement()

        return ForStatement(
            initialization,
            condition,
            update,
            body
        )

    def parse_do_while(self):
        self.expect("do")

        body = self.parse_statement()

        self.expect("while")
        condition = self.parse_condition()
        self.expect(";")

        return DoWhileStatement(body, condition)
