#!/usr/bin/python3

import sqlite3
import difflib
import shlex
import sys
import operator
import ast
from optparse import OptionParser

CONN = None
PLEASE_REPEAT = "Promiňte nerozuměl jsem vám, opakujte prosím: "

def eval_expr(node):
    if isinstance(node, str): return eval_expr(ast.parse(node, mode='eval').body)
    if isinstance(node, ast.Num): return node.n
    if isinstance(node, ast.BinOp): return eval_expr.operators[type(node.op)](eval_expr(node.left), eval_(node.right))
    if isinstance(node, ast.UnaryOp): return eval_expr.operators[type(node.op)](eval_expr(node.operand))
    raise TypeError(node)
eval_expr.operators = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg}

def get_recipes_names_to_ids():
    cursor = CONN.cursor()
    cursor.execute("SELECT receptID, nazev FROM recepty")
    data = cursor.fetchall()
    return {nazev: id for (id, nazev) in data}

def get_units_names_to_ids():
    cursor = CONN.cursor()
    cursor.execute("SELECT jednotkaID, nazev, plural, genitiv FROM jednotky")
    data = cursor.fetchall()
    units_primary = {nazev: id for (id, *nazvy) in data for nazev in nazvy if nazev is not None}

    cursor.execute("SELECT jednotkaID, nazev FROM alternativni_jednotky")
    data = cursor.fetchall()
    units_secondary = {nazev: id for (id, nazev) in data}

    return {k: v for d in (units_primary, units_secondary) for k, v in d.items()}

def get_materials_names_to_ids():
    cursor = CONN.cursor()
    cursor.execute("SELECT surovinaID, nazev, genitiv FROM suroviny")
    data = cursor.fetchall()
    return {nazev: id for (id, *nazvy) in data for nazev in nazvy if nazev is not None}

def create_unit():
    name = input("Zadejte prosím název jednotky: ").strip()
    while not name:
        name = input(PLEASE_REPEAT).strip()

    existing_units = get_units_names_to_ids()
    while name in existing_units:
        response = input("Tato jednotka již existuje, chcete použít ji místo vytváření nové? [a/n] ").strip().lower()
        if response in ['a', 'y']:
            return existing_units[response]
        name = input("Zadejte tedy prosím jiný název: ").strip()
        while not name:
            name = input(PLEASE_REPEAT).strip()

    plural = input("Zadejte prosím název jednotky v nominativu plurálu (nechte prázdné, pokud je totožný s nominativem): ").strip()
    if not plural:
        plural = None

    genitiv = input("Zadejte prosím název jednotky v genitivu plurálu (nechte prázdné, pokud je totožný se singulárem): ").strip()
    if not genitiv:
        genitiv = None

    response = None
    while response not in ['a', 'y', 'n']:
        response = input("Je jednotka přesná? [a/n] ").strip().lower()
    precise = response in ['a', 'y']

    cursor = CONN.cursor()
    cursor.execute("INSERT INTO jednotky (nazev, genitiv, plural, presna) VALUES (?, ?, ?, ?)", (name, genitiv, plural, precise))
    return cursor.lastrowid

def create_material():
    name = input("Zadejte prosím název suroviny: ").strip()
    while not name:
        name = input(PLEASE_REPEAT).strip()

    existing_materials = get_materials_names_to_ids()
    while name in existing_materials:
        response = input("Tato surovina již existuje, chcete použít ji místo vytváření nové? [a/n] ").strip().lower()
        if response in ['a', 'y']:
            return existing_materials[response]
        name = input("Zadejte tedy prosím jiný název: ").strip()
        while not name:
            name = input(PLEASE_REPEAT).strip()

    genitiv = input("Zadejte prosím název suroviny v geninitivu (nechte prázdné, pokud je totožný s nominativem): ").strip()
    if not genitiv:
        genitv = None

    base_unit = input("Jakou základní jednotku má tato surovina? ")
    base_unit = resolve_unit(base_unit)

    cursor = CONN.cursor()
    cursor.execute("INSERT INTO suroviny (jednotkaID, nazev, genitiv) VALUES (?, ?, ?)", (base_unit, name, genitiv))
    material_id = cursor.lastrowid

    cursor.execute("INSERT INTO prevody (jednotkaID, surovinaID, multiplikator) VALUES (?, ?, ?)", (base_unit, material_id, 1))
    return material_id

