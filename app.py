import streamlit as st
from collections import deque

# ============================================================
# GNF STUDIO
# ============================================================

st.set_page_config(
    page_title="GNF Studio",
    page_icon="🔷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================
# SESSION STATE
# ============================================================

if "result" not in st.session_state:
    st.session_state.result = None

if "steps" not in st.session_state:
    st.session_state.steps = []

if "analysis" not in st.session_state:
    st.session_state.analysis = {}

if "error" not in st.session_state:
    st.session_state.error = None


# ============================================================
# CSS
# ============================================================

st.markdown("""
<style>

.stApp {
    background-color: #0b0f17;
}

[data-testid="stSidebar"] {
    background-color: #151a24;
}

.title-text {
    font-size: 38px;
    font-weight: 800;
    margin-bottom: 0px;
}

.subtitle-text {
    color: #9ca9ba;
    font-size: 16px;
    margin-top: 3px;
    margin-bottom: 25px;
}

.section-title {
    font-size: 24px;
    font-weight: 700;
}

.card {
    background-color: #151a24;
    border: 1px solid #303b4d;
    border-radius: 14px;
    padding: 20px;
    margin-bottom: 15px;
}

.step-card {
    background-color: #121823;
    border: 1px solid #303b4d;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 15px;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def copy_grammar(grammar):
    return {
        lhs: [list(rhs) for rhs in rules]
        for lhs, rules in grammar.items()
    }


def unique_rules(rules):
    result = []
    seen = set()

    for rule in rules:
        key = tuple(rule)

        if key not in seen:
            seen.add(key)
            result.append(list(rule))

    return result


def grammar_text(grammar):

    if not grammar:
        return "∅"

    lines = []

    for lhs, rules in grammar.items():

        alternatives = []

        for rhs in rules:

            if not rhs:
                alternatives.append("ε")
            else:
                alternatives.append(
                    " ".join(rhs)
                )

        lines.append(
            f"{lhs} → " + " | ".join(alternatives)
        )

    return "\n".join(lines)


def grammar_download_text(grammar):

    lines = []

    for lhs, rules in grammar.items():

        alternatives = []

        for rhs in rules:

            if not rhs:
                alternatives.append("ε")
            else:
                alternatives.append(
                    " ".join(rhs)
                )

        lines.append(
            f"{lhs} -> " + " | ".join(alternatives)
        )

    return "\n".join(lines)


def fresh_variable(grammar, prefix="X"):

    i = 1

    while f"{prefix}{i}" in grammar:
        i += 1

    return f"{prefix}{i}"


# ============================================================
# PARSER
# ============================================================

def parse_rhs(text):

    text = text.strip()

    if text in ["", "ε", "ϵ", "epsilon"]:
        return []

    # Spaced input
    if " " in text:
        return text.split()

    # Compact input
    return list(text)


def parse_grammar(text):

    grammar = {}

    for raw in text.splitlines():

        line = raw.strip()

        if not line:
            continue

        line = line.replace("→", "->")

        if "->" not in line:
            raise ValueError(
                f"Invalid production: {raw}"
            )

        lhs, rhs_part = line.split(
            "->",
            1
        )

        lhs = lhs.strip()

        if not lhs:
            raise ValueError(
                "Left side cannot be empty."
            )

        grammar.setdefault(lhs, [])

        for alternative in rhs_part.split("|"):

            grammar[lhs].append(
                parse_rhs(alternative)
            )

    for lhs in grammar:
        grammar[lhs] = unique_rules(
            grammar[lhs]
        )

    if not grammar:
        raise ValueError(
            "Please enter at least one production."
        )

    return grammar


# ============================================================
# STEP
# ============================================================

def add_step(
    steps,
    title,
    explanation,
    before,
    after
):

    changed = (
        grammar_text(before)
        !=
        grammar_text(after)
    )

    steps.append({
        "title": title,
        "explanation": explanation,
        "before": copy_grammar(before),
        "after": copy_grammar(after),
        "changed": changed
    })


# ============================================================
# REMOVE UNIT PRODUCTIONS
# ============================================================

def remove_unit(grammar):

    result = copy_grammar(grammar)

    variables = set(grammar.keys())

    changed = True

    while changed:

        changed = False

        for lhs in list(result.keys()):

            new_rules = []

            for rhs in result[lhs]:

                if (
                    len(rhs) == 1
                    and rhs[0] in variables
                ):

                    target = rhs[0]

                    for target_rule in result.get(
                        target,
                        []
                    ):

                        if target_rule not in new_rules:

                            new_rules.append(
                                list(target_rule)
                            )

                            changed = True

                else:

                    new_rules.append(
                        list(rhs)
                    )

            result[lhs] = unique_rules(
                new_rules
            )

    for lhs in result:

        result[lhs] = [
            rhs
            for rhs in result[lhs]
            if not (
                len(rhs) == 1
                and rhs[0] in variables
            )
        ]

    return result


# ============================================================
# NULLABLE
# ============================================================

def find_nullable(grammar):

    nullable = set()

    changed = True

    while changed:

        changed = False

        for lhs, rules in grammar.items():

            for rhs in rules:

                if not rhs:

                    if lhs not in nullable:
                        nullable.add(lhs)
                        changed = True

                elif all(
                    symbol in nullable
                    for symbol in rhs
                ):

                    if lhs not in nullable:
                        nullable.add(lhs)
                        changed = True

    return nullable


# ============================================================
# REMOVE EPSILON
# ============================================================

def remove_epsilon(
    grammar,
    start_symbol
):

    nullable = find_nullable(
        grammar
    )

    result = {
        lhs: []
        for lhs in grammar
    }

    for lhs, rules in grammar.items():

        for rhs in rules:

            if not rhs:
                continue

            nullable_positions = [
                i
                for i, symbol in enumerate(rhs)
                if symbol in nullable
            ]

            count = len(
                nullable_positions
            )

            for mask in range(
                1 << count
            ):

                remove_positions = set()

                for j in range(count):

                    if mask & (1 << j):

                        remove_positions.add(
                            nullable_positions[j]
                        )

                new_rhs = [
                    symbol
                    for i, symbol in enumerate(rhs)
                    if i not in remove_positions
                ]

                if new_rhs:

                    result[lhs].append(
                        new_rhs
                    )

                elif lhs == start_symbol:

                    result[lhs].append([])

    for lhs in result:

        result[lhs] = unique_rules(
            result[lhs]
        )

    return result


# ============================================================
# USELESS SYMBOLS
# ============================================================

def remove_useless(
    grammar,
    start_symbol
):

    variables = set(
        grammar.keys()
    )

    generating = set()

    changed = True

    while changed:

        changed = False

        for lhs, rules in grammar.items():

            for rhs in rules:

                possible = True

                for symbol in rhs:

                    if (
                        symbol in variables
                        and symbol not in generating
                    ):

                        possible = False
                        break

                if possible:

                    if lhs not in generating:

                        generating.add(lhs)
                        changed = True

    temp = {}

    for lhs, rules in grammar.items():

        if lhs not in generating:
            continue

        temp[lhs] = []

        for rhs in rules:

            valid = True

            for symbol in rhs:

                if (
                    symbol in variables
                    and symbol not in generating
                ):

                    valid = False
                    break

            if valid:
                temp[lhs].append(rhs)

        temp[lhs] = unique_rules(
            temp[lhs]
        )

    if start_symbol not in temp:
        return {}

    reachable = {
        start_symbol
    }

    queue = deque([
        start_symbol
    ])

    while queue:

        current = queue.popleft()

        for rhs in temp.get(
            current,
            []
        ):

            for symbol in rhs:

                if (
                    symbol in temp
                    and symbol not in reachable
                ):

                    reachable.add(
                        symbol
                    )

                    queue.append(
                        symbol
                    )

    return {
        lhs: rules
        for lhs, rules in temp.items()
        if lhs in reachable
    }


# ============================================================
# LEFT RECURSION
# ============================================================

def eliminate_left_recursion(grammar):

    result = copy_grammar(grammar)

    order = list(
        result.keys()
    )

    i = 0

    while i < len(order):

        current = order[i]

        # Indirect recursion
        for j in range(i):

            previous = order[j]

            expanded = []

            for rhs in result[current]:

                if (
                    rhs
                    and rhs[0] == previous
                ):

                    for previous_rhs in result.get(
                        previous,
                        []
                    ):

                        expanded.append(
                            previous_rhs
                            + rhs[1:]
                        )

                else:

                    expanded.append(rhs)

            result[current] = unique_rules(
                expanded
            )

        recursive = []
        normal = []

        for rhs in result[current]:

            if (
                rhs
                and rhs[0] == current
            ):

                recursive.append(
                    rhs[1:]
                )

            else:

                normal.append(rhs)

        if recursive:

            new_variable = fresh_variable(
                result,
                current + "_R"
            )

            result[current] = []

            for beta in normal:

                result[current].append(
                    beta
                )

                result[current].append(
                    beta + [new_variable]
                )

            result[new_variable] = []

            for alpha in recursive:

                if alpha:

                    result[new_variable].append(
                        alpha
                    )

                    result[new_variable].append(
                        alpha + [new_variable]
                    )

            # epsilon for helper
            result[new_variable].append([])

            result[current] = unique_rules(
                result[current]
            )

            result[new_variable] = unique_rules(
                result[new_variable]
            )

            order.append(
                new_variable
            )

        i += 1

    return result


# ============================================================
# EXPAND LEADING VARIABLES
# ============================================================

def expand_leading_variables(grammar):

    result = copy_grammar(grammar)

    for _ in range(50):

        changed = False

        variables = set(
            result.keys()
        )

        for lhs in list(result.keys()):

            new_rules = []

            for rhs in result[lhs]:

                if (
                    rhs
                    and rhs[0] in variables
                    and rhs[0] != lhs
                ):

                    first = rhs[0]

                    for replacement in result.get(
                        first,
                        []
                    ):

                        candidate = (
                            replacement
                            + rhs[1:]
                        )

                        if candidate not in new_rules:
                            new_rules.append(
                                candidate
                            )

                    changed = True

                else:

                    new_rules.append(
                        rhs
                    )

            new_rules = unique_rules(
                new_rules
            )

            if (
                grammar_text(
                    {lhs: result[lhs]}
                )
                !=
                grammar_text(
                    {lhs: new_rules}
                )
            ):

                changed = True

            result[lhs] = new_rules

        if not changed:
            break

    return result


# ============================================================
# REPLACE LATER TERMINALS
# ============================================================

def replace_later_terminals(grammar):

    result = copy_grammar(grammar)

    helpers = {}

    for lhs in list(result.keys()):

        new_rules = []

        for rhs in result[lhs]:

            if len(rhs) <= 1:

                new_rules.append(rhs)
                continue

            new_rhs = list(rhs)

            for i in range(
                1,
                len(new_rhs)
            ):

                symbol = new_rhs[i]

                if symbol not in result:

                    if symbol not in helpers:

                        helper = fresh_variable(
                            result,
                            "T"
                        )

                        result[helper] = [
                            [symbol]
                        ]

                        helpers[symbol] = helper

                    new_rhs[i] = helpers[
                        symbol
                    ]

            new_rules.append(
                new_rhs
            )

        result[lhs] = unique_rules(
            new_rules
        )

    return result


# ============================================================
# VALIDATE GNF
# ============================================================

def validate_gnf(
    grammar,
    start_symbol,
    terminals
):

    variables = set(
        grammar.keys()
    )

    problems = []

    for lhs, rules in grammar.items():

        for rhs in rules:

            if not rhs:

                if lhs != start_symbol:

                    problems.append(
                        f"{lhs} -> ε is not allowed."
                    )

                continue

            # First symbol should be terminal
            if rhs[0] in variables:

                problems.append(
                    f"{lhs} -> {' '.join(rhs)} "
                    f"starts with variable {rhs[0]}."
                )

            # Remaining symbols should be variables
            for symbol in rhs[1:]:

                if symbol not in variables:

                    problems.append(
                        f"{lhs} -> {' '.join(rhs)} "
                        f"has terminal '{symbol}' "
                        "after first position."
                    )

    return (
        len(problems) == 0,
        problems
    )


# ============================================================
# COMPLETE CONVERSION
# ============================================================

def convert_to_gnf(
    grammar,
    start_symbol,
    terminals
):

    steps = []

    current = copy_grammar(
        grammar
    )

    # STEP 0
    steps.append({
        "title": "STEP 0 — ORIGINAL GRAMMAR",
        "explanation": "Original grammar entered by the user.",
        "before": copy_grammar(current),
        "after": copy_grammar(current),
        "changed": False
    })

    # STEP 1
    before = copy_grammar(current)

    current = remove_unit(
        current
    )

    add_step(
        steps,
        "STEP 1 — REMOVE UNIT PRODUCTIONS",
        "Unit productions like A → B are replaced using B's productions.",
        before,
        current
    )

    # STEP 2
    before = copy_grammar(current)

    current = remove_epsilon(
        current,
        start_symbol
    )

    add_step(
        steps,
        "STEP 2 — REMOVE ε-PRODUCTIONS",
        "Nullable variables are used to generate required alternatives.",
        before,
        current
    )

    # STEP 3
    before = copy_grammar(current)

    current = remove_useless(
        current,
        start_symbol
    )

    if not current:

        raise ValueError(
            "Grammar became empty after useless-symbol removal."
        )

    add_step(
        steps,
        "STEP 3 — REMOVE USELESS SYMBOLS",
        "Non-generating and unreachable variables are removed.",
        before,
        current
    )

    # STEP 4
    before = copy_grammar(current)

    current = eliminate_left_recursion(
        current
    )

    add_step(
        steps,
        "STEP 4 — ELIMINATE LEFT RECURSION",
        "Direct and indirect left recursion is transformed.",
        before,
        current
    )

    # STEP 5
    before = copy_grammar(current)

    current = expand_leading_variables(
        current
    )

    add_step(
        steps,
        "STEP 5 — EXPAND LEADING VARIABLES",
        "Productions beginning with a variable are expanded.",
        before,
        current
    )

    # STEP 6
    before = copy_grammar(current)

    current = replace_later_terminals(
        current
    )

    add_step(
        steps,
        "STEP 6 — REPLACE LATER TERMINALS",
        "Terminals appearing after the first symbol are replaced by helper variables.",
        before,
        current
    )

    # STEP 7
    before = copy_grammar(current)

    current = expand_leading_variables(
        current
    )

    add_step(
        steps,
        "STEP 7 — FINAL GNF EXPANSION",
        "Remaining leading variables are expanded.",
        before,
        current
    )

    for lhs in current:
        current[lhs] = unique_rules(
            current[lhs]
        )

    valid, problems = validate_gnf(
        current,
        start_symbol,
        terminals
    )

    return (
        current,
        steps,
        valid,
        problems
    )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        "## 🔷 GNF Studio"
    )

    st.caption(
        "CFG → Greibach Normal Form"
    )

    st.divider()

    st.markdown(
        "### Conversion Flow"
    )

    st.write("1️⃣ Remove Unit Productions")
    st.write("2️⃣ Remove ε-Productions")
    st.write("3️⃣ Remove Useless Symbols")
    st.write("4️⃣ Eliminate Left Recursion")
    st.write("5️⃣ Expand Leading Variables")
    st.write("6️⃣ Replace Later Terminals")
    st.write("7️⃣ Final GNF Expansion")
    st.write("8️⃣ Validate GNF")

    st.divider()

    st.markdown(
        "### 📘 GNF Rule"
    )

    st.info(
        "Production must start with a terminal.\n\n"
        "Remaining symbols must be variables.\n\n"
        "Example:\n"
        "A → a B"
    )


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="title-text">🔷 GNF Studio</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle-text">'
    'Context-Free Grammar → Greibach Normal Form'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# INPUT SECTION
# ============================================================

st.markdown(
    "## 📝 Grammar Input"
)

# ------------------------------------------------------------
# Row 1
# ------------------------------------------------------------

col1, col2, col3 = st.columns(
    [1, 2, 2]
)

with col1:

    start_symbol = st.text_input(
        "Start Symbol",
        value="S"
    ).strip()

with col2:

    non_terminals_input = st.text_input(
        "Non-Terminals / Variables",
        value="S, A, B",
        help="Example: S, A, B"
    )

with col3:

    terminals_input = st.text_input(
        "Terminals",
        value="a, b",
        help="Example: a, b"
    )


# ------------------------------------------------------------
# Convert comma separated lists
# ------------------------------------------------------------

non_terminals = [
    x.strip()
    for x in non_terminals_input.split(",")
    if x.strip()
]

terminals = [
    x.strip()
    for x in terminals_input.split(",")
    if x.strip()
]


# ============================================================
# PRODUCTION RULES
# ============================================================

st.markdown(
    "### Production Rules"
)

grammar_input = st.text_area(
    "Enter production rules",
    value="""S -> A B | b
A -> a A | a
B -> b B | b""",
    height=180,
    help="Example: S -> A B | b"
)

st.caption(
    "Format: S -> A B | b"
)


# ============================================================
# INPUT PREVIEW
# ============================================================

with st.expander(
    "👁️ View Input Symbols"
):

    p1, p2 = st.columns(2)

    with p1:

        st.markdown(
            "**Non-Terminals**"
        )

        st.write(
            ", ".join(non_terminals)
            if non_terminals
            else "None"
        )

    with p2:

        st.markdown(
            "**Terminals**"
        )

        st.write(
            ", ".join(terminals)
            if terminals
            else "None"
        )


# ============================================================
# BUTTONS
# ============================================================

button1, button2 = st.columns(
    [4, 1]
)

with button1:

    convert_clicked = st.button(
        "🚀 CONVERT TO GNF",
        type="primary",
        use_container_width=True
    )

with button2:

    clear_clicked = st.button(
        "🗑️ CLEAR",
        use_container_width=True
    )


# ============================================================
# CLEAR
# ============================================================

if clear_clicked:

    st.session_state.result = None
    st.session_state.steps = []
    st.session_state.analysis = {}
    st.session_state.error = None

    st.rerun()


# ============================================================
# CONVERSION
# ============================================================

if convert_clicked:

    st.session_state.error = None

    try:

        if not start_symbol:

            raise ValueError(
                "Start Symbol is required."
            )

        if not non_terminals:

            raise ValueError(
                "Please enter Non-Terminals."
            )

        if not terminals:

            raise ValueError(
                "Please enter Terminals."
            )

        grammar = parse_grammar(
            grammar_input
        )

        # Check start symbol
        if start_symbol not in grammar:

            raise ValueError(
                f"Start symbol '{start_symbol}' "
                "does not exist in production rules."
            )

        # Check declared non-terminals
        missing = [
            x
            for x in grammar.keys()
            if x not in non_terminals
        ]

        if missing:

            raise ValueError(
                "These production variables are not "
                f"listed as Non-Terminals: {', '.join(missing)}"
            )

        (
            result,
            steps,
            valid,
            problems
        ) = convert_to_gnf(
            grammar,
            start_symbol,
            set(terminals)
        )

        st.session_state.result = result

        st.session_state.steps = steps

        st.session_state.analysis = {

            "valid": valid,

            "problems": problems,

            "variables_before":
                len(grammar),

            "variables_after":
                len(result),

            "productions_before":
                sum(
                    len(x)
                    for x in grammar.values()
                ),

            "productions_after":
                sum(
                    len(x)
                    for x in result.values()
                ),

            "non_terminals":
                non_terminals,

            "terminals":
                terminals
        }

    except Exception as error:

        st.session_state.result = None

        st.session_state.steps = []

        st.session_state.analysis = {}

        st.session_state.error = str(
            error
        )


# ============================================================
# ERROR
# ============================================================

if st.session_state.error:

    st.error(
        f"❌ {st.session_state.error}"
    )


# ============================================================
# OUTPUT
# ============================================================

if st.session_state.result is not None:

    result = st.session_state.result
    steps = st.session_state.steps
    analysis = st.session_state.analysis

    st.divider()

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    if analysis["valid"]:

        st.success(
            "✅ GNF conversion completed successfully."
        )

    else:

        st.warning(
            "⚠️ Conversion completed, but the final "
            "grammar has validation issues."
        )

    # --------------------------------------------------------
    # TABS
    # --------------------------------------------------------

    tab_result, tab_steps, tab_analysis = st.tabs(
        [
            "📋 GNF RESULT",
            "🔄 STEPS",
            "📊 ANALYSIS"
        ]
    )

    # ========================================================
    # RESULT
    # ========================================================

    with tab_result:

        st.subheader(
            "🎯 Final GNF Grammar"
        )

        st.code(
            grammar_text(result),
            language="text"
        )

        st.download_button(
            "⬇️ Download GNF Grammar",

            data=grammar_download_text(
                result
            ),

            file_name="gnf_result.txt",

            mime="text/plain",

            use_container_width=True
        )

    # ========================================================
    # STEPS
    # ========================================================

    with tab_steps:

        st.subheader(
            "🔄 Step-by-Step Conversion"
        )

        st.info(
            "Every transformation is shown as "
            "BEFORE → AFTER."
        )

        for step in steps:

            with st.container(
                border=True
            ):

                st.markdown(
                    f"### {step['title']}"
                )

                st.write(
                    step["explanation"]
                )

                if step["changed"]:

                    st.success(
                        "🔄 GRAMMAR CHANGED"
                    )

                else:

                    st.info(
                        "ℹ️ NO CHANGE REQUIRED"
                    )

                before_col, after_col = st.columns(
                    2
                )

                with before_col:

                    st.markdown(
                        "#### BEFORE"
                    )

                    st.code(
                        grammar_text(
                            step["before"]
                        ),
                        language="text"
                    )

                with after_col:

                    st.markdown(
                        "#### AFTER"
                    )

                    st.code(
                        grammar_text(
                            step["after"]
                        ),
                        language="text"
                    )

    # ========================================================
    # ANALYSIS
    # ========================================================

    with tab_analysis:

        st.subheader(
            "📊 Grammar Analysis"
        )

        c1, c2, c3, c4 = st.columns(
            4
        )

        c1.metric(
            "Variables Before",
            analysis["variables_before"]
        )

        c2.metric(
            "Variables After",
            analysis["variables_after"]
        )

        c3.metric(
            "Productions Before",
            analysis["productions_before"]
        )

        c4.metric(
            "Productions After",
            analysis["productions_after"]
        )

        st.divider()

        a1, a2 = st.columns(2)

        with a1:

            st.markdown(
                "### Non-Terminals"
            )

            st.write(
                ", ".join(
                    analysis["non_terminals"]
                )
            )

        with a2:

            st.markdown(
                "### Terminals"
            )

            st.write(
                ", ".join(
                    analysis["terminals"]
                )
            )

        st.divider()

        st.markdown(
            "### Conversion Summary"
        )

        summary = [
            "Unit productions processed",
            "ε-productions processed",
            "Useless symbols processed",
            "Left recursion processed",
            "Leading variables expanded",
            "Later terminals replaced",
            "Final expansion performed",
            "GNF validation completed"
        ]

        for item in summary:

            st.write(
                "✅",
                item
            )

else:

    # ========================================================
    # WELCOME
    # ========================================================

    st.divider()

    st.markdown(
        "## 👋 Welcome to GNF Studio"
    )

    st.write(
        "Enter your grammar above and click "
        "**CONVERT TO GNF**."
    )

    w1, w2, w3 = st.columns(3)

    with w1:

        st.markdown(
            "### 1️⃣ Input"
        )

        st.write(
            "Define Start Symbol, "
            "Non-Terminals and Terminals."
        )

    with w2:

        st.markdown(
            "### 2️⃣ Transform"
        )

        st.write(
            "The grammar is processed "
            "step-by-step."
        )

    with w3:

        st.markdown(
            "### 3️⃣ Result"
        )

        st.write(
            "View final GNF and complete "
            "transformation steps."
        )