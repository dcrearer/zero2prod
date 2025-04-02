#!/usr/bin/env bash

CONNECTION_STRING="postgresql://newsletter:AVNS_fW-0KG2Zlk5OzXAtJgP@app-5fb226bd-635a-4ec0-a0c4-fbb831f70aae-do-user-19708848-0.i.db.ondigitalocean.com:25060/newsletter?sslmode=require"

DATABASE_URL=${CONNECTION_STRING} sqlx migrate run


