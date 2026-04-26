-- SQLite Schema for Translation Project

CREATE TABLE Languages (
    Name TEXT PRIMARY KEY NOT NULL,
    Family TEXT NOT NULL,
    Region TEXT
);

CREATE TABLE Model (
    ModelID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    Name TEXT NOT NULL,
    Version TEXT NOT NULL
);

CREATE TABLE Settings (
    SettingID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL
);

CREATE TABLE Ratings (
    RatingID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL
);

CREATE TABLE Documents (
    DocumentID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    Name TEXT NOT NULL,
    Type TEXT NOT NULL,
    OriginalLanguage TEXT NOT NULL,
    Description TEXT,
    FOREIGN KEY (OriginalLanguage) REFERENCES Languages(id)
);

CREATE TABLE Refrences (
    RefrenceID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    Name TEXT NOT NULL,
    Document INTEGER NOT NULL,
    Language TEXT NOT NULL,
    Text TEXT NOT NULL,
    FOREIGN KEY (Document) REFERENCES Documents(DocumentID),
    FOREIGN KEY (Language) REFERENCES Languages(id)
);

CREATE TABLE Translations (
    TranslationID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    Name TEXT NOT NULL,
    Document INTEGER NOT NULL,
    Refrence INTEGER,
    Translation INTEGER,
    Language TEXT NOT NULL,
    PreviousLanguage TEXT NOT NULL,
    Text TEXT NOT NULL,
    Model INTEGER NOT NULL,
    Settings INTEGER,
    Ratings INTEGER,
    FOREIGN KEY (Refrence) REFERENCES Refrences(RefrenceID),
    FOREIGN KEY (Translation) REFERENCES Translations(TranslationID),
    FOREIGN KEY (Language) REFERENCES Languages(id),
    FOREIGN KEY (PreviousLanguage) REFERENCES Languages(id),
    FOREIGN KEY (Model) REFERENCES Model(ModelID),
    FOREIGN KEY (Settings) REFERENCES Settings(SettingID),
    FOREIGN KEY (Ratings) REFERENCES Ratings(RatingID)
);
