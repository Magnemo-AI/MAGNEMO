"""THE DIALOG YES, the words (drill D5): the first-run paste and the README's top screen say the action in one sentence
and never send anyone to a terminal. The manual names the command line once."""
import os, re, unittest
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SENTENCE = "Your agent writes one line down and keeps working. Say keep, and it is Memory."      # P-106 addendum D (was: "… asks you in the chat. One click.")


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


@unittest.skipUnless(os.path.exists(os.path.join(ROOT, "README.md")), "the docs are not in this tree")
class TestTheWords(unittest.TestCase):
    def setUp(self):
        self.readme = read("README.md")
        self.top = self.readme.split("## Install in your client")[0]                 # everything before the per-client blocks
        self.paste = re.search(r"```text\n(Set up MAGNEMO in this project:.*?)```", self.readme, re.S).group(1)

    def test_no_terminal_on_the_top_screen_in_the_paste_or_in_the_install_file(self):
        for name, text in (("the README's top screen", self.top), ("the first-run paste", self.paste), ("llms-install.md", read("llms-install.md"))):
            self.assertEqual(re.findall(r"terminal", text, re.I), [], name)

    def test_the_action_is_said_in_the_one_sentence(self):
        self.assertIn(SENTENCE, self.top)
        self.assertLess(self.top.index(SENTENCE), self.top.index("## Install in one paste"))   # above the paste: the first screen
        self.assertTrue(self.readme.split("\n", 1)[1].startswith("**The Memory MCP. Your AI remembers. You keep what matters.**\n\nMAGNEMO is Memory for your AI, kept on your computer in plain files."))   # the founder's lines, Oct 12
        self.assertIn('<img alt="MAGNEMO"', self.readme.split("\n", 1)[0])   # the Mark Law (Oct 24, carried in addendum D): the header is the lockup
        self.assertIn("nothing becomes Memory until you approve it, and every Memory shows who wrote it and who approved it.", self.top)
        self.assertLess(self.top.index("pip install MAGNEMO"), self.top.index("Set up MAGNEMO in this project:"))   # three lines before the paste
        self.assertIn("## Works with", self.top)
        self.assertIn("Your agent writes one line down and\nkeeps working. Say keep, and it is Memory.", self.top)   # P-106 addendum A: nothing asks mid-work
        self.assertIn("Look around this folder, tell me what this project is for, and stage that as the first note.", self.paste)   # addendum D: the restart line
        self.assertNotIn("One click", self.top)

    def test_the_paste_no_longer_asks_for_a_command_to_approve(self):
        self.assertNotIn("command to approve", self.paste); self.assertNotIn("magnemo yes", self.top)
        self.assertIn("restart you", self.paste)                                    # the tools load at the client's start: the one step that is left

    def test_the_command_line_is_named_once_in_the_manual_and_nowhere_above_it(self):
        manual = read("docs", "MCP.md")
        self.assertEqual(manual.count("at their own terminal is the verified yes"), 1)   # the manual sends a person there in one place (P-106 v3)
        self.assertNotIn("The CLI is the other door", self.readme)

    def test_the_limit_is_written_down(self):
        limits = " ".join(read("KNOWN_LIMITS.md").split())
        self.assertIn("It stops a wrong thing from becoming memory without a person; it does not stop a wrong thing from being written.", limits)
        self.assertIn("The question at the pause is drawn by your client, not by MAGNEMO.", limits)   # P-106 addendum A
        self.assertIn("under 300 ms", limits)


if __name__ == "__main__":
    unittest.main()
