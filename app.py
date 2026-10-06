import tkinter as tk
from tkinter import ttk, messagebox
import re


# ============================================================
# GNF CONVERSION ENGINE
# ============================================================

class GNFConverter:

    def __init__(self, variables, terminals, start, rules):
        self.variables = variables
        self.terminals = terminals
        self.start = start
        self.rules = rules
        self.steps = []

    # --------------------------------------------------------
    # Step History Helpers
    # --------------------------------------------------------

    def format_grammar(self, rules):
        """Convert grammar dictionary into readable text."""
        lines = []

        for A in sorted(rules.keys()):
            productions = []

            for prod in sorted(rules[A], key=lambda x: " ".join(x)):
                if len(prod) == 0:
                    productions.append("ε")
                else:
                    productions.append(" ".join(prod))

            if productions:
                lines.append(f"{A} → " + " | ".join(productions))

        return "\n".join(lines) if lines else "No productions."

    def record_step(self, title, before, after, explanation):
        """Store a complete Before → Operation → After transformation."""
        before_text = self.format_grammar(before)
        after_text = self.format_grammar(after)

        change = "NO CHANGE REQUIRED" if before_text == after_text else "GRAMMAR CHANGED"

        self.steps.append(
            f"{title}\n"
            f"{'─' * 55}\n"
            f"{explanation}\n\n"
            f"BEFORE:\n{before_text}\n\n"
            f"STATUS: {change}\n\n"
            f"AFTER:\n{after_text}\n"
        )

    # --------------------------------------------------------
    # Validation
    # --------------------------------------------------------

    def validate(self):
        if not self.variables:
            return False, "Variables cannot be empty."

        if not self.terminals:
            return False, "Terminals cannot be empty."

        if not self.start:
            return False, "Start symbol cannot be empty."

        if self.start not in self.variables:
            return False, f"Start symbol '{self.start}' is not declared as a variable."

        if not self.rules:
            return False, "Production rules cannot be empty."

        for left, productions in self.rules.items():

            if left not in self.variables:
                return False, f"Variable '{left}' is not declared."

            for production in productions:

                if not production:
                    continue

                for symbol in production:

                    if symbol not in self.variables and symbol not in self.terminals:
                        return False, (
                            f"Symbol '{symbol}' is not declared "
                            f"as a variable or terminal."
                        )

        return True, "Grammar input is valid."

    # --------------------------------------------------------
    # Remove unit productions
    # --------------------------------------------------------

    def remove_unit(self):
        before = {v: set(p) for v, p in self.rules.items()}
        rules = {v: set(p) for v, p in self.rules.items()}

        changed = True
        while changed:
            changed = False
            for A in self.variables:
                new_rules = set()
                for prod in list(rules[A]):
                    if len(prod) == 1 and prod[0] in self.variables:
                        B = prod[0]
                        for x in rules.get(B, set()):
                            if x not in rules[A]:
                                new_rules.add(x)
                if new_rules:
                    rules[A].update(new_rules)
                    changed = True

        self.record_step(
            "STEP — REMOVE UNIT PRODUCTIONS",
            before,
            rules,
            "Unit productions such as A → B are replaced by the productions of B."
        )
        return rules

    # --------------------------------------------------------
    # Nullable variables
    # --------------------------------------------------------
    # Nullable variables
    # --------------------------------------------------------

    def nullable(self, rules):

        nullable = set()

        changed = True

        while changed:

            changed = False

            for A in self.variables:

                for prod in rules[A]:

                    if len(prod) == 0:
                        if A not in nullable:
                            nullable.add(A)
                            changed = True

                    elif all(symbol in nullable for symbol in prod):
                        if A not in nullable:
                            nullable.add(A)
                            changed = True

        return nullable

    # --------------------------------------------------------
    # Remove epsilon productions
    # --------------------------------------------------------

    def remove_epsilon(self, rules):
        before = {v: set(p) for v, p in rules.items()}
        nullable = self.nullable(rules)
        new_rules = {v: set() for v in self.variables}

        for A in self.variables:
            for prod in rules[A]:
                if len(prod) == 0:
                    continue

                positions = [
                    i for i, symbol in enumerate(prod)
                    if symbol in nullable
                ]

                combinations = [set()]
                for pos in positions:
                    combinations += [
                        s | {pos} for s in list(combinations)
                    ]

                for remove_positions in combinations:
                    new_prod = tuple(
                        symbol
                        for i, symbol in enumerate(prod)
                        if i not in remove_positions
                    )
                    if new_prod:
                        new_rules[A].add(new_prod)

        self.record_step(
            "STEP — REMOVE ε-PRODUCTIONS",
            before,
            new_rules,
            "Nullable variables were identified and ε-productions were removed. "
            "Required alternatives were generated."
        )
        return new_rules

    # --------------------------------------------------------
    # Remove useless symbols
    # --------------------------------------------------------
    # Remove useless symbols
    # --------------------------------------------------------

    def remove_useless(self, rules):
        before = {v: set(p) for v, p in rules.items()}

        generating = set()
        changed = True
        while changed:
            changed = False
            for A in self.variables:
                for prod in rules[A]:
                    if all(symbol in self.terminals or symbol in generating for symbol in prod):
                        if A not in generating:
                            generating.add(A)
                            changed = True

        reachable = {self.start}
        changed = True
        while changed:
            changed = False
            for A in list(reachable):
                for prod in rules.get(A, set()):
                    for symbol in prod:
                        if symbol in self.variables and symbol not in reachable:
                            reachable.add(symbol)
                            changed = True

        useful = generating & reachable
        result = {}

        for A in useful:
            result[A] = set()
            for prod in rules[A]:
                if all(symbol in self.terminals or symbol in useful for symbol in prod):
                    result[A].add(prod)

        self.record_step(
            "STEP — REMOVE USELESS SYMBOLS",
            before,
            result,
            "Non-generating and unreachable variables were removed."
        )
        return result

    # --------------------------------------------------------
    # Left recursion elimination
    # --------------------------------------------------------
    # Left recursion elimination
    # --------------------------------------------------------

    def eliminate_left_recursion(self, rules):
        before = {A: set(p) for A, p in rules.items()}
        result = {A: set(rules.get(A, set())) for A in rules}
        variables = list(result.keys())

        for i, A in enumerate(variables):
            for j in range(i):
                B = variables[j]
                replacements = set()

                for prod in result[A]:
                    if prod and prod[0] == B:
                        for beta in result[B]:
                            replacements.add(beta + prod[1:])
                    else:
                        replacements.add(prod)
                result[A] = replacements

            alpha = []
            beta = []

            for prod in result[A]:
                if prod and prod[0] == A:
                    alpha.append(prod[1:])
                else:
                    beta.append(prod)

            if alpha:
                new_var = A + "'"
                while new_var in result:
                    new_var += "'"

                result[new_var] = set()

                for b in beta:
                    result[A].add(b + (new_var,))

                result[A] = {
                    p for p in result[A]
                    if not (p and p[0] == A)
                }

                for a in alpha:
                    result[new_var].add(a + (new_var,))

                result[new_var].add(tuple())

        # Remove epsilon helper productions created during left-recursion removal.
        for A in list(result):
            result[A] = {p for p in result[A] if len(p) > 0}

        self.record_step(
            "STEP — ELIMINATE LEFT RECURSION",
            before,
            result,
            "Left-recursive productions were transformed into non-left-recursive productions."
        )
        return result

    # --------------------------------------------------------
    # Expand leading variables
    # --------------------------------------------------------
    # Expand leading variables
    # --------------------------------------------------------

    def expand_leading_variables(self, rules):
        before = {A: set(p) for A, p in rules.items()}
        result = {A: set(rules.get(A, set())) for A in rules}

        changed = True
        safety = 0

        while changed and safety < 100:
            safety += 1
            changed = False

            for A in list(result):
                new_set = set()

                for prod in result[A]:
                    if prod and prod[0] in result:
                        B = prod[0]
                        for Bprod in result[B]:
                            candidate = Bprod + prod[1:]
                            if candidate != prod:
                                new_set.add(candidate)
                                changed = True
                    else:
                        new_set.add(prod)

                result[A] = new_set

        self.record_step(
            "STEP — SUBSTITUTE LEADING VARIABLES",
            before,
            result,
            "Productions beginning with a variable were expanded using that variable's "
            "productions until the leading symbol becomes a terminal."
        )
        return result

    # --------------------------------------------------------
    # Replace terminals after first position
    # --------------------------------------------------------
    # Replace terminals after first position
    # --------------------------------------------------------

    def replace_later_terminals(self, rules):
        before = {A: set(p) for A, p in rules.items()}
        result = {A: set(rules.get(A, set())) for A in rules}
        helper_map = {}

        for A in list(result):
            new_rules = set()

            for prod in result[A]:
                if len(prod) <= 1:
                    new_rules.add(prod)
                    continue

                new_prod = list(prod)

                for i in range(1, len(new_prod)):
                    symbol = new_prod[i]

                    if symbol in self.terminals:
                        if symbol not in helper_map:
                            helper = "T_" + symbol
                            counter = 1

                            while helper in result:
                                helper = f"T_{symbol}_{counter}"
                                counter += 1

                            helper_map[symbol] = helper
                            result[helper] = {(symbol,)}

                        new_prod[i] = helper_map[symbol]

                new_rules.add(tuple(new_prod))

            result[A] = new_rules

        self.record_step(
            "STEP — REPLACE LATER TERMINALS",
            before,
            result,
            "Terminals appearing after the first position were replaced by helper "
            "variables such as T_a, T_b, etc."
        )
        return result

    # --------------------------------------------------------
    # GNF verification
    # --------------------------------------------------------
    # GNF verification
    # --------------------------------------------------------

    def is_gnf(self, rules):

        for A, productions in rules.items():

            for prod in productions:

                if not prod:
                    return False

                first = prod[0]

                if first not in self.terminals:
                    return False

                for symbol in prod[1:]:

                    if symbol not in self.variables and symbol not in rules:
                        return False

        return True

    # --------------------------------------------------------
    # Convert
    # --------------------------------------------------------

    def convert(self):

        valid, msg = self.validate()

        if not valid:
            raise ValueError(msg)

        self.steps = []

        rules = {
            A: set(prods)
            for A, prods in self.rules.items()
        }

        self.steps.append(
            "STEP 0 — ORIGINAL GRAMMAR\n"
            + "─" * 55 + "\n\n"
            + "This is the grammar entered by the user.\n\n"
            + "GRAMMAR:\n"
            + self.format_grammar(rules)
            + "\n"
        )

        rules = self.remove_unit()

        rules = self.remove_epsilon(rules)

        rules = self.remove_useless(rules)

        rules = self.eliminate_left_recursion(rules)

        rules = self.expand_leading_variables(rules)

        rules = self.replace_later_terminals(rules)

        rules = self.expand_leading_variables(rules)

        if not self.is_gnf(rules):

            raise ValueError(
                "The conversion could not produce strict GNF for this grammar."
            )

        self.steps.append(
            "FINAL STEP — GNF VERIFICATION\n"
            + "─" * 55 + "\n\n"
            + "FINAL GNF GRAMMAR:\n"
            + self.format_grammar(rules)
            + "\n\n"
            + "✓ Every production begins with a terminal.\n"
            + "✓ All symbols after the first position are variables.\n"
            + "✓ Grammar verified successfully as strict GNF.\n"
        )

        return rules


