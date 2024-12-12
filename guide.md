# MySQL
```bash
mysql -u root -p
```

```sql
CREATE DATABASE puzzle_db;

USE puzzle_db;

CREATE TABLE puzzles (
    PuzzleId VARCHAR(20) PRIMARY KEY,
    FEN VARCHAR(100),
    Moves VARCHAR(200),
    Rating INT,
    RatingDeviation INT,
    Popularity INT,
    NbPlays INT,
    Themes VARCHAR(200),
    GameUrl VARCHAR(50),
    OpeningTags VARCHAR(200)
);

LOAD DATA INFILE '/path/to/your/file.csv'
INTO TABLE puzzles
FIELDS TERMINATED BY ','
ENCLOSED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 ROWS;

CREATE INDEX idx_rating ON puzzles (Rating);
```

# Python
```bash
pip install -r requirements.txt
```

# Как запускаем
```bash
python game.py [mode] [foe] [color] [puzzle_index]
```
mode (обязательный аргумент):

    normal — игра
    puzzle — решение задачек

foe — противник (необязательный аргумент для normal) [по умолчанию: man]:

    man — игра с другим человеком
    computer — игра против компьютера

color — сторона (необязательный аргумент для normal) [по умолчанию: white]:

    white — играете белыми фигурами
    black — играете черными фигурами

puzzle_index — индекс задачки (обязательный аргумент для puzzle)

# config.ini
```ini
[mysql]
host = your_host
user = your_user
password = your_password
database = your_db_name
```

# Качаем двигатель
### https://stockfishchess.org/download/