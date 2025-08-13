import random
from sympy import simplify
from sympy.parsing.latex import parse_latex

def get_latex_expr(ex_str):
    if "=" in ex_str:
        ex_str = ex_str.split("=")[1].strip()
    ex_str = ex_str.replace("$", "")
    return parse_latex(ex_str)

def compare_latex(expr1, expr2):
    # 1) Direct structural equality
    eq = expr1.equals(expr2)
    if eq is True:
        return True
    else:
        # 2) Try symbol aliasing (e.g., gamma ↔ alpha)
        syms1 = {s.name: s for s in expr1.free_symbols}
        syms2 = {s.name: s for s in expr2.free_symbols}
        diff1 = set(syms1.keys()) - set(syms2.keys())
        diff2 = set(syms2.keys()) - set(syms1.keys())

        expr1_mapped = expr1
        if len(diff1) == 1 and len(diff2) == 1:
            s1 = syms1[list(diff1)[0]]
            s2 = syms2[list(diff2)[0]]
            expr1_mapped = expr1.subs({s1: s2})

        # 2a) Try simplify difference after mapping
        is_correct = False
        try:
            diff_simplified = simplify(expr1_mapped - expr2)
            if diff_simplified == 0:
                is_correct = True
            else:
                # 3) Numeric sampling fallback
                all_syms = list((expr1_mapped.free_symbols | expr2.free_symbols))
                def rand_val(name: str) -> float:
                    # Avoid zeros for decay/denominators; use positive range
                    return random.uniform(0.3, 2.5)
                ok = True
                for _ in range(5):
                    sub = {s: rand_val(s.name) for s in all_syms}
                    try:
                        v = (expr1_mapped - expr2).subs(sub).evalf()
                        if abs(float(v)) > 1e-6:
                            ok = False
                            break
                    except Exception:
                        ok = False
                        break
                is_correct = ok
        except Exception as e:
            print(f'Error simplifying difference: {expr1_mapped - expr2}')
            print(e)
    return is_correct