
CREATE TABLE IF NOT EXISTS 'users'
('id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
 'username' TEXT NOT NULL,
 'hash' TEXT NOT NULL,
 'cash' NUMERIC NOT NULL DEFAULT 10000.00 );

CREATE TABLE IF NOT EXISTS 'transactions'
 ('id' INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
  'symbol' TEXT NOT NULL,
  'shares' INTEGER NOT NULL,
  'price' REAL NOT NULL,
  'created_at' TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  'user_id' INTEGER, CONSTRAINT fk_users FOREIGN KEY (user_id) REFERENCES users(id));



-- stonk-it::DATABASE=> create sequence id_users
-- stonk-it::DATABASE-> start 1
-- stonk-it::DATABASE-> increment 1
-- stonk-it::DATABASE-> NO MAXVALUE
-- stonk-it::DATABASE-> CACHE 1;