def resolve_string(string, strings, fallback=None):
    if string in strings:
        return strings[string]
    alternatives = difflib.get_close_matches(string, strings.keys(), n=10)

    print("Název", string, "se nepodařilo najít, mysleli jste...")
    if alternatives:
        for alternative in alternatives:
            response = input("..." + alternative + "? [a/n/q] ").strip().lower()
            while response not in ['y', 'a', 'n', 'q']:
                response = input(PLEASE_REPEAT).strip().lower()
            if response in ['y', 'a']:
                return strings[alternative]
            elif response == 'q':
                break
        print("... nepodařilo se najít žádné další podobné názvy")
    else:
        print("... bohužel se nepodařilo najít žádný podobný název")

    if fallback:
        response = input("Chcete vytvořit nový záznam? [a/n] ").strip().lower()
        while response not in ['a', 'y', 'n']:
            reponse = input(PLEASE_REPEAT).stirp().lower()

        if response in ['a', 'y']:
            return fallback()
    return None

def resolve_unit(unit):
    return resolve_string(unit, get_units_names_to_ids(), create_unit)

def resolve_material(material):
    return resolve_string(material, get_materials_names_to_ids(), create_material)

def resolve_recipe(recipe):
    return resolve_string(recipe, get_recipes_names_to_ids())

def check_conversion(unit, material):
    cursor = CONN.cursor()
    cursor.execute("SELECT COUNT(prevodID) FROM prevody WHERE jednotkaID=? AND surovinaID=?", (unit, material))
    count = cursor.fetchone()[0]

    if count:
        return True

    cursor.execute("SELECT COALESCE(genitiv, nazev) FROM jednotky WHERE jednotkaID=?", (unit,))
    unit_genitiv = cursor.fetchone()[0]

    cursor.execute("SELECT COALESCE(s.genitiv, s.nazev), COALESCE(j.genitiv, j.nazev) FROM suroviny s LEFT JOIN jednotky j USING (jednotkaID) WHERE surovinaID=?", (material,))
    material_genitiv, basic_unit_genitiv = cursor.fetchone()

    msg = "Prosím zadejte kolik {} {} je potřeba k získání 1 {} {}: ".format(unit_genitiv, material_genitiv, basic_unit_genitiv, material_genitiv)

    while True:
        try:
            conversion = float(eval_expr(input(msg)))
            if conversion <= 0:
                raise ValueError
            break
        except EOFError:
            print("přeskakuji...")
            return False
        except Exception:
            msg = PLEASE_REPEAT

    cursor.execute("INSERT INTO prevody (jednotkaID, surovinaID, multiplikator) VALUES (?, ?, ?)", (unit, material, conversion))

    return True

def add_conversions():
    print("Na každém řádku zadejte kolik jednotek suroviny je potřeba k získání příslušné základní jednotky.")

    try:
        while True:
            row = input()
            if not row:
                break

            try:
                (count, unit, *name) = raw_inp = shlex.split(row)
                if not name:
                    raise ValueError
                count = float(count)
            except ValueError:
                print("Špatný vstup ", raw_inp, ", přeskakuji...")
                continue
            name = ' '.join(name)

            unit = resolve_unit(unit)
            if unit is None:
                continue

            material = resolve_material(name)
            if material is None:
                continue

            cursor = CONN.cursor()
            CONN.execute("INSERT OR REPLACE INTO prevody (jednotkaID, surovinaID, multiplikator) VALUES (?, ?, ?)", (unit, material, count))
    except EOFError:
        pass

def add_recipe():
    cursor = CONN.cursor()

    try:
        cursor.execute("SELECT nazev FROM recepty")
        existing_recipes = [x[0] for x in cursor.fetchall()]

        recipe_name = input("Název receptu: ").strip()
        while recipe_name in existing_recipes:
            recipe_name = input("Recept pro {} již existuje, zadejte prosím jiný název: ").strip()

        msg = "Počet porcí: "
        while True:
            try:
                ration_count = int(input(msg))
                break
            except ValueError:
                msg = PLEASE_REPEAT

        print("Nyní zadejte seznam potřebných surovin, výčet ukončete prázným řádkem")

        ingredients = []
        while True:
            row = input()
            if not row:
                break

            try:
                (count, unit, *name) = raw_inp = shlex.split(row)
                if not name:
                    raise ValueError
                count = float(count)
            except ValueError:
                print("Špatný vstup ", raw_inp, ", přeskakuji...")
                continue
            name = ' '.join(name)

            unit = resolve_unit(unit)
            if unit is None:
                continue

            material = resolve_material(name)
            if material is None:
                continue

            if not check_conversion(unit, material):
                continue

            ingredients.append((material, count / ration_count, unit))

    except EOFError:
        print()
        print("Ukončuji...")
        return

    print("Na zbytku vstupu je očekáván postup vaření:")
    lines = []
    try:
        while True:
            lines.append(input())
    except EOFError:
        pass
    description = '\n'.join(lines)

    cursor.execute("INSERT INTO recepty (nazev, postup) VALUES (?, ?)", (recipe_name, description))
    recipe_id = cursor.lastrowid

    ingredients_insert = [(recipe_id,) + ing for ing in ingredients]
    cursor.executemany("INSERT INTO ingredience (receptID, surovinaID, mnozstvi, jednotkaID) VALUES (?, ?, ?, ?)", ingredients_insert)

    print("Recept byl úspěšně vložen")

