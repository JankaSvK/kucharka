CREATE TABLE "recepty" (
	"receptID" INTEGER PRIMARY KEY AUTOINCREMENT,
	"nazev" TEXT NOT NULL,
	"postup" TEXT DEFAULT NULL
);

CREATE TABLE "suroviny" (
	"surovinaID" INTEGER PRIMARY KEY AUTOINCREMENT,
	"nazev" TEXT NOT NULL,
	"genitiv" TEXT DEFAULT NULL
);

CREATE TABLE "jednotky" (
	"jednotkaID" INTEGER PRIMARY KEY AUTOINCREMENT,
	"nazev" TEXT NOT NULL,
	"plural" TEXT DEFAULT NULL,
	"genitiv" DEFAULT NULL,
	"presna" BOOLEAN NOT NULL DEFAULT 1
);

CREATE TABLE "ingredience" (
	"ingredienceID" INTEGER PRIMARY KEY AUTOINCREMENT,
	"receptID" INTEGER NOT NULL,
	"surovinaID" INTEGER NOT NULL,
	"mnozstvi" DECIMAL NOT NULL,
	"jednotkaID" INTEGER NOT NULL,

	FOREIGN KEY("receptID") REFERENCES "recepty"("receptID"),
	FOREIGN KEY("surovinaID") REFERENCES "suroviny"("surovinaID"),
	FOREIGN KEY("jednotkaID") REFERENCES "jednotky"("jednotkaID")
);

CREATE TABLE "prevody" (
	"prevodID" INTEGER PRIMARY KEY AUTOINCREMENT,
	"jednotkaID" INTEGER NOT NULL,
	"surovinaID" INTEGER NOT NULL,
	"multiplikator" DECIMAL NOT NULL,

	FOREIGN KEY("jednotkaID") REFERENCES "jednotky"("jednotkaID"),
	FOREIGN KEY("surovinaID") REFERENCES "suroviny"("surovinaID")
);

CREATE TABLE "alternativni_suroviny" (
	"alternativni_surovinaID" INTEGER PRIMARY KEY AUTOINCREMENT,
	"surovinaID" INTEGER NOT NULL,
	"nazev" TEXT NOT NULL,

	FOREIGN KEY("surovinaID") REFERENCES "suroviny"("surovinaID")
);

CREATE TABLE alternativni_jednotky (
	"alternativni_jednotkaID" INTEGER PRIMARY KEY AUTOINCREMENT,
	"jednotkaID" INTEGER NOT NULL,
	"nazev" TEXT NOT NULL,

	FOREIGN KEY("jednotkaID") REFERENCES "jednotky"("jednotkaID")
);
