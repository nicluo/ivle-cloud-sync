CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL
);

-- Running upgrade None -> 2046ba892660

ALTER TABLE ivle_file ADD COLUMN file_type VARCHAR(8);

ALTER TABLE ivle_file ADD COLUMN upload_time DATETIME;

INSERT INTO alembic_version (version_num) VALUES ('2046ba892660');

