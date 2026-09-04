from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from grammar import EOF, EPSILON, Grammar  # noqa: E402


def rules(grammar: Grammar, nonterminal: str) -> list[tuple[str, ...]]:
    return [production.rhs for production in grammar.productions_for(nonterminal)]


def test_remove_recursao_direta_com_duas_alternativas():
    grammar = Grammar.from_text(
        """
        Expr ::= Expr PLUS Term | Expr MINUS Term | Term
        Term ::= IDENTIFIER
        """
    )
    assert grammar.eliminate_direct_left_recursion("Expr") is True
    assert rules(grammar, "Expr") == [("Term", "Expr'")]
    assert rules(grammar, "Expr'") == [
        ("PLUS", "Term", "Expr'"),
        ("MINUS", "Term", "Expr'"),
        (),
    ]


def test_first_percorre_sequencias_anulaveis_ate_o_ponto_fixo():
    grammar = Grammar.from_text(
        """
        S ::= A B
        A ::= C | ε
        B ::= b | ε
        C ::= c
        """
    )
    grammar.build_first()
    assert grammar.first["S"] == {"c", "b", EPSILON}
    assert grammar.first["A"] == {"c", EPSILON}
    assert grammar.first_of_sequence(("A", "B")) == {
        "c", "b", EPSILON
    }


def test_follow_propaga_atraves_de_sufixos_anulaveis():
    grammar = Grammar.from_text(
        """
        S ::= A B C
        A ::= a | ε
        B ::= b | ε
        C ::= c | ε
        """
    )
    grammar.build_first()
    grammar.build_follow()
    assert grammar.follow["S"] == {EOF}
    assert grammar.follow["A"] == {"b", "c", EOF}
    assert grammar.follow["B"] == {"c", EOF}
    assert grammar.follow["C"] == {EOF}


def test_start_de_producao_anulavel_inclui_follow():
    grammar = Grammar.from_text(
        """
        S ::= A B
        A ::= a | ε
        B ::= b | ε
        """
    )
    grammar.build_sets()
    terminal_a, empty_a = grammar.productions_for("A")
    terminal_b, empty_b = grammar.productions_for("B")
    assert grammar.start[terminal_a] == {"a"}
    assert grammar.start[empty_a] == {"b", EOF}
    assert grammar.start[terminal_b] == {"b"}
    assert grammar.start[empty_b] == {EOF}


def test_gramatica_microc_comeca_com_conflitos_e_termina_ll1():
    grammar = Grammar.from_file(PROJECT_ROOT / "MicroC.grammar")

    grammar.build_sets()
    assert grammar.ll1_conflicts(), (
        "a gramática inicial deve continuar não LL(1); "
        "não altere MicroC.grammar"
    )

    grammar.eliminate_all_direct_left_recursion()
    assert all(
        not production.rhs or production.rhs[0] != production.lhs
        for production in grammar.productions
    )
    grammar.left_factor()
    grammar.build_sets()

    assert grammar.first["program"] == {
        "KW_INT", "KW_BOOL", "KW_VOID", EPSILON
    }
    assert grammar.follow["expression"] == {
        "COMMA", "RIGHT_PAREN", "SEMICOLON"
    }
    assert grammar.is_ll1()


def test_remove_recursao_com_base_vazia():
    """Testa caso onde beta é vazio (produção epsilon já na base)."""
    grammar = Grammar.from_text(
        """
        A ::= A a | ε
        """
    )
    assert grammar.eliminate_direct_left_recursion("A") is True
    assert rules(grammar, "A") == [("A'",)]
    assert rules(grammar, "A'") == [("a", "A'"), ()]


def test_remove_recursao_retorna_false_se_nao_houver():
    """Testa se retorna False e mantém as regras intactas caso não haja recursão direta."""
    grammar = Grammar.from_text(
        """
        A ::= a B | c
        B ::= b
        """
    )
    assert grammar.eliminate_direct_left_recursion("A") is False
    assert rules(grammar, "A") == [("a", "B"), ("c",)]


def test_remove_recursao_evita_colisao_com_simbolos_existentes():
    """Testa se _fresh_nonterminal gera A'' se A' já existir na gramática."""
    grammar = Grammar.from_text(
        """
        Expr ::= Expr PLUS Term | Term
        Expr' ::= IDENTIFIER
        Term ::= NUMBER
        """
    )
    assert grammar.eliminate_direct_left_recursion("Expr") is True
    assert rules(grammar, "Expr") == [("Term", "Expr''")]
    assert rules(grammar, "Expr''") == [("PLUS", "Term", "Expr''"), ()]


def test_first_e_follow_com_cadeia_longa_anulavel():
    """Testa cadeia longa de não-terminais anuláveis até convergência de ponto fixo."""
    grammar = Grammar.from_text(
        """
        S ::= A B C D
        A ::= B | ε
        B ::= C | ε
        C ::= D | ε
        D ::= d | ε
        """
    )
    grammar.build_sets()
    assert grammar.first["S"] == {"d", EPSILON}
    assert grammar.first["A"] == {"d", EPSILON}
    assert grammar.first["B"] == {"d", EPSILON}
    assert grammar.first["C"] == {"d", EPSILON}
    assert grammar.first["D"] == {"d", EPSILON}
    assert grammar.follow["S"] == {EOF}
    assert grammar.follow["A"] == {"d", EOF}
    assert grammar.follow["B"] == {"d", EOF}
    assert grammar.follow["C"] == {"d", EOF}
    assert grammar.follow["D"] == {"d", EOF}


def test_follow_com_terminais_bloqueando_propagacao():
    """Testa se terminais no RHS bloqueiam a propagação de símbolos posteriores."""
    grammar = Grammar.from_text(
        """
        S ::= A x B y
        A ::= a | ε
        B ::= b | ε
        """
    )
    grammar.build_sets()
    assert grammar.follow["S"] == {EOF}
    assert grammar.follow["A"] == {"x"}
    assert grammar.follow["B"] == {"y"}


def test_follow_com_dependencia_circular_mutua():
    """Testa propagação de FOLLOW com dependência mútua entre não-terminais."""
    grammar = Grammar.from_text(
        """
        S ::= a A
        A ::= b B | c
        B ::= d A | e
        """
    )
    grammar.build_sets()
    assert grammar.follow["S"] == {EOF}
    assert grammar.follow["A"] == {EOF}
    assert grammar.follow["B"] == {EOF}


def test_first_of_sequence_com_sequencia_vazia_e_terminais():
    grammar = Grammar.from_text(
        """
        S ::= a
        """
    )
    grammar.build_sets()
    assert grammar.first_of_sequence(()) == {EPSILON}
    assert grammar.first_of_sequence(("a",)) == {"a"}
    assert grammar.first_of_sequence(("a", "b", "c")) == {"a"}

