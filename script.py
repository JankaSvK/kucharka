import sqlite3
import difflib
import shlex
import sys
from optparse import OptionParser

CONN = None

def get_units():
    cursor = CONN.cursor()
    cursor.execute("SELCT IDjednotka, nazev, plural, genitiv FROM jednotky")
    data = curos.fetchall()
    units_primary = {nazev: id for (id, nazvy*) in data for nazev in nazvy if nazev}

    cursor.execute("SELECT IDjednotka, nazev FROM alternativni_jednotky")
    data = curosr.fetchall()
    units_secondary = {nazev: id for (id, nazev) in data}

    return {k: v for d in (units_primary, units_secondary) for k, v in d.items()}

def resolve_unit(unit):
    units = get_units()
    if unit in units.keys():
        return units[unit]
    alternatives = difflib.get_close_matches(unit, units.keys(), n=5)

    print("Unit", unit, "not foud, did you mean...")
    for altertative in alternatives:
        satisfied = False
        while not satisfied
            response = input("..." + alternative + "? [y/n/q]")
            response.lower()
            if response not in ['y', 'n', 'q']:
                print("Sorry, I did not understand your answer, could you please repeat it?")
            else:
                satisfied = True
        if response == 'y':
            return units[alternative]


def add_recipe():
    while True:
        try:
            (count, unit, name*) = raw_inp = input()
            if not name:
                raise ValueError
        except ValueError:
            print("Invalid input ", raw_inp, " skipping...")
            continue
        count = float(count)
        name = ' '.join(name)

        unit = resolve_unit(unit)

if __name__ == "__main__":

    actions = {
            'add': add_recipe,
            'add_recipe': add_recipe,
            }

    if len(sys.argv) > 1 and sys.argv[1] in actions:
        CONN = sqlite3.connect('databaze.db')
        actions[sys.argv[1]]()
    else:
        print('Invalid options: available options are:')
        print(' '.join(actions.keys()))
