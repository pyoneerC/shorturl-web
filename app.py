from flask import Flask
app = Flask(__name__)
import datetime
import hashlib
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, Response
import requests
import psycopg2
import os
from starlette.responses import RedirectResponse

@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World!'

if __name__ == '__main__':
    app.run()

    app = FastAPI()


    def get_db_connection():
        return psycopg2.connect(os.getenv("DATABASE_URL"))


    @app.post("/shorten")
    async def create_short_url(url: str):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code < 200 or response.status_code >= 400:
                raise HTTPException(status_code=404, detail="Invalid URL")

            code = hashlib.md5(url.encode()).hexdigest()[:6]
            created_at = datetime.datetime.now()
            expiration_date = created_at + datetime.timedelta(days=69)

            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM urls WHERE short_code = %s", (code,))
            existing_url = cursor.fetchone()
            if existing_url:
                cursor.close()
                conn.close()
                raise HTTPException(status_code=409, detail=f"Short code already exists: {code}")

            cursor.execute(
                "INSERT INTO urls (short_code, original_url, created_at, last_updated_at, expiration_date, access_count) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (code, url, created_at.strftime("%Y-%m-%d %H:%M:%S %p"), created_at.strftime("%Y-%m-%d %H:%M:%S %p"),
                 expiration_date.strftime("%Y-%m-%d %H:%M:%S %p"), 0)
            )
            conn.commit()
            cursor.close()
            conn.close()

            return {
                "short_code": code,
                "original_url": url,
                "created_at": created_at.strftime("%Y-%m-%d %H:%M:%S %p"),
                "last_updated_at": created_at.strftime("%Y-%m-%d %H:%M:%S %p"),
                "expiration_date": expiration_date.strftime("%Y-%m-%d %H:%M:%S %p"),
                "access_count": 0
            }

        except requests.exceptions.RequestException:
            raise HTTPException(status_code=404,
                                detail="An error occurred while validating the URL, please try again later (or try putting 'http://' or 'https://' in front of the URL)")
        except psycopg2.Error as e:
            raise HTTPException(status_code=500, detail=f"Database error: {e}")


    @app.get("/shorten/{short_code}")
    async def get_original_url(short_code: str):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM urls WHERE short_code = %s", (short_code,))
            result = cursor.fetchone()

            if not result:
                cursor.close()
                conn.close()
                raise HTTPException(status_code=404, detail="Short code not found")

            expiration_date = result[5]
            if expiration_date < datetime.datetime.now():
                cursor.close()
                conn.close()
                await delete_short_url(short_code)
                raise HTTPException(status_code=404, detail="Short code has expired")

            cursor.execute("UPDATE urls SET access_count = access_count + 1 WHERE short_code = %s", (short_code,))
            conn.commit()

            cursor.close()
            conn.close()

            return {
                "short_code": result[1],
                "original_url": result[2],
                "created_at": result[3].strftime("%Y-%m-%d %H:%M:%S %p"),
                "last_updated_at": result[4].strftime("%Y-%m-%d %H:%M:%S %p"),
                "expiration_date": result[5].strftime("%Y-%m-%d %H:%M:%S %p"),
                "access_count": result[6] + 1
            }

        except psycopg2.Error as e:
            raise HTTPException(status_code=500, detail=f"Database error: {e}")


    @app.put("/shorten")
    async def update_short_url(short_code: str, url: str):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM urls WHERE short_code = %s", (short_code,))
            result = cursor.fetchone()

            if result is None:
                raise HTTPException(status_code=404, detail="Short code not found")

            expiration_date = result[5]
            if expiration_date < datetime.datetime.now():
                await delete_short_url(short_code)
                raise HTTPException(status_code=404, detail="Short code has expired")

            if url == result[2]:
                raise HTTPException(status_code=409, detail=f"New URL is the same as the current URL: {url}")

            last_updated_at = datetime.datetime.now()

            cursor.execute(
                "UPDATE urls SET original_url = %s, last_updated_at = %s, access_count = 0 WHERE short_code = %s",
                (url, last_updated_at, short_code)
            )
            conn.commit()

            cursor.execute("SELECT * FROM urls WHERE short_code = %s", (short_code,))
            updated_result = cursor.fetchone()

            cursor.close()
            conn.close()

            return {
                "short_code": updated_result[1],
                "original_url": updated_result[2],
                "created_at": updated_result[3].strftime("%Y-%m-%d %H:%M:%S %p"),
                "last_updated_at": updated_result[4].strftime("%Y-%m-%d %H:%M:%S %p"),
                "expiration_date": updated_result[5].strftime("%Y-%m-%d %H:%M:%S %p"),
                "access_count": updated_result[6]
            }

        except psycopg2.Error as e:
            raise HTTPException(status_code=500, detail=f"Database error: {e}")


    @app.delete("/shorten/{short_code}")
    async def delete_short_url(short_code: str):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM urls WHERE short_code = %s", (short_code,))
            result = cursor.fetchone()

            if result is None:
                cursor.close()
                conn.close()
                raise HTTPException(status_code=404, detail="Short code not found")

            cursor.execute("DELETE FROM urls WHERE short_code = %s", (short_code,))
            conn.commit()

            cursor.close()
            conn.close()

            return Response(status_code=204)

        except psycopg2.Error as e:
            raise HTTPException(status_code=500, detail=f"Database error: {e}")


    @app.get("/")
    async def redirect_to_url(short_code: str):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM urls WHERE short_code = %s", (short_code,))
            result = cursor.fetchone()

            if not result:
                cursor.close()
                conn.close()
                raise HTTPException(status_code=404, detail="Short code not found")

            expiration_date = result[5]

            if expiration_date < datetime.datetime.now():
                cursor.close()
                conn.close()
                await delete_short_url(short_code)
                raise HTTPException(status_code=404, detail="Short code has expired")

            return RedirectResponse(url=result[2])

        except psycopg2.Error as e:
            raise HTTPException(status_code=500, detail=f"Database error: {e}")

        except:
            raise HTTPException(status_code=404, detail="Short code not found")

