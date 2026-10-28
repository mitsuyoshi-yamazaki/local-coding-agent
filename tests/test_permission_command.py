import unittest

from local_coding_agent.permissions.command import has_substitution, split_command


class SplitCommandTest(unittest.TestCase):
    def test_single_command(self) -> None:
        self.assertEqual(split_command("  ls -la  "), ("ls -la",))

    def test_operators(self) -> None:
        self.assertEqual(
            split_command("a && b || c; d | e & f\ng"),
            ("a", "b", "c", "d", "e", "f", "g"),
        )

    def test_operators_without_spaces(self) -> None:
        self.assertEqual(split_command("a&&b;c|d"), ("a", "b", "c", "d"))

    def test_quotes_are_not_split(self) -> None:
        self.assertEqual(
            split_command("""echo 'a; b' "c && d" e"""),
            ("""echo 'a; b' "c && d" e""",),
        )

    def test_quote_inside_other_quote(self) -> None:
        self.assertEqual(
            split_command("""echo "it's; ok" ; ls"""), ("""echo "it's; ok\"""", "ls")
        )

    def test_backslash_escapes_the_next_character(self) -> None:
        self.assertEqual(split_command(r"echo a\; b"), (r"echo a\; b",))
        self.assertEqual(
            split_command(r'echo "a\" ; b"; ls'), (r'echo "a\" ; b"', "ls")
        )

    def test_backslash_is_plain_inside_single_quotes(self) -> None:
        self.assertEqual(split_command(r"echo 'a\'; ls"), (r"echo 'a\'", "ls"))

    def test_redirects_are_not_split(self) -> None:
        for command in (
            "python3 -m unittest 2>&1",
            "make &> log.txt",
            "cat <&3",
            "echo a >&2",
        ):
            with self.subTest(command=command):
                self.assertEqual(split_command(command), (command,))

    def test_redirect_then_operator(self) -> None:
        self.assertEqual(
            split_command("python3 -m unittest 2>&1 | tail -5"),
            ("python3 -m unittest 2>&1", "tail -5"),
        )

    def test_empty_parts_are_dropped(self) -> None:
        self.assertEqual(split_command("a;; b &&"), ("a", "b"))
        self.assertEqual(split_command("   "), ())

    def test_unclosed_quote_keeps_the_rest(self) -> None:
        self.assertEqual(split_command("echo 'a; rm x"), ("echo 'a; rm x",))

    def test_leading_grouping_and_keywords_are_removed(self) -> None:
        for command, parts in (
            ("(cd build && rm x)", ("cd build", "rm x)")),
            ("(rm x)", ("rm x)",)),
            ("{ rm x; }", ("rm x", "}")),
            ("! rm x", ("rm x",)),
            ("for f in *; do rm $f; done", ("for f in *", "rm $f", "done")),
            ("if true; then rm x; fi", ("true", "rm x", "fi")),
            ("while true; do rm x; done", ("true", "rm x", "done")),
            ("time python3 -m unittest", ("python3 -m unittest",)),
        ):
            with self.subTest(command=command):
                self.assertEqual(split_command(command), parts)

    def test_words_starting_like_keywords_are_kept(self) -> None:
        self.assertEqual(split_command("done.sh; dox"), ("done.sh", "dox"))

    def test_whitespace_runs_become_one_space(self) -> None:
        self.assertEqual(split_command("rm\t-rf   x"), ("rm -rf x",))

    def test_quote_inside_comment_does_not_hide_next_line(self) -> None:
        # コメントの中の ' は引用符ではない。改行の後の rm x は、別の部分として走る
        for command, parts in (
            ("echo hi # don't\nrm x", ("echo hi # don't", "rm x")),
            ("ls;# it's\nrm x", ("ls", "# it's", "rm x")),
            ("(# it's\nrm x)", ("# it's", "rm x)")),
            ('echo a >#"x\nrm x', ('echo a >#"x', "rm x")),
        ):
            with self.subTest(command=command):
                self.assertEqual(split_command(command), parts)

    def test_separators_inside_comment_are_not_split(self) -> None:
        # シェルは # から行末までを走らせないので、; の後ろは部分にしない
        self.assertEqual(split_command("echo a # ; rm x"), ("echo a # ; rm x",))

    def test_hash_inside_a_word_is_not_a_comment(self) -> None:
        for command, parts in (
            ("echo a#b; rm x", ("echo a#b", "rm x")),
            ("echo $#; rm x", ("echo $#", "rm x")),
            ("echo '#'; rm x", ("echo '#'", "rm x")),
            (r"echo \#; rm x", (r"echo \#", "rm x")),
        ):
            with self.subTest(command=command):
                self.assertEqual(split_command(command), parts)

    def test_ansi_c_quotes(self) -> None:
        # $'\'' は ' の1字。後ろの ; は引用符の外にある
        self.assertEqual(
            split_command("echo $'\\'' ; rm x ; echo ''"),
            ("echo $'\\''", "rm x", "echo ''"),
        )
        self.assertEqual(split_command("echo $'a;b'"), ("echo $'a;b'",))


class SubstitutionTest(unittest.TestCase):
    def test_marks(self) -> None:
        for command in ("echo $(rm x)", "echo `rm x`", "diff <(a) b", "tee >(b)"):
            with self.subTest(command=command):
                self.assertTrue(has_substitution(command))

    def test_plain_commands(self) -> None:
        for command in ("echo $HOME", "ls (a)", "a > b"):
            with self.subTest(command=command):
                self.assertFalse(has_substitution(command))

    def test_inside_quotes_is_also_counted(self) -> None:
        self.assertTrue(has_substitution("echo '$(x)'"))


if __name__ == "__main__":
    unittest.main()
