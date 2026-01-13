-- Add migration script here
INSERT INTO users (user_id, username, password_hash)
VALUES (
        'ddf8994f-d522-4659-8d02-c1d479057be6',
        'admin',
        '$argon2d$v=19$m=15000,t=2,p=1$DL95bix2KfP6Yzz1L5NXdQ$AnX5SYkZrRxkX8YhxzyHjjf/r/1CUaFHWiLqugcVED0'
);