# ============================================================
# APP
# ============================================================

class GNFStudio:

    BG = "#0b1220"
    PANEL = "#111a2e"
    PANEL2 = "#16213a"
    TEXT = "#e8eefc"
    MUTED = "#91a1bd"
    BLUE = "#4f8cff"
    GREEN = "#2dd4a8"
    RED = "#ff6678"
    BORDER = "#263653"

    def __init__(self, root):

        self.root = root

        root.title("GNF Studio")
        root.geometry("1250x760")
        root.minsize(1100, 680)
        root.configure(bg=self.BG)

        self.setup_style()
        self.build_ui()

    # --------------------------------------------------------
    # Styling
    # --------------------------------------------------------

    def setup_style(self):

        style = ttk.Style()

        try:
            style.theme_use("clam")
        except:
            pass

        style.configure(
            "TNotebook",
            background=self.BG,
            borderwidth=0
        )

        style.configure(
            "TNotebook.Tab",
            background=self.PANEL2,
            foreground=self.MUTED,
            padding=(18, 10),
            font=("Segoe UI", 10, "bold")
        )

        style.map(
            "TNotebook.Tab",
            background=[
                ("selected", self.BLUE)
            ],
            foreground=[
                ("selected", "white")
            ]
        )

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------

    def build_ui(self):

        # Header
        header = tk.Frame(
            self.root,
            bg=self.BG
        )
        header.pack(
            fill="x",
            padx=30,
            pady=(22, 12)
        )

        title_frame = tk.Frame(
            header,
            bg=self.BG
        )
        title_frame.pack(side="left")

        tk.Label(
            title_frame,
            text="GNF STUDIO",
            font=("Segoe UI", 25, "bold"),
            fg=self.TEXT,
            bg=self.BG
        ).pack(anchor="w")

        tk.Label(
            title_frame,
            text="Context-Free Grammar  •  Greibach Normal Form",
            font=("Segoe UI", 11),
            fg=self.MUTED,
            bg=self.BG
        ).pack(anchor="w", pady=(2, 0))

        self.status = tk.Label(
            header,
            text="● READY",
            font=("Segoe UI", 10, "bold"),
            fg=self.GREEN,
            bg=self.BG
        )

        self.status.pack(
            side="right",
            pady=10
        )

        # Main
        main = tk.Frame(
            self.root,
            bg=self.BG
        )

        main.pack(
            fill="both",
            expand=True,
            padx=30,
            pady=10
        )

        # Left
        left = tk.Frame(
            main,
            bg=self.PANEL,
            highlightbackground=self.BORDER,
            highlightthickness=1
        )

        left.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 10)
        )

        tk.Label(
            left,
            text="01  •  GRAMMAR BUILDER",
            font=("Segoe UI", 11, "bold"),
            fg=self.BLUE,
            bg=self.PANEL
        ).pack(
            anchor="w",
            padx=20,
            pady=(18, 14)
        )

        self.variables = self.create_entry(
            left,
            "Variables",
            "Example: S A B"
        )

        self.terminals = self.create_entry(
            left,
            "Terminals",
            "Example: a b"
        )

        self.start = self.create_entry(
            left,
            "Start Symbol",
            "Example: S"
        )

        tk.Label(
            left,
            text="Production Rules",
            font=("Segoe UI", 10, "bold"),
            fg=self.TEXT,
            bg=self.PANEL
        ).pack(
            anchor="w",
            padx=20,
            pady=(10, 6)
        )

        self.rules = tk.Text(
            left,
            height=13,
            bg="#0d1628",
            fg=self.TEXT,
            insertbackground="white",
            selectbackground=self.BLUE,
            relief="flat",
            font=("Consolas", 10),
            padx=12,
            pady=10
        )

        self.rules.pack(
            fill="both",
            expand=True,
            padx=20
        )

        tk.Label(
            left,
            text="Format:  S -> A B | a",
            font=("Segoe UI", 9),
            fg=self.MUTED,
            bg=self.PANEL
        ).pack(
            anchor="w",
            padx=20,
            pady=(5, 8)
        )

        # Demo buttons
        demo_frame = tk.Frame(
            left,
            bg=self.PANEL
        )

        demo_frame.pack(
            fill="x",
            padx=20,
            pady=5
        )

        self.button(
            demo_frame,
            "VALID EXAMPLE",
            self.load_valid,
            self.GREEN
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 5)
        )

        self.button(
            demo_frame,
            "INVALID EXAMPLE",
            self.load_invalid,
            self.RED
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=(5, 0)
        )

        # Action buttons
        actions = tk.Frame(
            left,
            bg=self.PANEL
        )

        actions.pack(
            fill="x",
            padx=20,
            pady=(8, 20)
        )

        self.button(
            actions,
            "CLEAR",
            self.clear,
            "#33445f"
        ).pack(
            side="left",
            padx=(0, 5)
        )

        self.button(
            actions,
            "VALIDATE",
            self.validate_input,
            "#31558f"
        ).pack(
            side="left",
            padx=5
        )

        self.button(
            actions,
            "CONVERT  →",
            self.convert,
            self.BLUE
        ).pack(
            side="right"
        )

        # Right
        right = tk.Frame(
            main,
            bg=self.PANEL,
            highlightbackground=self.BORDER,
            highlightthickness=1
        )

        right.pack(
            side="right",
            fill="both",
            expand=True,
            padx=(10, 0)
        )

        tk.Label(
            right,
            text="02  •  CONVERSION PROCESS",
            font=("Segoe UI", 11, "bold"),
            fg=self.BLUE,
            bg=self.PANEL
        ).pack(
            anchor="w",
            padx=20,
            pady=(18, 10)
        )

        # Pipeline
        pipeline = tk.Frame(
            right,
            bg=self.PANEL
        )

        pipeline.pack(
            fill="x",
            padx=20,
            pady=(0, 12)
        )

        stages = [
            "CFG",
            "ε",
            "UNIT",
            "LEFT",
            "GNF"
        ]

        for i, stage in enumerate(stages):

            tk.Label(
                pipeline,
                text=stage,
                font=("Segoe UI", 9, "bold"),
                fg="white",
                bg=self.BLUE if stage == "GNF" else self.PANEL2,
                padx=10,
                pady=6
            ).pack(
                side="left"
            )

            if i < len(stages) - 1:

                tk.Label(
                    pipeline,
                    text="→",
                    font=("Segoe UI", 10, "bold"),
                    fg=self.MUTED,
                    bg=self.PANEL
                ).pack(
                    side="left",
                    padx=5
                )

        notebook = ttk.Notebook(right)

        notebook.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 15)
        )

        # Result
        result_tab = tk.Frame(
            notebook,
            bg="#0d1628"
        )

        notebook.add(
            result_tab,
            text="  GNF RESULT  "
        )

        self.result = tk.Text(
            result_tab,
            bg="#0d1628",
            fg=self.TEXT,
            insertbackground="white",
            relief="flat",
            font=("Consolas", 10),
            padx=15,
            pady=15
        )

        self.result.pack(
            fill="both",
            expand=True
        )

        # Steps
        steps_tab = tk.Frame(
            notebook,
            bg="#0d1628"
        )

        notebook.add(
            steps_tab,
            text="  STEPS  "
        )

        self.steps_box = tk.Text(
            steps_tab,
            bg="#0d1628",
            fg=self.TEXT,
            relief="flat",
            font=("Consolas", 10),
            padx=15,
            pady=15,
            wrap="word"
        )

        self.steps_box.pack(
            fill="both",
            expand=True
        )

        # Analysis
        analysis_tab = tk.Frame(
            notebook,
            bg="#0d1628"
        )

        notebook.add(
            analysis_tab,
            text="  ANALYSIS  "
        )

        self.analysis = tk.Text(
            analysis_tab,
            bg="#0d1628",
            fg=self.TEXT,
            relief="flat",
            font=("Segoe UI", 10),
            padx=15,
            pady=15
        )

        self.analysis.pack(
            fill="both",
            expand=True
        )

        # Footer
        footer = tk.Frame(
            self.root,
            bg=self.BG
        )

        footer.pack(
            fill="x",
            padx=30,
            pady=(0, 15)
        )

        tk.Label(
            footer,
            text="STRICT GNF  •  Every production begins with a terminal followed by zero or more variables",
            font=("Segoe UI", 9),
            fg=self.MUTED,
            bg=self.BG
        ).pack(side="left")

        tk.Label(
            footer,
            text="DESKTOP APPLICATION",
            font=("Segoe UI", 9, "bold"),
            fg=self.BLUE,
            bg=self.BG
        ).pack(side="right")

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    def create_entry(self, parent, label, placeholder):

        tk.Label(
            parent,
            text=label,
            font=("Segoe UI", 10, "bold"),
            fg=self.TEXT,
            bg=self.PANEL
        ).pack(
            anchor="w",
            padx=20,
            pady=(4, 5)
        )

        entry = tk.Entry(
            parent,
            bg="#0d1628",
            fg=self.TEXT,
            insertbackground="white",
            relief="flat",
            font=("Segoe UI", 10)
        )

        entry.pack(
            fill="x",
            padx=20,
            ipady=8
        )

        return entry

    def button(self, parent, text, command, color):

        return tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg="white",
            activebackground=color,
            activeforeground="white",
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            padx=14,
            pady=9
        )

    # --------------------------------------------------------
    # Load valid example
    # --------------------------------------------------------

    def load_valid(self):

        self.variables.delete(0, tk.END)
        self.variables.insert(0, "S A B")

        self.terminals.delete(0, tk.END)
        self.terminals.insert(0, "a b")

        self.start.delete(0, tk.END)
        self.start.insert(0, "S")

        self.rules.delete("1.0", tk.END)

        self.rules.insert(
            "1.0",
            "S -> A B | a\n"
            "A -> a\n"
            "B -> b"
        )

        self.status.config(
            text="● VALID EXAMPLE",
            fg=self.GREEN
        )

        self.result.delete("1.0", tk.END)
        self.result.insert(
            "1.0",
            "Valid CFG example loaded.\n\n"
            "Click CONVERT → to generate the GNF result."
        )

    # --------------------------------------------------------
    # Load invalid example
    # --------------------------------------------------------

    def load_invalid(self):

        self.variables.delete(0, tk.END)
        self.variables.insert(0, "S A")

        self.terminals.delete(0, tk.END)
        self.terminals.insert(0, "a b")

        self.start.delete(0, tk.END)
        self.start.insert(0, "S")

        self.rules.delete("1.0", tk.END)

        self.rules.insert(
            "1.0",
            "S -> A B\n"
            "A -> a"
        )

        self.status.config(
            text="● INVALID EXAMPLE",
            fg=self.RED
        )

        self.result.delete("1.0", tk.END)

        self.result.insert(
            "1.0",
            "INVALID CFG\n\n"
            "Reason:\n"
            "Symbol 'B' is used in the production,\n"
            "but B is not declared as a variable."
        )

    # --------------------------------------------------------
    # Parse input
    # --------------------------------------------------------

    def parse_input(self):

        variables = self.variables.get().strip().split()
        terminals = self.terminals.get().strip().split()
        start = self.start.get().strip()

        text = self.rules.get(
            "1.0",
            tk.END
        ).strip()

        rules = {}

        for line in text.splitlines():

            if not line.strip():
                continue

            if "->" not in line:
                raise ValueError(
                    f"Invalid production format:\n{line}"
                )

            left, right = line.split(
                "->",
                1
            )

            left = left.strip()

            if not left:
                raise ValueError(
                    "Production has no left-hand variable."
                )

            alternatives = right.split("|")

            rules.setdefault(left, set())

            for alt in alternatives:

                alt = alt.strip()

                if not alt:
                    continue

                symbols = tuple(
                    alt.split()
                )

                rules[left].add(symbols)

        return (
            variables,
            terminals,
            start,
            rules
        )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    def validate_input(self):

        try:

            variables, terminals, start, rules = self.parse_input()

            converter = GNFConverter(
                variables,
                terminals,
                start,
                rules
            )

            valid, msg = converter.validate()

            self.result.delete(
                "1.0",
                tk.END
            )

            if valid:

                self.status.config(
                    text="● VALID CFG",
                    fg=self.GREEN
                )

                self.result.insert(
                    "1.0",
                    "✓ VALID CFG\n\n"
                    "The grammar input is structurally valid.\n\n"
                    "You can now click CONVERT → to generate GNF."
                )

            else:

                self.status.config(
                    text="● INVALID CFG",
                    fg=self.RED
                )

                self.result.insert(
                    "1.0",
                    "✗ INVALID CFG\n\n"
                    + msg
                )

        except Exception as e:

            self.status.config(
                text="● INVALID INPUT",
                fg=self.RED
            )

            self.result.delete(
                "1.0",
                tk.END
            )

            self.result.insert(
                "1.0",
                "✗ INVALID INPUT\n\n"
                + str(e)
            )

    # --------------------------------------------------------
    # Convert
    # --------------------------------------------------------

    def convert(self):

        try:

            variables, terminals, start, rules = self.parse_input()

            converter = GNFConverter(
                variables,
                terminals,
                start,
                rules
            )

            valid, msg = converter.validate()

            if not valid:
                raise ValueError(msg)

            final_rules = converter.convert()

            self.result.delete(
                "1.0",
                tk.END
            )

            self.steps_box.delete(
                "1.0",
                tk.END
            )

            self.analysis.delete(
                "1.0",
                tk.END
            )

            self.result.insert(
                "1.0",
                "✓ VALID GNF\n"
                "────────────────────────────\n\n"
            )

            for A in final_rules:

                productions = []

                for prod in final_rules[A]:

                    productions.append(
                        " ".join(prod)
                    )

                if productions:

                    self.result.insert(
                        tk.END,
                        f"{A} → "
                        + " | ".join(productions)
                        + "\n"
                    )

            self.steps_box.insert(
                "1.0",
                "CONVERSION STEPS\n"
                "────────────────────────────\n\n"
            )

            for step in converter.steps:
                self.steps_box.insert(
                    tk.END,
                    step + "\n\n"
                )

            self.analysis.insert(
                "1.0",
                "GNF ANALYSIS\n"
                "────────────────────────────\n\n"
                "✓ Input CFG validated\n"
                "✓ ε-productions processed\n"
                "✓ Unit productions processed\n"
                "✓ Useless symbols processed\n"
                "✓ Left recursion processed\n"
                "✓ Leading variables substituted\n"
                "✓ Later terminals replaced\n"
                "✓ Final GNF verification passed\n\n"
                "RESULT\n"
                "Every production begins with a terminal.\n"
                "All following symbols are variables."
            )

            self.status.config(
                text="● GNF READY",
                fg=self.GREEN
            )

        except Exception as e:

            self.status.config(
                text="● CONVERSION ERROR",
                fg=self.RED
            )

            self.result.delete(
                "1.0",
                tk.END
            )

            self.result.insert(
                "1.0",
                "✗ CONVERSION FAILED\n\n"
                + str(e)
            )

            self.steps_box.delete(
                "1.0",
                tk.END
            )

            self.analysis.delete(
                "1.0",
                tk.END
            )

    # --------------------------------------------------------
    # Clear
    # --------------------------------------------------------

    def clear(self):

        self.variables.delete(
            0,
            tk.END
        )

        self.terminals.delete(
            0,
            tk.END
        )

        self.start.delete(
            0,
            tk.END
        )

        self.rules.delete(
            "1.0",
            tk.END
        )

        self.result.delete(
            "1.0",
            tk.END
        )

        self.steps_box.delete(
            "1.0",
            tk.END
        )

        self.analysis.delete(
            "1.0",
            tk.END
        )

        self.status.config(
            text="● READY",
            fg=self.GREEN
        )


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = GNFStudio(root)

    root.mainloop()