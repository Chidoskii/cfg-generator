import re
from dataclasses import dataclass


@dataclass
class Token:
    type: str
    value: str
    line: int


class Lexer:
    TOKEN_SPECIFICATION = [
        ("COMMENT", r"//[^\n]*|/\*[\s\S]*?\*/"),
        ("STRING", r'"(?:\\.|[^"\\])*"'),
        ("CHAR", r"'(?:\\.|[^'\\])'"),
        ("NUMBER", r"\d+(?:\.\d+)?"),
        ("IDENTIFIER", r"[A-Za-z_]\w*"),
        ("OPERATOR", r">>|<<|==|!=|<=|>=|&&|\|\||\+\+|--|[+\-*/%=<>!]"),
        ("LPAREN", r"\("),
        ("RPAREN", r"\)"),
        ("LBRACE", r"\{"),
        ("RBRACE", r"\}"),
        ("SEMICOLON", r";"),
        ("COMMA", r","),
        ("WHITESPACE", r"\s+"),
        ("MISMATCH", r"."),
    ]

    KEYWORDS = {
        "if", "else", "while", "for", "do",
        "return", "break", "continue",
        "int", "float", "double", "char",
        "bool", "boolean", "void", "true",
        "false", "cin", "cout", "printf",
        "scanf"
    }

    def __init__(self, source):
        self.source = source
        self.tokens = []

    def tokenize(self):
        pattern = "|".join(
            f"(?P<{name}>{regex})"
            for name, regex in self.TOKEN_SPECIFICATION
        )

        line = 1

        for match in re.finditer(pattern, self.source):
            token_type = match.lastgroup
            value = match.group()

            if token_type == "WHITESPACE":
                line += value.count("\n")
                continue

            if token_type == "COMMENT":
                line += value.count("\n")
                continue

            if token_type == "MISMATCH":
                raise SyntaxError(
                    f"Unexpected character {value!r} "
                    f"at line {line}"
                )

            if token_type == "IDENTIFIER":
                if value in self.KEYWORDS:
                    token_type = "KEYWORD"

            self.tokens.append(
                Token(token_type, value, line)
            )

            line += value.count("\n")

        self.tokens.append(Token("EOF", "", line))

        return self.tokens