def list_recipes():
    cursor = CONN.cursor()
    cursor.execute("SELECT receptID, nazev FROM recepty")
    recipes = cursor.fetchall()
    print('\n'.join([': '.join(map(str, x)) for x in recipes]))

def find_best_unit_fit(material_id, amount, accurate):
    cursor = CONN.cursor()
    cursor.execute(
            "SELECT j.nazev, COALESCE(j.plural, j.nazev), COALESCE(j.genitiv, j.nazev), p.multiplikator "
            "FROM prevody p "
            "LEFT JOIN jednotky j USING (jednotkaID) "
            "WHERE p.surovinaID=? AND j.presna=? ",
            (material_id,accurate)
            )
    ingredients = cursor.fetchall()

    best_amount = None
    best_fit = None
    for name, plural, genitiv, multiplier in ingredients:
        this_amount = amount * multiplier
        if (
                best_amount is None
                or best_amount < 1 and this_amount > best_amount
                or this_amount > 1 and this_amount < best_amount
            ):
            best_amount = this_amount
            print_amount = "{0:.3f}".format(this_amount).rstrip('0').rstrip('.')
            case_amount = int(print_amount.split(".")[-1])
            if case_amount == 1:
                best_fit = print_amount + ' ' + name
            elif case_amount in [2,3,4]:
                best_fit = print_amount + ' ' + plural
            else:
                best_fit = print_amount + ' ' + genitiv

    return best_fit

def show_recipe():

    recipes = get_recipes_names_to_ids()
    argv = sys.argv[2:]
    if argv[0].isdigit() and len(argv) > 1:
        rations = int(argv[0])
        recipe = ' '.join(argv[1:])
    else:
        rations = 1
        recipe = ' '.join(argv)

    try:
        recipe = int(recipe)
        if recipe not in recipes.values():
            print("Zadaný recept neexistuje")
            return
    except ValueError:
        recipe = resolve_recipe(recipe)
        if not recipe:
            return

    cursor = CONN.cursor()
    cursor.execute(
            "SELECT s.surovinaID, s.nazev, s.genitiv, :rations * i.mnozstvi / p.multiplikator "
            "FROM ingredience i "
            "LEFT JOIN suroviny s USING (surovinaID) "
            "LEFT JOIN prevody p USING (jednotkaID, surovinaID) "
            "WHERE i.receptID=:recipe "
            , {'rations': rations, 'recipe': recipe}
            )
    ingredients = cursor.fetchall()

    for ing_id, ing_name, ing_genitiv, ing_amount in ingredients:
        if not ing_genitiv:
            ing_genitiv = ing_name

        acc_fit = find_best_unit_fit(ing_id, ing_amount, True)
        inacc_fit = find_best_unit_fit(ing_id, ing_amount, False)

        s = ""
        if acc_fit:
            s += acc_fit + ' '
        if inacc_fit:
            s += '(' + inacc_fit + ') '
        s += ing_genitiv
        print(s)

    print()

    cursor.execute("SELECT postup FROM recepty WHERE receptID=?", (recipe,))
    desc = cursor.fetchone()[0]
    print(desc)

if __name__ == "__main__":

    actions = {
            'add': add_recipe,
            'add_recipe': add_recipe,
            'list': list_recipes,
            'list_recipes': list_recipes,
            'show': show_recipe,
            'show_recipe': show_recipe,
            'add_conversion': add_conversions,
            }

    if len(sys.argv) > 1 and sys.argv[1] in actions:
        CONN = sqlite3.connect('databaze.db')
        CONN.isolation_level = None
        actions[sys.argv[1]]()
    else:
        print('Invalid options: available options are:')
        print(' '.join(actions.keys()))
